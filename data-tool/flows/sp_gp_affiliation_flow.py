import json

import pandas as pd
import prefect
import requests
from legal_api.models import Business
from legal_api.services.bootstrap import AccountService
from prefect import task, Flow, unmapped
from prefect.client import Client
from prefect.engine.state import Skipped
from prefect.executors import LocalDaskExecutor
from prefect.schedules import IntervalSchedule

from config import get_named_config
from common.affiliation_queries import get_unaffiliated_firms_query
from common.lear_data_utils import get_firm_affiliation_passcode
from custom_filer.filing_processors.filing_components import business_profile
from common.affiliation_processing_status_service import AffiliationProcessingStatusService as ProcessingStatusService, \
    ProcessingStatuses
from common.custom_exceptions import CustomUnsupportedTypeException, CustomException
from tasks.task_utils import ColinInitTask, LearInitTask
from sqlalchemy import engine, text


colin_init_task = ColinInitTask(name='init_colin')
lear_init_task = LearInitTask(name='init_lear', flask_app_name='lear-affiliate', nout=2)


@task
def get_config():
    config = get_named_config()
    return config


@task(name='get_unaffiliated_firms')
def get_unaffiliated_firms(config, db_engine: engine):
    logger = prefect.context.get("logger")

    query = get_unaffiliated_firms_query(config.DATA_LOAD_ENV)
    sql_text = text(query)

    with db_engine.connect() as conn:
        rs = conn.execute(sql_text)
        df = pd.DataFrame(rs, columns=rs.keys())
        raw_data_dict = df.to_dict('records')
        corp_nums = [x.get('corp_num') for x in raw_data_dict]
        logger.info(f'{len(raw_data_dict)} corp_nums to process from colin data: {corp_nums}')

    return raw_data_dict


@task(name='clean_unaffiliated_firm_data')
def clean_unaffiliated_firm_data(unaffiliated_firm: dict):
    email = None
    # assume that if admin_email exists, that the SP/GP pipeline has already pushed contact information to auth
    if not unaffiliated_firm.get('admin_email') and unaffiliated_firm.get('contact_email'):
        email = unaffiliated_firm.get('contact_email')
    unaffiliated_firm['email'] = email

    return unaffiliated_firm


@task(name='transform_unaffiliated_firm_data')
def transform_unaffiliated_firm_data(unaffiliated_firm: dict):
    if email := unaffiliated_firm.get('email'):
        unaffiliated_firm['contact_info'] = { 'email': email }

    return unaffiliated_firm


@task(name='affiliate_firm_data')
def affiliate_firm_data(config, app, colin_db_engine: engine, db_lear, unaffiliated_firm: dict):
    logger = prefect.context.get("logger")
    status_service = ProcessingStatusService(config.DATA_LOAD_ENV, colin_db_engine)

    with app.app_context():
        try:
            account_id = unaffiliated_firm.get('account_id')
            account_svc_affiliate_url = f'{config.AUTH_SVC_URL}/orgs/{account_id}/affiliations'
            token = AccountService.get_bearer_token()
            corp_num = unaffiliated_firm.get('corp_num')
            business = Business.find_by_identifier(corp_num)
            pass_code = get_firm_affiliation_passcode(business)

            # Create an account:business affiliation
            affiliate_data = json.dumps({
                'businessIdentifier': corp_num,
                'passCode': pass_code
            })
            affiliate = requests.post(
                url=account_svc_affiliate_url,
                headers={**AccountService.CONTENT_TYPE_JSON,
                         'Authorization': AccountService.BEARER + token},
                data=affiliate_data,
                timeout=AccountService.timeout
            )

            if affiliate.status_code != 201:
                error_msg = f"""error affiliating {corp_num} to account {account_id}.
                            Affiliation status code: {affiliate.status_code} - {affiliate.text}
                            """
                raise CustomException(f'{error_msg}', unaffiliated_firm)

            # push contact info
            if contact_info := unaffiliated_firm.get('contact_info'):
                business_profile.update_business_profile(business, contact_info)

            status_service.update_status(corp_num=corp_num,
                                              account_id=account_id,
                                              processed_status=ProcessingStatuses.COMPLETED)

        except CustomUnsupportedTypeException as err:
            error_msg = f'Custom error for corp_num={corp_num}, account id={account_id}, {err}'
            logger.error(error_msg)
            status_service.update_status(corp_num=corp_num,
                                         account_id=account_id,
                                         processed_status=ProcessingStatuses.FAILED,
                                         last_error=error_msg)
            raise err
        except Exception as err:
            error_msg = f'error affiliating business {corp_num}, {account_id}, {err}'
            logger.error(error_msg)
            status_service.update_status(corp_num=corp_num,
                                              account_id=account_id,
                                              processed_status=ProcessingStatuses.FAILED,
                                              last_error=error_msg)
            raise err



def skip_if_running_handler(obj, old_state, new_state):  # pylint: disable=unused-argument
    if new_state.is_running():
        client = Client()
        flow_run_query = """
            query($flow_id: uuid) {
              flow_run(
                where: {
                    _and: [
                        {flow_id: {_eq: $flow_id}},
                        {state: {_eq: "Running"}}
                    ]
                }
                limit: 1
              ) {
                name
                state
                start_time
              }
            }
        """
        response = client.graphql(
            query=flow_run_query, variables=dict(flow_id=prefect.context.flow_id)
        )
        active_flow_runs = response["data"]["flow_run"]
        if active_flow_runs:
            logger = prefect.context.get("logger")
            message = "Skipping this flow run since there is already a flow run in progress"
            logger.info(message)
            print(f'{message}')
            return Skipped(message)
    return new_state


# Note: uncomment to run flow with prefect server as long running task with multiple runs
# now = datetime.utcnow()
# schedule = IntervalSchedule(interval=timedelta(minutes=1), start_date=now)
#
# with Flow(name="SP-GP-Affiliation",
#           schedule=schedule,
#           executor=LocalDaskExecutor(scheduler="threads"),
#            state_handlers=[skip_if_running_handler]) as f:
#           # state_handlers=[]) as f:

with Flow("SP-GP-Affiliation", executor=LocalDaskExecutor(scheduler="threads") ) as f:

    # setup
    config = get_config()
    db_colin_engine = colin_init_task(config)
    FLASK_APP, db_lear = lear_init_task(config)

    # get list unaffiliated firms
    unaffiliated_firms = get_unaffiliated_firms(config, db_colin_engine)

    # clean/validate to ensure all required affiliation fields are present
    cleaned_unaffiliated_firm_data = clean_unaffiliated_firm_data.map(unaffiliated_firms)

    # transform unaffiliated firm data into required form
    transform_unaffiliated_firm_data = transform_unaffiliated_firm_data.map(cleaned_unaffiliated_firm_data)

    # affiliate firms and push contact info where req'd
    affiliate_firm_data.map(unmapped(config),
                        unmapped(FLASK_APP),
                        unmapped(db_colin_engine),
                        unmapped(db_lear),
                        transform_unaffiliated_firm_data)


result = f.run()
