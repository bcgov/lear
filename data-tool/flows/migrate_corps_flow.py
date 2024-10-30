import os
import sys

# Prefect 3 dependencies requires SQLAlchemy 2.x so we load what Prefect 3 needs by default.
# We override SqlAlchemy in this flow to use SQLAlchemy 1.4.44 which is still required by
# legal api dependencies.
# Add SQLAlchemy 1.4.44 to path - do this before any other imports
sqlalchemy_path = os.getenv('SQLALCHEMY_PATH')
if sqlalchemy_path:
    print(f'Using SQLAlchemy from: {sqlalchemy_path}')
    sys.path.insert(0, sqlalchemy_path)
    from sqlalchemy import __version__, create_engine, engine, text
    from sqlalchemy.exc import InvalidRequestError
    print(f'SQLAlchemy version: {__version__}')


import pandas as pd
import prefect
from legal_api.models import db
from legal_api.models.db import init_db
from legal_api.models import Business
from prefect import flow, task, serve


from config import get_named_config
from flows.corps.corp_queries import get_unprocessed_corps_query
from flows.corps.event_filing_service import EventFilingService, IAEventFilings
from corps.filing_data_cleaning_utils import clean_offices_data, clean_corp_party_data, clean_corp_data, clean_event_data
from common.processing_status_service import ProcessingStatusService, ProcessingStatuses
from custom_filer.corps_filer import process_filing
from common.custom_exceptions import CustomException, CustomUnsupportedTypeException
from flows.corps.lear_data_utils import populate_filing_json_from_lear, populate_filing
from corps.filing_json_factory_service import FilingJsonFactoryService
from corps.filing_data_utils import get_previous_event_ids, \
    get_processed_event_ids, get_event_info_to_retrieve, is_in_lear
from flask import Flask
from datetime import timedelta



@task(
    name="colin_init",
    # retries=3,
    # retry_delay_seconds=60,
    log_prints=True
)
def colin_init(config):
    print("Initializing COLIN connection")
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI_COLIN_MIGR)
    return engine


@task(
    name="lear_init",
    # retries=3,
    # retry_delay_seconds=60,
    log_prints=True
)
def lear_init(config):
    print("Initializing LEAR connection")
    FLASK_APP = Flask('init_lear')
    FLASK_APP.config.from_object(config)
    init_db(FLASK_APP)
    FLASK_APP.app_context().push()
    return FLASK_APP, db


@task(
    name="get_config",
    # retries=3,
    # retry_delay_seconds=60,
    log_prints=True
)
def get_config():
    config = get_named_config()
    return config


@task(
    name="get_unprocessed_corps",
    # retries=3,
    # retry_delay_seconds=60,
    log_prints=True
)
def get_unprocessed_corps(config, db_engine: engine):
    print("Getting unprocessed corporations")
    logger = prefect.get_run_logger()
    query = get_unprocessed_corps_query(config.DATA_LOAD_ENV)
    sql_text = text(query)

    with db_engine.connect() as conn:
        rs = conn.execute(sql_text)
        df = pd.DataFrame(rs, columns=rs.keys())
        raw_data_dict = df.to_dict('records')
        corp_nums = [x.get('corp_num') for x in raw_data_dict]
        # logger.info(f'{len(raw_data_dict)} corp_nums to process from colin data: {corp_nums}')
        status_service = ProcessingStatusService(config.DATA_LOAD_ENV, db_engine)
        # TODO: optimize to update all records in one-shot
        for corp_num in corp_nums:
            status_service.update_flow_status(flow_name='corps-flow',
                                              corp_num=corp_num,
                                              processed_status=ProcessingStatuses.PROCESSING)
    return raw_data_dict


