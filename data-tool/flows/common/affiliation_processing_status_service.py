from enum import Enum

from sqlalchemy import engine, text

class ProcessingStatuses(str, Enum):
    NOT_PROCESSED = 'NOT_PROCESSED'
    FAILED = 'FAILED'
    COMPLETED = 'COMPLETED'

class AffiliationProcessingStatusService:
    def __init__(self, data_load_env, db_engine: engine):
        self.db_engine = db_engine
        self.data_load_env = data_load_env

    def update_status(self, corp_num:str, account_id: int, processed_status: str, last_error=None):
        query = f"""
            update affiliation_processing 
            set processed_status = :processed_status,
                last_error = :last_error
            where environment = :environment
                and corp_num = :corp_num 
                and account_id = :account_id 
        """

        with self.db_engine.connect() as conn:
            sql_text = text(query)
            conn.execute(sql_text,
                              environment=self.data_load_env,
                              corp_num=corp_num,
                              account_id=account_id,
                              processed_status=processed_status,
                              last_error=last_error)



