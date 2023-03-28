import json

import pandas as pd
import prefect
import requests
from legal_api.models import Business
from legal_api.services.bootstrap import AccountService
from prefect import task, Flow, unmapped, flow
from prefect.task_runners import SequentialTaskRunner

from config import get_named_config
from common.affiliation_queries import get_unaffiliated_firms_query
from common.lear_data_utils import get_firm_affiliation_passcode
from custom_filer.filing_processors.filing_components import business_profile
from common.affiliation_processing_status_service import AffiliationProcessingStatusService as ProcessingStatusService, \
    ProcessingStatuses
from common.custom_exceptions import CustomUnsupportedTypeException, CustomException
from sqlalchemy import create_engine, engine, text
from legal_api.models import db
from flask import Flask



@task(name='init_colin')
def colin_init(config):
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI_COLIN_MIGR)
    return engine


@task(name='init_lear')
def lear_init(config):
    FLASK_APP = Flask('init_lear')
    FLASK_APP.config.from_object(config)
    db.init_app(FLASK_APP)
    FLASK_APP.app_context().push()
    return FLASK_APP, db

@task
def get_config():
    config = get_named_config()
    return config


@task(name='get_unaffiliated_firms')
def get_unaffiliated_firms(config, db_engine: engine):
    logger = prefect.get_run_logger()

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
    logger = prefect.get_run_logger()
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



@flow(name="SP-GP-Affiliation", task_runner=SequentialTaskRunner())
def affiliate_flow():
    # setup
    config = get_config()
    db_colin_engine = colin_init(config)
    FLASK_APP, db_lear = lear_init(config)

    # get list unaffiliated firms
    unaffiliated_firms = get_unaffiliated_firms(config, db_colin_engine)

    # clean/validate to ensure all required affiliation fields are present
    cleaned_unaffiliated_firm_data = clean_unaffiliated_firm_data.map(unaffiliated_firms)

    # transform unaffiliated firm data into required form
    transformed_unaffiliated_firm_data = transform_unaffiliated_firm_data.map(cleaned_unaffiliated_firm_data)

    # affiliate firms and push contact info where req'd
    affiliate_firm_data.map(unmapped(config),
                        unmapped(FLASK_APP),
                        unmapped(db_colin_engine),
                        unmapped(db_lear),
                        transformed_unaffiliated_firm_data)


if __name__ == "__main__":
    affiliate_flow()
