from contextlib import suppress
from enum import Enum

from legal_api.core import Filing as FilingCore
from sqlalchemy import engine, text
from .firm_queries import get_firm_event_filing_data_query, \
    get_firm_event_filing_corp_party_data_query, \
    get_firm_event_filing_office_data_query
from .query_utils import convert_result_set_to_dict
from .shared_queries import get_corp_comments_data_query


class RegistrationEventFilings(str, Enum):
    FILE_FRREG = 'FILE_FRREG'
    CONVFMREGI_FRREG = 'CONVFMREGI_FRREG'

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_

class ChangeRegistrationEventFilings(str, Enum):
    CONVFMACP_FRMEM = 'CONVFMACP_FRMEM'

    CONVFMMISS_FRACH = 'CONVFMMISS_FRACH'
    CONVFMMISS_FRADD = 'CONVFMMISS_FRADD'
    CONVFMMISS_FRARG = 'CONVFMMISS_FRARG'
    CONVFMMISS_FRCHG = 'CONVFMMISS_FRCHG'
    CONVFMMISS_FRMEM = 'CONVFMMISS_FRMEM'
    CONVFMMISS_FRNAT = 'CONVFMMISS_FRNAT'

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

    CONVFMACP_FRARG = 'CONVFMACP_FRARG'
    CONVFMNC_FRARG = 'CONVFMNC_FRARG'
    CONVFMRCP_FRARG = 'CONVFMRCP_FRARG'
    CONVFMRCP_FRMEM = 'CONVFMRCP_FRMEM'
    CONVFMRCP_NULL = 'CONVFMRCP_NULL'
    FILE_AMDGP = 'FILE_AMDGP'
    FILE_AMDSP = 'FILE_AMDSP'
    FILE_FRACH = 'FILE_FRACH'
    FILE_FRARG = 'FILE_FRARG'

    ADFIRM_NULL = 'ADFIRM_NULL'

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


class CorrectionEventFilings(str, Enum):
    FILE_CORGP = 'FILE_CORGP'
    FILE_CORSP = 'FILE_CORSP'
    FILE_FRCCH = 'FILE_FRCCH'
    FILE_FRCRG = 'FILE_FRCRG'

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


class OtherEventFilings(str, Enum):
    ADMIN_ADMCF = 'ADMIN_ADMCF'
    FILE_FRPBO = 'FILE_FRPBO'

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


