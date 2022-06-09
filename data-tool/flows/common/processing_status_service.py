from datetime import datetime

from sqlalchemy import engine, text


class ProcessingStatusService:
    def __init__(self, data_load_env, db_engine: engine):
        self.db_engine = db_engine
        self.data_load_env = data_load_env

    def update_flow_status(self, flow_name: str,
                           corp_num:str,
                           corp_name: str,
                           processed_status: str,
                           last_processed_event_id=None,
                           failed_event_id=None,
                           failed_event_file_type=None,
                           last_error=None):
        query = f"""
            insert into corp_processing (corp_num, 
                                         corp_name, 
                                         flow_name, 
                                         processed_status,
                                         environment, 
                                         last_error,
                                         last_processed_event_id,
                                         failed_event_id,
                                         failed_event_file_type,
                                         create_date,
                                         last_modified)
            VALUES (:corp_num, 
                    :corp_name, 
                    :flow_name, 
                    :processed_status,
                    :environment, 
                    :last_error,
                    :last_processed_event_id,
                    :failed_event_id,
                    :failed_event_file_type,
                    :create_date,
                    :last_modified)
            ON CONFLICT (corp_num, flow_name, environment)
                DO UPDATE SET corp_name = :corp_name,
                              processed_status = :processed_status,
                              environment = :environment,
                              last_error = :last_error,
                              last_processed_event_id = :last_processed_event_id,
                              failed_event_id = :failed_event_id,  
                              failed_event_file_type = :failed_event_file_type,                              
                              last_modified = :last_modified;
        """

        current_date = datetime.now()

        with self.db_engine.connect() as conn:
            sql_text = text(query)
            rs = conn.execute(sql_text,
                              corp_num=corp_num,
                              corp_name=corp_name,
                              flow_name=flow_name,
                              processed_status=processed_status,
                              environment=self.data_load_env,
                              last_error=last_error,
                              last_processed_event_id=last_processed_event_id,
                              failed_event_id=failed_event_id,
                              failed_event_file_type=failed_event_file_type,
                              create_date=current_date,
                              last_modified=current_date)