@task(
    name="get_event_filing_data",
    # retries=3,
    # retry_delay_seconds=60,
    # cache_key_fn=task_input_hash,
    # cache_expiration=timedelta(minutes=30),  # Shorter expiration for data freshness
    log_prints=True
)
def get_event_filing_data(config, colin_db_engine: engine, unprocessed_corp_dict: dict):
    logger = prefect.get_run_logger()
    corp_num = unprocessed_corp_dict.get('corp_num')
    print(f"Starting event filing data processing for corp: {corp_num}")
    status_service = ProcessingStatusService(config.DATA_LOAD_ENV, colin_db_engine)
    event_filing_service = EventFilingService(colin_db_engine, config)
    corp_name = ''

    try:
        event_ids = unprocessed_corp_dict.get('event_ids')
        correction_event_ids = unprocessed_corp_dict.get('correction_event_ids')
        events_ids_to_process, event_filing_types_to_process = get_event_info_to_retrieve(unprocessed_corp_dict)
        processed_events_ids = get_processed_event_ids(unprocessed_corp_dict)
        unprocessed_corp_dict['retrieved_events_cnt'] = len(events_ids_to_process)
        event_filing_data_arr = []

        corp_comments = event_filing_service.get_corp_comments_data(corp_num)
        unprocessed_corp_dict['corp_comments'] = corp_comments
        unprocessed_corp_dict['correctionEventFilingMappings'] = {}
        correction_event_filing_mappings = unprocessed_corp_dict['correctionEventFilingMappings']

        prev_event_filing_data = None
        for idx, event_id in enumerate(events_ids_to_process):
            event_file_type = event_filing_types_to_process[idx]
            is_supported_event_filing = event_filing_service.get_event_filing_is_supported(event_file_type)
            # print(f'event_id: {event_id}, event_file_type: {event_file_type}, is_supported_event_filing: {is_supported_event_filing}')
            prev_event_ids = get_previous_event_ids(event_ids, event_id)
            event_filing_data_dict, is_corrected_event_filing, correction_event_id = \
                event_filing_service.get_event_filing_data(corp_num,
                                                           event_id,
                                                           event_file_type,
                                                           prev_event_filing_data,
                                                           prev_event_ids,
                                                           correction_event_ids,
                                                           correction_event_filing_mappings)
            if is_corrected_event_filing:
                correction_event_filing_mappings[correction_event_id] = {
                    'correctedEventId': event_id,
                    'learFilingType': event_filing_data_dict['target_lear_filing_type']
                }

            event_filing_data_arr.append({
                'is_in_lear': is_in_lear(processed_events_ids, event_id),
                'is_supported_type': is_supported_event_filing,
                'skip_filing': event_filing_data_dict['skip_filing'],
                'data': event_filing_data_dict
            })
            prev_event_filing_data = event_filing_data_dict

        unprocessed_corp_dict['event_filing_data'] = event_filing_data_arr

    except Exception as err:
        error_msg = f'error getting event filing data {corp_num}, {corp_name}, {err}'
        error_msg_minimal = f'error getting event filing data {corp_num}, {corp_name}'
        logger.error(error_msg_minimal)
        status_service.update_flow_status(flow_name='corps-flow',
                                          corp_num=corp_num,
                                          corp_name=corp_name,
                                          processed_status=ProcessingStatuses.FAILED,
                                          failed_event_id=event_id,
                                          failed_event_file_type=event_file_type,
                                          last_error=error_msg)
        raise CustomException(error_msg_minimal)

    print(f"Completed event filing data processing for corp: {corp_num}")
    return unprocessed_corp_dict


@task(
    name="clean_event_filing_data",
    # retries=3,
    # retry_delay_seconds=60,
    log_prints=True
)
def clean_event_filing_data(config, colin_db_engine: engine, event_filing_data_dict: dict):
    logger = prefect.get_run_logger()
    corp_num = event_filing_data_dict.get('corp_num')
    print(f"Starting data cleaning for corp: {corp_num}")
    status_service = ProcessingStatusService(config.DATA_LOAD_ENV, colin_db_engine)
    corp_name = ''
    event_id = None
    event_filing_type = None

    try:
        event_filing_data_arr = event_filing_data_dict['event_filing_data']
        for event_filing_data in event_filing_data_arr:
            if event_filing_data['is_supported_type'] and not event_filing_data['skip_filing']:
                filing_data = event_filing_data['data']
                event_filing_type = filing_data['event_file_type']
                event_id=filing_data['e_event_id']
                clean_event_data(filing_data)
                clean_corp_data(config, filing_data)
                corp_name = filing_data['curr_corp_name']
                clean_corp_party_data(filing_data)
                clean_offices_data(filing_data)
    except Exception as err:
        error_msg = f'error cleaning business {corp_num}, {corp_name}, {err}'
        error_msg_minimal = f'error cleaning business {corp_num}, {corp_name}'
        logger.error(error_msg_minimal)
        status_service.update_flow_status(flow_name='corps-flow',
                                          corp_num=corp_num,
                                          corp_name=corp_name,
                                          processed_status=ProcessingStatuses.FAILED,
                                          failed_event_id=event_id,
                                          failed_event_file_type=event_filing_type,
                                          last_error=error_msg)
        raise CustomException(error_msg_minimal)

    print(f"Completed data cleaning for corp: {corp_num}")
    return event_filing_data_dict


