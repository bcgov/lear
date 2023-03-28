import pandas as pd
import prefect
from legal_api.models import Business, Comment
from prefect import task, Flow, unmapped, flow, allow_failure
from prefect.task_runners import ConcurrentTaskRunner, SequentialTaskRunner

from config import get_named_config
from common.firm_queries import get_unprocessed_firms_query
from common.event_filing_service import EventFilingService, RegistrationEventFilings
from common.filing_data_cleaning_utils import clean_naics_data, clean_corp_party_data, clean_offices_data, \
    clean_corp_data, clean_event_data
from common.processing_status_service import ProcessingStatusService, ProcessingStatuses
from custom_filer.filer import process_filing
from common.custom_exceptions import CustomException, CustomUnsupportedTypeException
from common.lear_data_utils import populate_filing_json_from_lear, get_colin_event, populate_filing
from common.filing_json_factory_service import FilingJsonFactoryService
from common.filing_data_utils import get_is_paper_only, get_previous_event_ids, \
    get_processed_event_ids, get_event_info_to_retrieve, is_in_lear
from sqlalchemy.exc import InvalidRequestError
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


@task(name='get_unprocessed_firms')
def get_unprocessed_firms(config, db_engine: engine):
    logger = prefect.get_run_logger()
    query = get_unprocessed_firms_query(config.DATA_LOAD_ENV)
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
            status_service.update_flow_status(flow_name='sp-gp-flow',
                                              corp_num=corp_num,
                                              processed_status=ProcessingStatuses.PROCESSING)
    return raw_data_dict


@task(name='get_event_filing_data')
def get_event_filing_data(config, colin_db_engine: engine, unprocessed_firm_dict: dict):
    logger = prefect.get_run_logger()
    status_service = ProcessingStatusService(config.DATA_LOAD_ENV, colin_db_engine)
    event_filing_service = EventFilingService(colin_db_engine, config)
    corp_num = unprocessed_firm_dict.get('corp_num')
    corp_name = ''
    # print(f'get event filing data for {corp_num}')

    try:
        event_ids = unprocessed_firm_dict.get('event_ids')
        correction_event_ids = unprocessed_firm_dict.get('correction_event_ids')
        events_ids_to_process, event_filing_types_to_process = get_event_info_to_retrieve(unprocessed_firm_dict)
        processed_events_ids = get_processed_event_ids(unprocessed_firm_dict)
        unprocessed_firm_dict['retrieved_events_cnt'] = len(events_ids_to_process)
        event_filing_data_arr = []

        corp_comments = event_filing_service.get_corp_comments_data(corp_num)
        unprocessed_firm_dict['corp_comments'] = corp_comments
        unprocessed_firm_dict['correctionEventFilingMappings'] = {}
        correction_event_filing_mappings = unprocessed_firm_dict['correctionEventFilingMappings']

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

        unprocessed_firm_dict['event_filing_data'] = event_filing_data_arr

    except Exception as err:
        error_msg = f'error getting event filing data {corp_num}, {corp_name}, {err}'
        logger.error(error_msg)
        status_service.update_flow_status(flow_name='sp-gp-flow',
                                          corp_num=corp_num,
                                          corp_name=corp_name,
                                          processed_status=ProcessingStatuses.FAILED,
                                          failed_event_id=event_id,
                                          failed_event_file_type=event_file_type,
                                          last_error=error_msg)
        raise CustomException(error_msg, event_filing_data_dict)

    return unprocessed_firm_dict


@task(name='clean_event_filing_data')
def clean_event_filing_data(config, colin_db_engine: engine, event_filing_data_dict: dict):
    logger = prefect.get_run_logger()
    status_service = ProcessingStatusService(config.DATA_LOAD_ENV, colin_db_engine)
    corp_num = event_filing_data_dict['corp_num']
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
                clean_naics_data(filing_data)
                clean_corp_party_data(filing_data)
                clean_offices_data(filing_data)
    except Exception as err:
        error_msg = f'error cleaning business {corp_num}, {corp_name}, {err}'
        logger.error(error_msg)
        status_service.update_flow_status(flow_name='sp-gp-flow',
                                          corp_num=corp_num,
                                          corp_name=corp_name,
                                          processed_status=ProcessingStatuses.FAILED,
                                          failed_event_id=event_id,
                                          failed_event_file_type=event_filing_type,
                                          last_error=error_msg)
        raise CustomException(error_msg, event_filing_data_dict)

    return event_filing_data_dict


@task(name='transform_event_filing_data')
def transform_event_filing_data(config, colin_db_engine: engine, event_filing_data_dict: dict):
    logger = prefect.get_run_logger()
    status_service = ProcessingStatusService(config.DATA_LOAD_ENV, colin_db_engine)
    corp_num = event_filing_data_dict['corp_num']
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
                firm_filing_json_factory_service = FilingJsonFactoryService(event_filing_data)
                filing_json = firm_filing_json_factory_service.get_filing_json()
                event_filing_data['filing_json'] = filing_json
    except Exception as err:
        error_msg = f'error transforming business {corp_num}, {corp_name}, {err}'
        logger.error(error_msg)
        status_service.update_flow_status(flow_name='sp-gp-flow',
                                          corp_num=corp_num,
                                          corp_name=corp_name,
                                          processed_status=ProcessingStatuses.FAILED,
                                          failed_event_id=event_id,
                                          failed_event_file_type=event_filing_type,
                                          last_error=error_msg)
        raise CustomException(error_msg, event_filing_data_dict)

    return event_filing_data_dict