EVENT_FILING_LEAR_TARGET_MAPPING = {
    RegistrationEventFilings.FILE_FRREG: FilingCore.FilingTypes.REGISTRATION.value,
    RegistrationEventFilings.CONVFMREGI_FRREG: FilingCore.FilingTypes.REGISTRATION.value,

    ChangeRegistrationEventFilings.CONVFMACP_FRMEM: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,

    ChangeRegistrationEventFilings.CONVFMMISS_FRACH: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.CONVFMMISS_FRADD: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.CONVFMMISS_FRARG: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.CONVFMMISS_FRCHG: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.CONVFMMISS_FRMEM: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.CONVFMMISS_FRNAT: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,

    ChangeRegistrationEventFilings.CONVFMNC_FRCHG: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.CONVFMREGI_FRCHG: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.CONVFMREGI_FRMEM: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,

    ChangeRegistrationEventFilings.FILE_ADDGP: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.FILE_ADDSP: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.FILE_CHGGP: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.FILE_CHGSP: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,

    ChangeRegistrationEventFilings.FILE_FRADD: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.FILE_FRCHG: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.FILE_FRMEM: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,

    ChangeRegistrationEventFilings.FILE_FRNAM: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.FILE_FRNAT: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.FILE_MEMGP: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.FILE_NAMGP: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.FILE_NAMSP: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.FILE_NATGP: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.FILE_NATSP: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,

    ChangeRegistrationEventFilings.CONVFMACP_FRARG: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.CONVFMNC_FRARG: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.CONVFMRCP_FRARG: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.CONVFMRCP_FRMEM: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.CONVFMRCP_NULL: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.FILE_AMDGP: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.FILE_AMDSP: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.FILE_FRACH: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,
    ChangeRegistrationEventFilings.FILE_FRARG: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,

    ChangeRegistrationEventFilings.ADFIRM_NULL: FilingCore.FilingTypes.CHANGEOFREGISTRATION.value,

    DissolutionEventFilings.CONVFMDISS_FRDIS: FilingCore.FilingTypes.DISSOLUTION.value,
    DissolutionEventFilings.FILE_DISGP: FilingCore.FilingTypes.DISSOLUTION.value,
    DissolutionEventFilings.FILE_DISSP: FilingCore.FilingTypes.DISSOLUTION.value,
    DissolutionEventFilings.FILE_FRDIS: FilingCore.FilingTypes.DISSOLUTION.value,
    DissolutionEventFilings.FILE_LLREG: FilingCore.FilingTypes.DISSOLUTION.value,

    CorrectionEventFilings.FILE_CORGP: FilingCore.FilingTypes.CORRECTION.value,
    CorrectionEventFilings.FILE_CORSP: FilingCore.FilingTypes.CORRECTION.value,
    CorrectionEventFilings.FILE_FRCCH: FilingCore.FilingTypes.CORRECTION.value,
    CorrectionEventFilings.FILE_FRCRG: FilingCore.FilingTypes.CORRECTION.value,

    OtherEventFilings.ADMIN_ADMCF: FilingCore.FilingTypes.CONVERSION.value,
    OtherEventFilings.FILE_FRPBO: FilingCore.FilingTypes.PUTBACKON.value
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
                        prev_event_ids: list,
                        correction_event_ids: list,
                        correction_event_filing_mappings):
        with self.db_engine.connect() as conn:
            # get base aggregated registration data that fits on one row
            sql_text = get_firm_event_filing_data_query(corp_num, event_id)
            rs = conn.execute(sql_text)
            event_filing_data_dict = convert_result_set_to_dict(rs)
            event_filing_data_dict = event_filing_data_dict[0]
            event_filing_data_dict['skip_filing'] = False
            event_filing_data_dict['event_file_type'] = event_file_type
            event_filing_data_dict['is_corrected_event_filing'] = False
            if event_file_type in EVENT_FILING_LEAR_TARGET_MAPPING:
                event_filing_data_dict['target_lear_filing_type'] = EVENT_FILING_LEAR_TARGET_MAPPING[event_file_type]
            else:
                event_filing_data_dict['target_lear_filing_type'] = None

            corp_name = event_filing_data_dict['cn_corp_name']
            if (corp_name_suffix := self.config.CORP_NAME_SUFFIX):
                corp_name = f'{corp_name}{corp_name_suffix}'
            event_filing_data_dict['cn_corp_name'] = corp_name

            # get corp party data
            sql_text = get_firm_event_filing_corp_party_data_query(corp_num, event_id, prev_event_ids, event_filing_data_dict)
            rs = conn.execute(sql_text)
            event_filing_corp_party_data_dict = convert_result_set_to_dict(rs)
            if prev_event_filing_data:
                prev_corp_parties = prev_event_filing_data.get('corp_parties')
                for corp_party_dict in event_filing_corp_party_data_dict:
                    prev_corp_party_dict = self.find_prev_corp_party(prev_corp_parties, corp_party_dict)
                    if prev_corp_party_dict:
                        corp_party_dict['cp_appointment_dt'] = prev_corp_party_dict['cp_appointment_dt']

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

            if CorrectionEventFilings.has_value(event_file_type):
                if event_id in correction_event_filing_mappings:
                    event_filing_data_dict['corrected_event_filing_info'] = correction_event_filing_mappings[event_id]
                else:
                    event_filing_data_dict['skip_filing'] = True

            # check if corrected event/filing
            if correction_event_ids and len(correction_event_ids) > 0:
                is_corrected_event_filing, correction_event_id = \
                    self.is_corrected_event_filing(event_filing_data_dict, correction_event_ids)
                if is_corrected_event_filing:
                    event_filing_data_dict['is_corrected_event_filing'] = True
                    event_filing_data_dict['correction_event_id'] = correction_event_ids
                    return event_filing_data_dict, is_corrected_event_filing, correction_event_id

            return event_filing_data_dict, False, None


    def find_prev_corp_party(self, prev_corp_parties: list, corp_party_to_find_dict: dict):
        if (prev_corp_party_dict := next((x for x in prev_corp_parties \
                                         if x['cp_corp_party_id'] == corp_party_to_find_dict['cp_prev_party_id'] \
                                            and x['cp_party_typ_cd'] != 'FCP'), None)) or \
                (prev_corp_party_dict := next((x for x in prev_corp_parties \
                                           if x['cp_corp_party_id'] == corp_party_to_find_dict['cp_corp_party_id'] \
                                              and x['cp_party_typ_cd'] != 'FCP'), None)):
            return prev_corp_party_dict
        return None


    def is_corrected_event_filing(self, event_filing_data_dict, correction_event_ids: list):
        corp_parties = event_filing_data_dict['corp_parties']
        cp_end_event_ids = [x.get('cp_end_event_id') for x in corp_parties]

        offices = event_filing_data_dict['offices']
        o_end_event_ids = [x.get('o_end_event_id') for x in offices]

        bd_end_event_id = event_filing_data_dict.get('bd_end_event_id', None)
        cn_end_event_id = event_filing_data_dict.get('cn_end_event_id', None)
        cs_end_event_id = event_filing_data_dict.get('cs_end_event_id', None)

        for correction_event_id in correction_event_ids:
            if correction_event_id in cp_end_event_ids:
                return True, correction_event_id
            if correction_event_id in o_end_event_ids:
                return True, correction_event_id
            if bd_end_event_id == correction_event_id:
                return True, correction_event_id
            if cn_end_event_id == correction_event_id:
                return True, correction_event_id
            if cs_end_event_id == correction_event_id:
                return True, correction_event_id

        return False, None


    def get_event_filing_data(self,
                              corp_num: str,
                              event_id: int,
                              event_file_type: str,
                              prev_event_filing_data: dict,
                              prev_event_ids: list,
                              correction_event_ids: list,
                              correction_event_filing_mappings):
        return self.get_filing_data(corp_num,
                                    event_id,
                                    event_file_type,
                                    prev_event_filing_data,
                                    prev_event_ids,
                                    correction_event_ids,
                                    correction_event_filing_mappings)


    def get_corp_comments_data(self,
                              corp_num: str):
        with self.db_engine.connect() as conn:
            sql_text = get_corp_comments_data_query(corp_num)
            rs = conn.execute(sql_text)
            corp_comments = convert_result_set_to_dict(rs)
            return corp_comments



    def get_event_filing_is_supported(self, event_file_type: str):
        if RegistrationEventFilings.has_value(event_file_type) or \
                ChangeRegistrationEventFilings.has_value(event_file_type) or \
                DissolutionEventFilings.has_value(event_file_type) or \
                CorrectionEventFilings.has_value(event_file_type) or \
                OtherEventFilings.has_value(event_file_type):
            return True

        return False
