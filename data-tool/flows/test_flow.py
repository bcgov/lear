from datetime import timedelta

import pandas as pd
import prefect
from prefect import task, Flow, unmapped
from prefect.schedules import IntervalSchedule
from prefect.tasks.postgres.postgres import PostgresFetch, PostgresExecute
from prefect import Parameter
from config import get_named_config
from prefect.triggers import all_successful, all_failed, all_finished
from common.transform_utils import transform_address, transform_business
from common.custom_exceptions import CustomException
from tasks.task_utils import LearInitTask

fetch_colin_data_task = PostgresFetch(
                           name='get_colin_data',
                           db_name='colin-mig-data',
                           user='postgres',
                           host='localhost',
                           port=5432,
                           fetch='all',
                           commit=True,
                           max_retries=100,
                           retry_delay=timedelta(seconds=5))

update_processing_status = PostgresExecute(
                            name='update_status',
                            db_name='colin-mig-data',
                            user='postgres',
                            host='localhost',
                            port=5432,
                            commit=True)

lear_init_task = LearInitTask(name='init_lear', flask_app_name='test-etl')

@task
def get_config():
    config = get_named_config()
    return config

@task(name='config_value')
def get_config_value_by_key(config, config_key):
    result = getattr(config, config_key)
    return result


@task(name='colin_query', )
def get_fetch_colin_query(start_date: str, end_date: str):
    query = f"""
        select c.corp_num, c.corp_type_cd, cn.corp_name, bd.naics_code, bd.description as naics_desc, c.recognition_dts, a.*
        from corporation c
                 join corp_name cn on cn.corp_num = c.corp_num
                 left outer join corp_processing cp on cp.corp_num = c.corp_num
                 join business_description bd on bd.corp_num = c.corp_num
                 join office o ON c.corp_num = o.corp_num
                 JOIN address a ON o.mailing_addr_id = a.addr_id
        where 
            c.recognition_dts between '{start_date}' and '{end_date}'
            and (a.addr_line_3 is not null and a.addr_line_3 <> '')
            and (cp.flow_name is null or cp.flow_name = 'test-etl')
            and (cp.processed_status = 'FAILED' or cp.processed_status is null)
        order by c.recognition_dts asc;
    """
    return query

@task(name='completed_query', trigger=all_successful)
def get_update_processing_status_to_completed_query(row_dict: dict):
    corp_num = row_dict.get('corp_num')
    query = f"""
        insert into corp_processing (corp_num, flow_name, processed_status)
        VALUES ('{corp_num}', 'test-etl', 'COMPLETED')
        ON CONFLICT (corp_num, flow_name)
            DO UPDATE SET processed_status = 'COMPLETED';
    """
    return query


@task(name='failed_query', trigger=all_failed)
def get_update_processing_status_to_failed_query(ex: CustomException):
    corp_num = ex.data.get('corp_num')
    query = f"""
        insert into corp_processing (corp_num, flow_name, processed_status)
        VALUES ('{corp_num}', 'test-etl', 'FAILED')
        ON CONFLICT (corp_num, flow_name)
            DO UPDATE SET processed_status = 'FAILED';
    """
    return query


@task(name='status_query', trigger=all_finished)
def get_update_processing_status_query(processed_row_result):
    if isinstance(processed_row_result, CustomException):
        status = 'FAILED'
        corp_num = processed_row_result.data.get('corp_num')
    else:
        corp_num = processed_row_result.get('corp_num')
        status = 'COMPLETED'

    query = f"""
        insert into corp_processing (corp_num, flow_name, processed_status)
        VALUES ('{corp_num}', 'test-etl', '{status}')
        ON CONFLICT (corp_num, flow_name)
            DO UPDATE SET processed_status = '{status}';
    """
    return query


@task(name='convert_colin_data')
def convert_colin_data_to_dict(raw_data):
    logger = prefect.context.get("logger")
    columns = list(raw_data[0])
    del raw_data[0]
    df = pd.DataFrame(raw_data, columns=columns)
    raw_data_dict = df.to_dict('records')
    corp_nums = [x.get('corp_num') for x in raw_data_dict]
    logger.info(f'{len(raw_data_dict)} corp_nums to process from colin data: {corp_nums}')
    return raw_data_dict


@task
def transform(row_dict: dict):
    business = transform_business(row_dict)
    address = transform_address(row_dict)
    return (row_dict, business, address)


@task(trigger=all_finished)
def load_row(db, transformed_data):
    logger = prefect.context.get("logger")
    if isinstance(transformed_data, CustomException):
        raise transformed_data

    try:
        row_dict = transformed_data[0]
        business = transformed_data[1]
        address = transformed_data[2]
        db.session.add(address)
        db.session.add(business)
        db.session.commit()
        return row_dict
    except Exception as err:
        db.session.rollback()
        logger.error(f'load row exception {err}, {row_dict}')
        raise CustomException(f'load row exception {err}', row_dict)


@task(trigger=all_successful)
def check_flow_results(load_data_result): # used to trigger flow failure if any corps failed processing
    logger = prefect.context.get("logger")
    logger.info('check_flow_results')


schedule = IntervalSchedule(interval=timedelta(seconds=60))

with Flow("Test-ETL", schedule) as f:

    # params for flow
    start_date = Parameter("start_date", default='2016-04-15')
    end_date = Parameter("end_date", default='2016-04-15')

    # setup
    config = get_config()
    db = lear_init_task(config)

    # get data from colin
    db_pwd_colin_mgr = get_config_value_by_key(config, 'DB_PASSWORD_COLIN_MIGR')
    query = get_fetch_colin_query(start_date, end_date)
    raw_data_results = fetch_colin_data_task(password=db_pwd_colin_mgr,
                                           col_names=True,
                                           query=query)
    raw_data_dict = convert_colin_data_to_dict(raw_data_results)

    # transform colin data to format that can be used for lear
    transformed_data = transform.map(raw_data_dict)

    # load transformed data into lear db
    load_data_result = load_row.map(db=unmapped(db),
                                    transformed_data=transformed_data)

    # update processing status table with corp processing results
    status_queries = get_update_processing_status_query.map(load_data_result)
    status_results = update_processing_status.map(password=unmapped(db_pwd_colin_mgr),
                                                            query=status_queries)

    check_flow_results(load_data_result)
