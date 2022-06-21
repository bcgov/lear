import pandas as pd

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


def get_street_additional(addr_line_2: str, addr_line_3: str):
    addr_line_2 = addr_line_2 if addr_line_2 else ''
    addr_line_2 = addr_line_2.strip()
    addr_line_3 = addr_line_3 if addr_line_3 else ''
    result = f'{addr_line_2} {addr_line_3}'
    result = result.strip()
    return result


def get_party_role_type(corp_type_cd: str, role_type: str):
    if role_type == 'FCP':
        return 'Completing Party'
    elif role_type == 'FIO' or role_type == 'FBO':
        if corp_type_cd == 'SP':
            return 'Proprietor'
        elif corp_type_cd == 'GP':
            return 'Partner'
        else:
            return None
    else:
        return None


def get_party_type(filing_party_data: dict):
    corp_party_business_name = filing_party_data['cp_business_name']
    if corp_party_business_name:
        return 'organization'

    return 'person'


def get_is_paper_only(filing_data: dict):
    if (ods_type_cd := filing_data['f_ods_type']) and \
            ods_type_cd == 'P':
        return True

    return False


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
