from enum import Enum

import pandas as pd


class AddressFormatType(str, Enum):
    BASIC = 'BAS'
    ADVANCED = 'ADV'
    FOREIGN = 'FOR'

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


def get_certified_by(filing_data: dict):
    user_id = filing_data.get('u_user_id')
    if user_id:
        first_name = filing_data.get('u_first_name')
        middle_name = filing_data.get('u_middle_name')
        last_name = filing_data.get('u_last_name')
        if first_name or middle_name or last_name:
            result = f'{first_name} {middle_name} {last_name}'
            result = result.replace('  ', ' ')
            return result
        return user_id

    return ''


def get_street_additional(address_format_type: str, address_data_dict: dict, address_key_prefix: str):
    result = ''

    if address_format_type == AddressFormatType.FOREIGN:
        addr_line_2_key = f'{address_key_prefix}addr_line_2'
        addr_line_3_key = f'{address_key_prefix}addr_line_3'
        addr_line_2 = address_data_dict[addr_line_2_key]
        addr_line_3 = address_data_dict[addr_line_3_key]
        addr_line_2 = addr_line_2 if addr_line_2 else ''
        addr_line_2 = addr_line_2.strip()
        addr_line_3 = addr_line_3 if addr_line_3 else ''
        result = f'{addr_line_2} {addr_line_3}'
    elif address_format_type == AddressFormatType.ADVANCED:
        route_service_type_key = f'{address_key_prefix}route_service_type'
        lock_box_no_key = f'{address_key_prefix}lock_box_no'
        route_service_no_key = f'{address_key_prefix}route_service_no'
        installation_type_key = f'{address_key_prefix}installation_type'
        installation_name_key = f'{address_key_prefix}installation_name'
        street_additional_elements = [address_data_dict[route_service_type_key],
                                   address_data_dict[lock_box_no_key],
                                   address_data_dict[route_service_no_key],
                                   address_data_dict[installation_type_key],
                                   address_data_dict[installation_name_key]]
        for element in street_additional_elements:
            if element:
                result += f' {element}'

    result = result.strip()
    return result


def get_street_address(address_format_type: str, address_data_dict: dict, address_key_prefix: str):
    result = ''

    if address_format_type == AddressFormatType.FOREIGN:
        addr_line_1_key = f'{address_key_prefix}addr_line_1'
        result = address_data_dict[addr_line_1_key]
    elif address_format_type in (AddressFormatType.BASIC, AddressFormatType.ADVANCED):
        unit_type_key = f'{address_key_prefix}unit_type'
        unit_no_key = f'{address_key_prefix}unit_no'
        civic_no_key = f'{address_key_prefix}civic_no'
        civic_no_suffix_key = f'{address_key_prefix}civic_no_suffix'
        street_name_key = f'{address_key_prefix}street_name'
        street_type_key = f'{address_key_prefix}street_type'
        street_direction_key = f'{address_key_prefix}street_direction'
        street_address_elements = [address_data_dict[unit_type_key],
                                   address_data_dict[unit_no_key],
                                   address_data_dict[civic_no_key],
                                   address_data_dict[civic_no_suffix_key],
                                   address_data_dict[street_name_key],
                                   address_data_dict[street_type_key],
                                   address_data_dict[street_direction_key]]
        for element in street_address_elements:
            if element:
                result += f' {element}'

    result = result.strip()
    return result


def get_party_role_type(corp_type_cd: str, role_type: str):
    if role_type == 'INC':
        return 'Incorporator'
    elif role_type == 'DIR':
        return 'Director'
    else:
        return None


def get_party_type(filing_party_data: dict):
    if (corp_party_business_name := filing_party_data['cp_business_name']) \
            and corp_party_business_name.strip():
        return 'organization'

    return 'person'


def get_is_paper_only(filing_data: dict):
    if (ods_type_cd := filing_data['f_ods_type']) and \
            ods_type_cd == 'P':
        return True

    return False


def get_effective_date(filing_data: dict):
    return filing_data['f_effective_dts_pacific']


def get_effective_date_str(filing_data: dict):
    return filing_data['f_effective_dt_str']


def get_event_info_to_retrieve(unprocessed_firm_dict: dict):
    event_ids = unprocessed_firm_dict.get('event_ids')
    event_file_types = unprocessed_firm_dict.get('event_file_types')
    event_file_types = event_file_types.split(',')
    last_event_id = unprocessed_firm_dict.get('last_event_id')
    last_processed_event_id = unprocessed_firm_dict.get('last_processed_event_id')

    if not last_processed_event_id or pd.isna(last_processed_event_id):
        return event_ids, event_file_types

    if last_processed_event_id != last_event_id:
        next_event_index = event_ids.index(last_processed_event_id)
        events_ids_to_retrieve = event_ids[next_event_index:]
        event_file_types_to_retrieve = event_file_types[next_event_index:]
        return events_ids_to_retrieve, event_file_types_to_retrieve

    # shouldn't get here
    return [], []


def get_processed_event_ids(unprocessed_firm_dict: dict):
    event_ids = unprocessed_firm_dict.get('event_ids')
    last_event_id = unprocessed_firm_dict.get('last_event_id')
    last_processed_event_id = unprocessed_firm_dict.get('last_processed_event_id')

    if not last_processed_event_id or pd.isna(last_processed_event_id):
        return []

    if last_processed_event_id != last_event_id:
        last_processed_event_id_index = event_ids.index(last_processed_event_id) + 1
        processed_events_ids = event_ids[:last_processed_event_id_index]
        return processed_events_ids

    # shouldn't get here
    return []


def get_previous_event_ids(event_ids: list, current_event_id: int):
    index = event_ids.index(current_event_id)
    previous_event_ids = event_ids[:index]
    return previous_event_ids


def is_in_lear(processed_events_ids: list, event_id: int):
    if event_id in processed_events_ids:
        return True
    return False


def get_is_frozen(filing_data: dict):
    if (corp_frozen_type_cd := filing_data.get('c_corp_frozen_type_cd', '')) and corp_frozen_type_cd == 'C':
        return True
    return False


def get_office_type(office_type_cd: str):
    if office_type_cd == 'RG':
        return 'registeredOffice'
    elif office_type_cd == 'RC':
        return 'recordsOffice'
    else:
        return None


def get_alias_type(corp_name_typ_cd: dict):
    if corp_name_typ_cd in ('CO', 'NB'):
        return None
    if corp_name_typ_cd == 'TR':
        return 'TRANSLATION'

    return corp_name_typ_cd
