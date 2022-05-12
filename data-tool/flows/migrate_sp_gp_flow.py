from datetime import datetime, timedelta

import pandas as pd
import prefect
from legal_api.models import Filing
from prefect import task, Flow, unmapped
from prefect.executors import LocalDaskExecutor
from prefect.schedules import IntervalSchedule

from config import get_named_config
from common.firm_queries import get_unprocessed_firms_query
from common.event_filing_service import EventFilingService
from common.firm_filing_json_factory import get_registration_sp_filing_json
from common.firm_filing_data_cleaning_utils import clean_naics_data, clean_corp_party_data, clean_offices_data
from common.processing_status_service import ProcessingStatusService
from custom_filer.filer import process_filing
from common.custom_exceptions import CustomException
from tasks.task_utils import ColinInitTask, LearInitTask
from sqlalchemy import engine, text


colin_init_task = ColinInitTask(name='init_colin')
lear_init_task = LearInitTask(name='init_lear', flask_app_name='lear-test-etl', nout=2)


@task
def get_config():
    config = get_named_config()
    return config


@task(name='get_unprocessed_firms')
def get_unprocessed_firms(db_engine: engine):
    logger = prefect.context.get("logger")

    query = get_unprocessed_firms_query()
    sql_text = text(query)

    with db_engine.connect() as conn:
        rs = conn.execute(sql_text)
        df = pd.DataFrame(rs, columns=rs.keys())
        raw_data_dict = df.to_dict('records')
        corp_nums = [x.get('corp_num') for x in raw_data_dict]
        logger.info(f'{len(raw_data_dict)} corp_nums to process from colin data: {corp_nums}')

    return raw_data_dict


@task(name='get_event_filing_data')
def get_event_filing_data(colin_db_engine: engine, unprocessed_firm_dict: dict):
    logger = prefect.context.get("logger")
    event_filing_service = EventFilingService(colin_db_engine)
    corp_num = unprocessed_firm_dict.get('corp_num')
    print(f'get event filing data for {corp_num}')

    event_ids = unprocessed_firm_dict.get('event_ids')
    event_file_types = unprocessed_firm_dict.get('event_file_types')
    event_file_types = event_file_types.split(',')
    event_filing_data_arr = []

    for idx, event_id in enumerate(event_ids):
        event_file_type = event_file_types[idx]
        is_supported_event_filing = event_filing_service.get_event_filing_is_supported(event_file_type)
        print(f'event_id: {event_id}, event_file_type: {event_file_type}, is_supported_event_filing: {is_supported_event_filing}')
        if is_supported_event_filing:
            event_filing_data_dict = event_filing_service.get_event_filing_data(corp_num, event_id, event_file_type)
            event_filing_data_arr.append({
                'processed': True,
                'data': event_filing_data_dict
            })
        else:
            event_filing_data_arr.append({
                'processed': False,
                'data': None
            })
    unprocessed_firm_dict['event_filing_data'] = event_filing_data_arr
    return unprocessed_firm_dict


@task(name='clean_event_filing_data')
def clean_event_filing_data(colin_db_engine: engine, event_filing_data_dict: dict):
    logger = prefect.context.get("logger")
    status_service = ProcessingStatusService(colin_db_engine)
    corp_num = event_filing_data_dict['corp_num']
    corp_name = 'Unknown'

    try:
        event_filing_data_arr = event_filing_data_dict['event_filing_data']
        for event_filing_data in event_filing_data_arr:
            if event_filing_data['processed']:
                filing_data = event_filing_data['data']
                corp_name = filing_data['cn_corp_name']
                clean_naics_data(filing_data)
                clean_corp_party_data(filing_data)
                clean_offices_data(filing_data)
    except Exception as err:
        logger.error(f'error cleaning business {corp_num}, {corp_name}, {err}')
        status_service.update_flow_status('sp-gp-flow', corp_num, corp_name, 'FAILED')
        raise CustomException(f'error cleaning business {corp_num}, {corp_name}, {err}', event_filing_data_dict)

    return event_filing_data_dict


