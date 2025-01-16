import copy

from contextlib import suppress
from enum import Enum

from legal_api.core import Filing as FilingCore
from sqlalchemy import engine, text
from .corp_queries import get_corp_event_filing_data_query, \
    get_corp_event_filing_corp_party_data_query, \
    get_corp_event_filing_office_data_query, get_corp_event_names_data_query, \
    get_share_structure_data_query, get_corp_event_jurisdiction_data_query
from flows.common.query_utils import convert_result_set_to_dict
from flows.common.shared_queries import get_corp_comments_data_query


class NewBusinessEventFilings(str, Enum):
    # Incorporation Application
    FILE_ICORP = 'FILE_ICORP'
    FILE_ICORU = 'FILE_ICORU'
    FILE_ICORC = 'FILE_ICORC'

    # Continuation In
    FILE_CONTI = 'FILE_CONTI'
    FILE_CONTU = 'FILE_CONTU'
    FILE_CONTC = 'FILE_CONTC'

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


class OtherEventFilings(str, Enum):
    FILE_ANNBC = 'FILE_ANNBC'

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


EVENT_FILING_LEAR_TARGET_MAPPING = {
    NewBusinessEventFilings.FILE_ICORP: FilingCore.FilingTypes.INCORPORATIONAPPLICATION.value,
    NewBusinessEventFilings.FILE_ICORU: FilingCore.FilingTypes.INCORPORATIONAPPLICATION.value,
    NewBusinessEventFilings.FILE_ICORC: FilingCore.FilingTypes.INCORPORATIONAPPLICATION.value,
    NewBusinessEventFilings.FILE_CONTI: FilingCore.FilingTypes.CONTINUATIONIN.value,
    NewBusinessEventFilings.FILE_CONTU: FilingCore.FilingTypes.CONTINUATIONIN.value,
    NewBusinessEventFilings.FILE_CONTC: FilingCore.FilingTypes.CONTINUATIONIN.value,

    OtherEventFilings.FILE_ANNBC: FilingCore.FilingTypes.ANNUALREPORT.value
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
            sql_text = get_corp_event_filing_data_query(corp_num, event_id)
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

            # get names translations and other names types data
            sql_text = get_corp_event_names_data_query(corp_num, event_id)
            rs = conn.execute(sql_text)
            event_filing_corp_names_data_dict = convert_result_set_to_dict(rs)
            event_filing_data_dict['corp_names'] = event_filing_corp_names_data_dict

            # get corp party data
            sql_text = get_corp_event_filing_corp_party_data_query(corp_num, event_id, prev_event_ids, event_filing_data_dict)
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
            include_prev_active_offices = event_file_type == 'FILE_ANNBC'
            sql_text = get_corp_event_filing_office_data_query(corp_num, event_id, include_prev_active_offices)
            rs = conn.execute(sql_text)
            event_filing_office_data_dict = convert_result_set_to_dict(rs)
            event_filing_data_dict['offices'] = event_filing_office_data_dict

            # get share structure data
            sql_text = get_share_structure_data_query(corp_num, event_id)
            rs = conn.execute(sql_text)
            temp_share_struct_data_dict = convert_result_set_to_dict(rs)
            event_filing_share_structure_data_dict = self.parse_share_struct_data(temp_share_struct_data_dict)
            event_filing_data_dict['share_structure'] = event_filing_share_structure_data_dict

            # get jurisdiction data
            sql_text = get_corp_event_jurisdiction_data_query(corp_num, event_id)
            rs = conn.execute(sql_text)
            event_filing_jurisdiction_data_dict = convert_result_set_to_dict(rs)
            if len(event_filing_jurisdiction_data_dict) > 0:
                event_filing_data_dict['jurisdiction'] = event_filing_jurisdiction_data_dict[0]

            if prev_event_filing_data:
                event_filing_data_dict['prev_event_filing_data'] = prev_event_filing_data
            else:
                event_filing_data_dict['prev_event_filing_data'] = {}

            # if CorrectionEventFilings.has_value(event_file_type):
            #     if event_id in correction_event_filing_mappings:
            #         event_filing_data_dict['corrected_event_filing_info'] = correction_event_filing_mappings[event_id]
            #     else:
            #         event_filing_data_dict['skip_filing'] = True

            # check if corrected event/filing
            if correction_event_ids and len(correction_event_ids) > 0:
                is_corrected_event_filing, correction_event_id = \
                    self.is_corrected_event_filing(event_filing_data_dict, correction_event_ids)
                if is_corrected_event_filing:
                    event_filing_data_dict['is_corrected_event_filing'] = True
                    event_filing_data_dict['correction_event_id'] = correction_event_ids
                    return event_filing_data_dict, is_corrected_event_filing, correction_event_id

            return event_filing_data_dict, False, None


    def parse_share_struct_data(self, share_struct_data_dict: dict):
        share_classes_dict = []
        curr_share_class_id = None

        for share_class in share_struct_data_dict:
            share_class_id = share_class['ssc_share_class_id']
            if curr_share_class_id != share_class_id:
                # first time to parse share class
                matching_series = \
                    [copy.deepcopy(x) for x in share_struct_data_dict if x['srs_share_class_id'] == share_class_id]
                share_class['share_series'] = matching_series
                share_classes_dict.append(copy.deepcopy(share_class))
                curr_share_class_id = share_class_id

        result_dict = { 'share_classes': share_classes_dict }
        return result_dict


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
        if NewBusinessEventFilings.has_value(event_file_type) or \
                OtherEventFilings.has_value(event_file_type):
            return True

        return False
