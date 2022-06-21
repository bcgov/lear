from datetime import datetime
from enum import Enum

from sqlalchemy import engine, text

class ProcessingStatuses(str, Enum):
    PROCESSING = 'PROCESSING'
    FAILED = 'FAILED'
    PARTIAL = 'PARTIAL'
    COMPLETED = 'COMPLETED'

class ProcessingStatusService:
    def __init__(self, data_load_env, db_engine: engine):
        self.db_engine = db_engine
        self.data_load_env = data_load_env

    def update_flow_status(self,
                           flow_name: str,
                           corp_num:str,
                           processed_status: str,
                           corp_name=None,
                           last_processed_event_id=None,
                           failed_event_id=None,
                           failed_event_file_type=None,
                           last_error=None):

        dynamic_insert_cols = self.get_dynamic_insert_cols(corp_name,
                                                           processed_status,
                                                           last_processed_event_id,
                                                           failed_event_id,
                                                           failed_event_file_type,
                                                           last_error)

        dynamic_insert_values = self.get_dynamic_insert_values(corp_name,
                                                               processed_status,
                                                               last_processed_event_id,
                                                               failed_event_id,
                                                               failed_event_file_type,
                                                               last_error)

        do_update_query = self.get_do_update_query(corp_name,
                                                   processed_status,
                                                   last_processed_event_id,
                                                   failed_event_id,
                                                   failed_event_file_type,
                                                   last_error)

        dynamic_query_params = self.get_dynamic_query_params(corp_name,
                                                             processed_status,
                                                             last_processed_event_id,
                                                             failed_event_id,
                                                             failed_event_file_type,
                                                             last_error)


        query = f"""
            insert into corp_processing ({dynamic_insert_cols})
            VALUES ({dynamic_insert_values})
            ON CONFLICT (corp_num, flow_name, environment)
                {do_update_query}
        """

        current_date = datetime.now()

        with self.db_engine.connect() as conn:
            sql_text = text(query)
            rs = conn.execute(sql_text,
                              corp_num=corp_num,
                              flow_name=flow_name,
                              create_date=current_date,
                              last_modified=current_date,
                              environment=self.data_load_env,
                              **dynamic_query_params)


    def get_dynamic_insert_cols(self,
                                  corp_name: str,
                                  processed_status: str,
                                  last_processed_event_id=None,
                                  failed_event_id=None,
                                  failed_event_file_type=None,
                                  last_error=None):

        query = "corp_num, flow_name, create_date, last_modified "

        if corp_name:
            query = f'{query}, corp_name'
        if processed_status:
            query = f'{query}, processed_status'
        if self.data_load_env:
            query = f'{query}, environment'
        if last_error:
            query = f'{query}, last_error'
        if last_processed_event_id:
            query = f'{query}, last_processed_event_id'
        if failed_event_id:
            query = f'{query}, failed_event_id'
        if failed_event_file_type:
            query = f'{query}, failed_event_file_type'

        return query


    def get_dynamic_insert_values(self,
                                  corp_name: str,
                                  processed_status: str,
                                  last_processed_event_id=None,
                                  failed_event_id=None,
                                  failed_event_file_type=None,
                                  last_error=None):

        query = ":corp_num, :flow_name, :create_date, :last_modified "

        if corp_name:
            query = f'{query}, :corp_name'
        if processed_status:
            query = f'{query}, :processed_status'
        if self.data_load_env:
            query = f'{query}, :environment'
        if last_error:
            query = f'{query}, :last_error'
        if last_processed_event_id:
            query = f'{query}, :last_processed_event_id'
        if failed_event_id:
            query = f'{query}, :failed_event_id'
        if failed_event_file_type:
            query = f'{query}, :failed_event_file_type'

        return query


    def get_do_update_query(self,
                           corp_name: str,
                           processed_status: str,
                           last_processed_event_id=None,
                           failed_event_id=None,
                           failed_event_file_type=None,
                           last_error=None):

        query = "DO UPDATE SET environment = :environment, last_modified = :last_modified"

        if corp_name:
            query = f'{query}, corp_name = :corp_name'
        if processed_status:
            query = f'{query}, processed_status = :processed_status'
        if last_error:
            query = f'{query}, last_error = :last_error'
        if last_processed_event_id:
            query = f'{query}, last_processed_event_id = :last_processed_event_id'
        if failed_event_id:
            query = f'{query}, failed_event_id = :failed_event_id'
        if failed_event_file_type:
            query = f'{query}, failed_event_file_type = :failed_event_file_type'

        query = f'{query};'
        return query


    def get_dynamic_query_params(self,
                                 corp_name: str,
                                 processed_status: str,
                                 last_processed_event_id=None,
                                 failed_event_id=None,
                                 failed_event_file_type=None,
                                 last_error=None) -> dict:

        params_dict = {}

        if corp_name:
            params_dict['corp_name'] = corp_name
        if processed_status:
            params_dict['processed_status'] = processed_status
        if last_error:
            params_dict['last_error'] = last_error
        if last_processed_event_id:
            params_dict['last_processed_event_id'] = last_processed_event_id
        if failed_event_id:
            params_dict['failed_event_id'] = failed_event_id
        if failed_event_file_type:
            params_dict['failed_event_file_type'] = failed_event_file_type

        return params_dict