@task(name='transform_event_filing_data')
def transform_event_filing_data(colin_db_engine: engine, event_filing_data_dict: dict):
    logger = prefect.context.get("logger")
    status_service = ProcessingStatusService(colin_db_engine)
    corp_num = event_filing_data_dict['corp_num']
    corp_name = 'Unknown'

    try:
        event_filing_data_arr = event_filing_data_dict['event_filing_data']
        for event_filing_data in event_filing_data_arr:
            if event_filing_data['processed']:
                # process and create LEAR json filing dict
                filing_data = event_filing_data['data']
                corp_name = filing_data['cn_corp_name']
                filing_json = get_registration_sp_filing_json(filing_data)
                event_filing_data['filing_json'] = filing_json
    except Exception as err:
        logger.error(f'error transforming business {corp_num}, {corp_name}, {err}')
        status_service.update_flow_status('sp-gp-flow', corp_num, corp_name, 'FAILED')
        raise CustomException(f'error transforming business {corp_num}, {corp_name}, {err}', event_filing_data_dict)

    return event_filing_data_dict


@task(name='load_event_filing_data')
def load_event_filing_data(app: any, colin_db_engine: engine, db_lear, event_filing_data_dict: dict):
    logger = prefect.context.get("logger")
    status_service = ProcessingStatusService(colin_db_engine)
    corp_num = event_filing_data_dict['corp_num']
    corp_name = 'Unknown'

    try:
        with app.app_context():
            event_filing_data_arr = event_filing_data_dict['event_filing_data']
            for event_filing_data in event_filing_data_arr:
                if event_filing_data['processed']:
                    filing_data = event_filing_data['data']
                    filing_json = event_filing_data['filing_json']
                    effective_date = filing_data['f_effective_dts']
                    corp_name = filing_data['cn_corp_name']

                    # save filing to filing table
                    filing = Filing()
                    filing.effective_date = effective_date
                    filing._filing_json = filing_json
                    filing._filing_type = 'registration'
                    filing.filing_date = effective_date

                    # Override the state setting mechanism
                    filing.source = Filing.Source.COLIN.value
                    db_lear.session.add(filing)
                    db_lear.session.commit()

                    # process filing with custom filer function
                    process_filing(filing.id, filing_data, db_lear)
                    status_service.update_flow_status('sp-gp-flow', corp_num, corp_name, 'COMPLETED')

                    # confirm can access from dashboard if we use existing account for now
    except Exception as err:
        logger.error(f'error loading business {corp_num}, {corp_name}, {err}')
        status_service.update_flow_status('sp-gp-flow', corp_num, corp_name, 'FAILED')
        db_lear.session.rollback()


now = datetime.utcnow()
schedule = IntervalSchedule(interval=timedelta(minutes=10), start_date=now)

with Flow("SP-GP-Migrate-ETL", schedule=schedule, executor=LocalDaskExecutor(scheduler="threads")) as f:

    # setup
    config = get_config()
    db_colin_engine = colin_init_task(config)
    FLASK_APP, db_lear = lear_init_task(config)

    unprocessed_firms = get_unprocessed_firms(db_colin_engine)

    # get event/filing related data for each firm
    event_filing_data = get_event_filing_data.map(colin_db_engine=unmapped(db_colin_engine),
                                                  unprocessed_firm_dict=unprocessed_firms)

    # clean/validate filings for a given business
    cleaned_event_filing_data = clean_event_filing_data.map(unmapped(db_colin_engine),
                                                            event_filing_data)

    # transform data to appropriate format in preparation for data loading into LEAR
    transformed_event_filing_data = transform_event_filing_data.map(unmapped(db_colin_engine),
                                                                    cleaned_event_filing_data)

    # load all filings for a given business sequentially
    # if a filing fails, flag business as failed indicating which filing it failed at
    loaded_event_filing_data = load_event_filing_data.map(unmapped(FLASK_APP),
                                                          unmapped(db_colin_engine),
                                                          unmapped(db_lear),
                                                          transformed_event_filing_data)

