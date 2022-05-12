from sqlalchemy import engine, text


class ProcessingStatusService:
    def __init__(self, db_engine: engine):
        self.db_engine = db_engine

    def update_flow_status(self, flow_name: str, corp_num:str, corp_name: str, processed_status: str):
        query = f"""
            insert into corp_processing (corp_num, corp_name, flow_name, processed_status)
            VALUES (:corp_num, :corp_name, :flow_name, :processed_status)
            ON CONFLICT (corp_num, flow_name)
                DO UPDATE SET processed_status = :processed_status;
        """

        with self.db_engine.connect() as conn:
            sql_text = text(query)
            rs = conn.execute(sql_text,
                              corp_num=corp_num,
                              corp_name=corp_name,
                              flow_name=flow_name,
                              processed_status=processed_status)



