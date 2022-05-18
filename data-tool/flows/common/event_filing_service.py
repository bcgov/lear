import pandas as pd
from sqlalchemy import engine, text
from .firm_queries import get_firm_event_filing_data_query, \
                          get_firm_event_filing_corp_party_data_query, \
                          get_firm_event_filing_office_data_query
from .query_utils import convert_result_set_to_dict

class EventFilingService:
    def __init__(self, db_engine: engine):
        self.db_engine = db_engine

    def get_registration_filing_data(self, corp_num: str, event_id: int):
        with self.db_engine.connect() as conn:

            # get base aggregated registration data that fits on one row
            sql_text = get_firm_event_filing_data_query(corp_num, event_id)
            rs = conn.execute(sql_text)
            event_filing_data_dict = convert_result_set_to_dict(rs)
            event_filing_data_dict = event_filing_data_dict[0]
            # todo remove next 3 lines - for testing purposes only
            corp_name = event_filing_data_dict['cn_corp_name']
            corp_name = f'{corp_name} - IMPORT_TEST'
            event_filing_data_dict['cn_corp_name'] = corp_name

            # get corp party data
            sql_text = get_firm_event_filing_corp_party_data_query(corp_num, event_id)
            rs = conn.execute(sql_text)
            event_filing_corp_party_data_dict = convert_result_set_to_dict(rs)
            event_filing_data_dict['corp_parties'] = event_filing_corp_party_data_dict

            # get office data
            sql_text = get_firm_event_filing_office_data_query(corp_num, event_id)
            rs = conn.execute(sql_text)
            event_filing_office_data_dict = convert_result_set_to_dict(rs)
            event_filing_data_dict['offices'] = event_filing_office_data_dict

            return event_filing_data_dict

    def get_event_filing_data(self, corp_num: str, event_id: int, event_file_type: str):
        if event_file_type == 'FILE_FRREG':
            return self.get_registration_filing_data(corp_num, event_id)

        return None

    def get_event_filing_is_supported(self, event_file_type: str):
        if event_file_type == 'FILE_FRREG':
            return True

        return False
