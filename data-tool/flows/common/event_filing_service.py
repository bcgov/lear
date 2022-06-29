from contextlib import suppress
from enum import Enum

import pandas as pd
from sqlalchemy import engine, text
from .firm_queries import get_firm_event_filing_data_query, \
                          get_firm_event_filing_corp_party_data_query, \
                          get_firm_event_filing_office_data_query
from .query_utils import convert_result_set_to_dict


class RegistrationEventFilings(str, Enum):
    FILE_FRREG = 'FILE_FRREG'
    CONVFMREGI_FRREG = 'CONVFMREGI_FRREG'

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_

class ChangeRegistrationEventFilings(str, Enum):
    CONVFMACP_FRMEM = 'CONVFMACP_FRMEM'
    #TODO currently has no event data.  need to determine what to do with these event/filing types
    # CONVFMMISS_FRADD = 'CONVFMMISS_FRADD'
    # CONVFMMISS_FRCHG = 'CONVFMMISS_FRCHG'
    # CONVFMMISS_FRMEM = 'CONVFMMISS_FRMEM'
    # CONVFMMISS_FRNAT = 'CONVFMMISS_FRNAT'
    # CONVFMRCP_FRMEM = 'CONVFMRCP_FRMEM'
    CONVFMNC_FRCHG = 'CONVFMNC_FRCHG'
    CONVFMREGI_FRCHG = 'CONVFMREGI_FRCHG'
    CONVFMREGI_FRMEM = 'CONVFMREGI_FRMEM'
    FILE_ADDGP = 'FILE_ADDGP'
    FILE_ADDSP = 'FILE_ADDSP'
    FILE_CHGGP = 'FILE_CHGGP'
    FILE_CHGSP = 'FILE_CHGSP'

    FILE_FRADD = 'FILE_FRADD'
    FILE_FRCHG = 'FILE_FRCHG'
    FILE_FRMEM = 'FILE_FRMEM'

    FILE_FRNAM = 'FILE_FRNAM'
    FILE_FRNAT = 'FILE_FRNAT'
    FILE_MEMGP = 'FILE_MEMGP'
    FILE_NAMGP = 'FILE_NAMGP'
    FILE_NAMSP = 'FILE_NAMSP'
    FILE_NATGP = 'FILE_NATGP'
    FILE_NATSP = 'FILE_NATSP'

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_

class DissolutionEventFilings(str, Enum):
    CONVFMDISS_FRDIS = 'CONVFMDISS_FRDIS'
    FILE_DISGP = 'FILE_DISGP'
    FILE_DISSP = 'FILE_DISSP'
    FILE_FRDIS = 'FILE_FRDIS'
    FILE_LLREG = 'FILE_LLREG'

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_

class OtherEventFilings(str, Enum):
    ADMIN_ADMCF = 'ADMIN_ADMCF'

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