@task(
    name="transform_event_filing_data",
    # retries=3,
    # retry_delay_seconds=60,
    log_prints=True
)
def transform_event_filing_data(config, colin_db_engine: engine, event_filing_data_dict: dict):
    logger = prefect.get_run_logger()
    corp_num = event_filing_data_dict.get('corp_num')
    print(f"Starting data transformation for corp: {corp_num}")
    status_service = ProcessingStatusService(config.DATA_LOAD_ENV, colin_db_engine)
    corp_name = ''
    event_id = None
    event_filing_type = None

    try:
        event_filing_data_arr = event_filing_data_dict['event_filing_data']
        for event_filing_data in event_filing_data_arr:
            if not event_filing_data['is_in_lear'] and event_filing_data['is_supported_type']  \
                    and not event_filing_data['skip_filing']:
                # process and create LEAR json filing dict
                filing_data = event_filing_data['data']
                event_filing_type = filing_data['event_file_type']
                event_id=filing_data['e_event_id']
                corp_name = filing_data['curr_corp_name']
                corp_filing_json_factory_service = FilingJsonFactoryService(event_filing_data)
                filing_json = corp_filing_json_factory_service.get_filing_json()
                event_filing_data['filing_json'] = filing_json
    except Exception as err:
        error_msg = f'error transforming business {corp_num}, {corp_name}, {err}'
        error_msg_minimal = f'error transforming business {corp_num}, {corp_name}'
        logger.error(error_msg_minimal)
        status_service.update_flow_status(flow_name='corps-flow',
                                          corp_num=corp_num,
                                          corp_name=corp_name,
                                          processed_status=ProcessingStatuses.FAILED,
                                          failed_event_id=event_id,
                                          failed_event_file_type=event_filing_type,
                                          last_error=error_msg)
        raise CustomException(error_msg_minimal)

    print(f"Completed data transformation for corp: {corp_num}")
    return event_filing_data_dict


@task(
    name="load_event_filing",
    # retries=3,
    # retry_delay_seconds=60,
    log_prints=True
)
def load_event_filing_data(config, app: any, colin_db_engine: engine, db_lear, event_filing_data_dict: dict):
    logger = prefect.get_run_logger()
    corp_num = event_filing_data_dict.get('corp_num')
    print(f"Starting data load for corp: {corp_num}")
    status_service = ProcessingStatusService(config.DATA_LOAD_ENV, colin_db_engine)
    corp_type = event_filing_data_dict['corp_type_cd']
    filings_count = event_filing_data_dict['cnt']
    corp_name = ''
    event_id = None
    event_filing_type = None
    filing = None
    filing_processed = False

    with app.app_context():
        try:
            event_filing_data_arr = event_filing_data_dict['event_filing_data']
            for idx, event_filing_data in enumerate(event_filing_data_arr):
                filing_data = event_filing_data['data']
                event_id=filing_data['e_event_id']
                event_filing_type = filing_data['event_file_type']

                if not event_filing_data['is_supported_type']:
                    error_msg = f'could not finish processing this corp as there is an unsupported event/filing type: {event_filing_type}'
                    raise CustomUnsupportedTypeException(f'{error_msg}')

                if not event_filing_data['is_in_lear'] and not event_filing_data['skip_filing']:
                    # the corp_processing table should already track whether an event/filing has been processed and
                    # saved to lear but just to be safe a final check against lear is made to ensure the event/filing
                    # is not already in lear
                    # colin_event = get_colin_event(db_lear, event_id)
                    # if colin_event:
                    #     error_msg = f'colin event id ({event_id}) already exists in lear: {event_filing_type}'
                    #     raise CustomException(f'{error_msg}')

                    business = None
                    if not IAEventFilings.has_value(event_filing_type):
                        business = Business.find_by_identifier(corp_num)
                    populate_filing_json_from_lear(db, event_filing_data, business)
                    corp_name = filing_data['curr_corp_name']

                    # save filing to filing table
                    filing = populate_filing(business, event_filing_data, filing_data)
                    filing.save()

                    # process filing with custom filer function
                    business = process_filing(config, filing.id, event_filing_data_dict, filing_data, db_lear)
                    filing_processed = True

                    event_cnt = event_filing_data_dict['retrieved_events_cnt']
                    if event_cnt == (idx + 1):
                        status_service.update_flow_status(flow_name='corps-flow',
                                                          corp_num=corp_num,
                                                          corp_name=corp_name,
                                                          corp_type=corp_type,
                                                          filings_count=filings_count,
                                                          processed_status=ProcessingStatuses.COMPLETED,
                                                          last_processed_event_id=event_id)
                        print(f"Completed data load for corp: {corp_num}")
                    else:
                        status_service.update_flow_status(flow_name='corps-flow',
                                                          corp_num=corp_num,
                                                          corp_name=corp_name,
                                                          processed_status=ProcessingStatuses.PROCESSING,
                                                          last_processed_event_id=event_id)
        except CustomUnsupportedTypeException as err:
            error_msg = f'Partial loading of business {corp_num}, {corp_name}, {err}'
            error_msg_minimal = f'Partial loading of business {corp_num}, {corp_name}'
            logger.error(error_msg_minimal)
            status_service.update_flow_status(flow_name='corps-flow',
                                              corp_num=corp_num,
                                              corp_name=corp_name,
                                              corp_type=corp_type,
                                              filings_count=filings_count,
                                              processed_status=ProcessingStatuses.PARTIAL,
                                              failed_event_id=event_id,
                                              failed_event_file_type=event_filing_type,
                                              last_error=error_msg)
            raise CustomException(error_msg_minimal)
        except InvalidRequestError as err:
            error_msg = f'error loading business InvalidRequestError: {corp_num}, {corp_name}, {err}'
            error_msg_minimal = f'error loading business InvalidRequestError: {corp_num}, {corp_name}'
            logger.error(error_msg_minimal)
            status_service.update_flow_status(flow_name='corps-flow',
                                              corp_num=corp_num,
                                              corp_name=corp_name,
                                              corp_type=corp_type,
                                              filings_count=filings_count,
                                              processed_status=ProcessingStatuses.FAILED,
                                              failed_event_id=event_id,
                                              failed_event_file_type=event_filing_type,
                                              last_error=error_msg)
            logger.info(f'filing processed: {filing_processed}')
            logger.info('lear db rollback')
            db_lear.session.rollback()

            raise CustomException(error_msg_minimal)
        except Exception as err:
            error_msg = f'error loading business {corp_num}, {corp_name}, {err}'
            error_msg_minimal = f'error loading business {corp_num}, {corp_name}'
            logger.error(error_msg_minimal)
            status_service.update_flow_status(flow_name='corps-flow',
                                              corp_num=corp_num,
                                              corp_name=corp_name,
                                              corp_type=corp_type,
                                              filings_count=filings_count,
                                              processed_status=ProcessingStatuses.FAILED,
                                              failed_event_id=event_id,
                                              failed_event_file_type=event_filing_type,
                                              last_error=error_msg)
            logger.info(f'filing processed: {filing_processed}')
            logger.info('lear db rollback')
            db_lear.session.rollback()

            raise CustomException(error_msg_minimal)