@task(name='load_event_filing_data')
def load_event_filing_data(config, app: any, colin_db_engine: engine, db_lear, event_filing_data_dict: dict):
    logger = prefect.get_run_logger()
    status_service = ProcessingStatusService(config.DATA_LOAD_ENV, colin_db_engine)
    corp_num = event_filing_data_dict['corp_num']
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
                    error_msg = f'could not finish processing this firm as there is an unsupported event/filing type: {event_filing_type}'
                    raise CustomUnsupportedTypeException(f'{error_msg}', filing_data)

                if not event_filing_data['is_in_lear'] and not event_filing_data['skip_filing']:
                    # the corp_processing table should already track whether an event/filing has been processed and
                    # saved to lear but just to be safe a final check against lear is made to ensure the event/filing
                    # is not already in lear
                    # colin_event = get_colin_event(db_lear, event_id)
                    # if colin_event:
                    #     error_msg = f'colin event id ({event_id}) already exists in lear: {event_filing_type}'
                    #     raise CustomException(f'{error_msg}', filing_data)

                    business = None
                    if not RegistrationEventFilings.has_value(event_filing_type):
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
                        corp_type = event_filing_data_dict['corp_type_cd']
                        filings_count = event_filing_data_dict['cnt']
                        status_service.update_flow_status(flow_name='sp-gp-flow',
                                                          corp_num=corp_num,
                                                          corp_name=corp_name,
                                                          corp_type=corp_type,
                                                          filings_count=filings_count,
                                                          processed_status=ProcessingStatuses.COMPLETED,
                                                          last_processed_event_id=event_id)
                    else:
                        status_service.update_flow_status(flow_name='sp-gp-flow',
                                                          corp_num=corp_num,
                                                          corp_name=corp_name,
                                                          processed_status=ProcessingStatuses.PROCESSING,
                                                          last_processed_event_id=event_id)
        except CustomUnsupportedTypeException as err:
            error_msg = f'Partial loading of business {corp_num}, {corp_name}, {err}'
            logger.error(error_msg)
            status_service.update_flow_status(flow_name='sp-gp-flow',
                                              corp_num=corp_num,
                                              corp_name=corp_name,
                                              corp_type=corp_type,
                                              filings_count=filings_count,
                                              processed_status=ProcessingStatuses.PARTIAL,
                                              failed_event_id=event_id,
                                              failed_event_file_type=event_filing_type,
                                              last_error=error_msg)
            raise err
        except InvalidRequestError as err:
            error_msg = f'error loading business InvalidRequestError: {corp_num}, {corp_name}, {err}'
            logger.error(error_msg)
            status_service.update_flow_status(flow_name='sp-gp-flow',
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

            raise err
        except Exception as err:
            error_msg = f'error loading business {corp_num}, {corp_name}, {err}'
            logger.error(error_msg)
            status_service.update_flow_status(flow_name='sp-gp-flow',
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

            raise err



# @flow(name="SP-GP-Migrate-ETL", task_runner=ConcurrentTaskRunner())
# @flow(name="SP-GP-Migrate-ETL", task_runner=DaskTaskRunner())
@flow(name="SP-GP-Migrate-ETL", task_runner=SequentialTaskRunner())
def migrate_flow():
    # setup
    config = get_config()
    db_colin_engine = colin_init(config)
    FLASK_APP, db_lear = lear_init(config)

    unprocessed_firms = get_unprocessed_firms(config, db_colin_engine)

    # get event/filing related data for each firm
    event_filing_data = get_event_filing_data.map(unmapped(config),
                                                  colin_db_engine=unmapped(db_colin_engine),
                                                  unprocessed_firm_dict=unprocessed_firms)

    # clean/validate filings for a given business
    cleaned_event_filing_data = clean_event_filing_data.map(unmapped(config),
                                                            unmapped(db_colin_engine),
                                                            event_filing_data)

    # transform data to appropriate format in preparation for data loading into LEAR
    transformed_event_filing_data = transform_event_filing_data.map(unmapped(config),
                                                                    unmapped(db_colin_engine),
                                                                    cleaned_event_filing_data)

    # load all filings for a given business sequentially
    # if a filing fails, flag business as failed indicating which filing it failed at
    loaded_event_filing_data = load_event_filing_data.map(unmapped(config),
                                                          unmapped(FLASK_APP),
                                                          unmapped(db_colin_engine),
                                                          unmapped(db_lear),
                                                          transformed_event_filing_data)


if __name__ == "__main__":
    migrate_flow()