EVENT_FILING_LEAR_TARGET_MAPPING = {
    RegistrationEventFilings.FILE_FRREG: 'registration',
    RegistrationEventFilings.CONVFMREGI_FRREG: 'registration',

    ChangeRegistrationEventFilings.CONVFMACP_FRMEM: 'changeOfRegistration',
    #TODO currently has no event data.  need to determine what to do with these event/filing types
    # ChangeRegistrationEventFilings.CONVFMMISS_FRADD: 'changeOfRegistration',
    # ChangeRegistrationEventFilings.CONVFMMISS_FRCHG: 'changeOfRegistration',
    # ChangeRegistrationEventFilings.CONVFMMISS_FRMEM: 'changeOfRegistration',
    # ChangeRegistrationEventFilings.CONVFMMISS_FRNAT: 'changeOfRegistration',
    # ChangeRegistrationEventFilings.CONVFMRCP_FRMEM: 'changeOfRegistration',
    ChangeRegistrationEventFilings.CONVFMNC_FRCHG: 'changeOfRegistration',
    ChangeRegistrationEventFilings.CONVFMREGI_FRCHG: 'changeOfRegistration',
    ChangeRegistrationEventFilings.CONVFMREGI_FRMEM: 'changeOfRegistration',

    ChangeRegistrationEventFilings.FILE_ADDGP: 'changeOfRegistration',
    ChangeRegistrationEventFilings.FILE_ADDSP: 'changeOfRegistration',
    ChangeRegistrationEventFilings.FILE_CHGGP: 'changeOfRegistration',
    ChangeRegistrationEventFilings.FILE_CHGSP: 'changeOfRegistration',

    ChangeRegistrationEventFilings.FILE_FRADD: 'changeOfRegistration',
    ChangeRegistrationEventFilings.FILE_FRCHG: 'changeOfRegistration',
    ChangeRegistrationEventFilings.FILE_FRMEM: 'changeOfRegistration',

    ChangeRegistrationEventFilings.FILE_FRNAM: 'changeOfRegistration',
    ChangeRegistrationEventFilings.FILE_FRNAT: 'changeOfRegistration',
    ChangeRegistrationEventFilings.FILE_MEMGP: 'changeOfRegistration',
    ChangeRegistrationEventFilings.FILE_NAMGP: 'changeOfRegistration',
    ChangeRegistrationEventFilings.FILE_NAMSP: 'changeOfRegistration',
    ChangeRegistrationEventFilings.FILE_NATGP: 'changeOfRegistration',
    ChangeRegistrationEventFilings.FILE_NATSP: 'changeOfRegistration',

    DissolutionEventFilings.CONVFMDISS_FRDIS: 'dissolution',
    DissolutionEventFilings.FILE_DISGP: 'dissolution',
    DissolutionEventFilings.FILE_DISSP: 'dissolution',
    DissolutionEventFilings.FILE_FRDIS: 'dissolution',
    DissolutionEventFilings.FILE_LLREG: 'dissolution',

    OtherEventFilings.ADMIN_ADMCF: 'conversion'
}


class EventFilingService:


    def __init__(self, db_engine: engine, config):
        self.db_engine = db_engine
        self.config= config


    def get_filing_data(self,
                        corp_num: str,
                        event_id: int,
                        event_file_type: str,
                        prev_event_filing_data: dict,
                        prev_event_ids: list):
        with self.db_engine.connect() as conn:
            # get base aggregated registration data that fits on one row
            sql_text = get_firm_event_filing_data_query(corp_num, event_id)
            rs = conn.execute(sql_text)
            event_filing_data_dict = convert_result_set_to_dict(rs)
            event_filing_data_dict = event_filing_data_dict[0]
            event_filing_data_dict['event_file_type'] = event_file_type
            with suppress(IndexError, KeyError, TypeError):
                event_filing_data_dict['target_lear_filing_type'] = EVENT_FILING_LEAR_TARGET_MAPPING[event_file_type]

            corp_name = event_filing_data_dict['cn_corp_name']
            if (corp_name_prefix := self.config.CORP_NAME_PREFIX):
                corp_name = f'{corp_name}{corp_name_prefix}'
            event_filing_data_dict['cn_corp_name'] = corp_name

            # get corp party data
            sql_text = get_firm_event_filing_corp_party_data_query(corp_num, event_id, prev_event_ids, event_filing_data_dict)
            rs = conn.execute(sql_text)
            event_filing_corp_party_data_dict = convert_result_set_to_dict(rs)
            event_filing_data_dict['corp_parties'] = event_filing_corp_party_data_dict

            # get office data
            sql_text = get_firm_event_filing_office_data_query(corp_num, event_id)
            rs = conn.execute(sql_text)
            event_filing_office_data_dict = convert_result_set_to_dict(rs)
            event_filing_data_dict['offices'] = event_filing_office_data_dict

            if prev_event_filing_data:
                event_filing_data_dict['prev_event_filing_data'] = prev_event_filing_data
            else:
                event_filing_data_dict['prev_event_filing_data'] = {}

            return event_filing_data_dict


    def get_event_filing_data(self,
                              corp_num: str,
                              event_id: int,
                              event_file_type: str,
                              prev_event_filing_data: dict,
                              prev_event_ids: list):
        return self.get_filing_data(corp_num,
                                    event_id,
                                    event_file_type,
                                    prev_event_filing_data,
                                    prev_event_ids)


    def get_event_filing_is_supported(self, event_file_type: str):
        if RegistrationEventFilings.has_value(event_file_type) or \
                ChangeRegistrationEventFilings.has_value(event_file_type) or \
                DissolutionEventFilings.has_value(event_file_type) or \
                OtherEventFilings.has_value(event_file_type):
            return True