@flow(
    name="Corps-Migrate-ETL",
    description="Migrate corporation data through ETL process",
    version="1.0",
    log_prints=True
)
def migrate_flow():
    # setup
    config = get_config()
    db_colin_engine = colin_init(config)
    FLASK_APP, db_lear = lear_init(config)

    unprocessed_corps = get_unprocessed_corps(config, db_colin_engine)
    print(f"Found {len(unprocessed_corps)} corps to process")

    # Submit all event filing tasks in parallel
    event_filing_futures = []
    for corp in unprocessed_corps:
        future = get_event_filing_data.submit(
            config=config,
            colin_db_engine=db_colin_engine,
            unprocessed_corp_dict=corp
        )
        event_filing_futures.append(future)

    # Process results and submit cleaning tasks
    clean_futures = []
    for future in event_filing_futures:
        data = future.result()  # Wait for result
        if data:
            clean_future = clean_event_filing_data.submit(
                config=config,
                colin_db_engine=db_colin_engine,
                event_filing_data_dict=data
            )
            clean_futures.append(clean_future)

    # Process cleaning results and submit transform tasks
    transform_futures = []
    for future in clean_futures:
        data = future.result()  # Wait for result
        if data:
            transform_future = transform_event_filing_data.submit(
                config=config,
                colin_db_engine=db_colin_engine,
                event_filing_data_dict=data
            )
            transform_futures.append(transform_future)

    # Process transform results and submit load tasks
    load_futures = []
    for future in transform_futures:
        data = future.result()  # Wait for result
        if data:
            load_future = load_event_filing_data.submit(
                config=config,
                app=FLASK_APP,
                colin_db_engine=db_colin_engine,
                db_lear=db_lear,
                event_filing_data_dict=data
            )
            load_futures.append(load_future)

    # Wait for all loads to complete
    for future in load_futures:
        future.result()


if __name__ == "__main__":
    migrate_flow()


# if __name__ == "__main__":
#     # Create deployment with schedule
#     deployment = migrate_flow.to_deployment(
#         name="corps-migration",
#         interval=timedelta(seconds=15),  # Run every 15 seconds
#         tags=["corps-migration"]
#     )

#     # Start serving the deployment
#     serve(deployment)
