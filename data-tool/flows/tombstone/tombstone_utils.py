import copy
import json
from datetime import datetime, timezone

import pandas as pd
import pytz
from sqlalchemy import Connection, text
from tombstone.tombstone_base_data import (ALIAS, FILING, FILING_JSON, OFFICE,
                                           PARTY, PARTY_ROLE, RESOLUTION,
                                           SHARE_CLASSES, USER)
from tombstone.tombstone_mappings import (EVENT_FILING_LEAR_TARGET_MAPPING,
                                          LEAR_FILING_BUSINESS_UPDATE_MAPPING,
                                          LEAR_STATE_FILINGS)

unsupported_event_file_types = set()


def format_business_data(data: dict) -> dict:
    business_data = data['businesses'][0]
    # Note: only ACT or HIS
    state = business_data['state']
    business_data['state'] = 'ACTIVE' if state == 'ACT' else 'HISTORICAL'

    if not (last_ar_date := business_data['last_ar_date']):
        last_ar_date = business_data['founding_date']
    
    last_ar_year = int(last_ar_date.split('-')[0])

    formatted_business = {
        **business_data,
        'last_ar_date': last_ar_date,
        'last_ar_year': last_ar_year,
        'fiscal_year_end_date': business_data['founding_date'],
        'last_ledger_timestamp': business_data['founding_date'],
        'last_modified': datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    }

    return formatted_business


def format_address_data(address_data: dict, prefix: str) -> dict:
    # Note: all corps have a format type of null or FOR
    address_type = 'mailing' if prefix == 'ma_' else 'delivery'
    
    street = address_data[f'{prefix}addr_line_1']
    street_additional_elements = []
    if (line_2 := address_data[f'{prefix}addr_line_2']) and (line_2 := line_2.strip()):
        street_additional_elements.append(line_2)
    if (line_3 := address_data[f'{prefix}addr_line_3']) and (line_3 := line_3.strip()):
        street_additional_elements.append(line_3)
    street_additional = ' '.join(street_additional_elements)

    if not (delivery_instructions := address_data[f'{prefix}delivery_instructions']) \
        or not (delivery_instructions := delivery_instructions.strip()):
        delivery_instructions = ''

    formatted_address = {
        'address_type': address_type,
        'street': street,
        'street_additional': street_additional,
        'city': address_data[f'{prefix}city'],
        'region': address_data[f'{prefix}province'],
        'country': address_data[f'{prefix}country_typ_cd'],
        'postal_code': address_data[f'{prefix}postal_cd'],
        'delivery_instructions': delivery_instructions
    }
    return formatted_address


def format_offices_data(data: dict) -> list[dict]:
    offices_data = data['offices']
    formatted_offices = []

    for x in offices_data:
        # Note: only process RC and RG now (done in SQL)
        # TODO: support other office types
        office = copy.deepcopy(OFFICE)
        office['offices']['office_type'] = 'recordsOffice' if x['o_office_typ_cd'] == 'RC' else 'registeredOffice'

        mailing_address = format_address_data(x, 'ma_')
        delivery_address = format_address_data(x, 'da_')

        office['addresses'].append(mailing_address)
        office['addresses'].append(delivery_address)

        formatted_offices.append(office)
    
    return formatted_offices


def format_parties_data(data: dict) -> list[dict]:
    parties_data = data['parties']

    if not parties_data:
        return []

    formatted_parties = []

    df = pd.DataFrame(parties_data)
    grouped_parties = df.groupby('cp_full_name')
    for _, group in grouped_parties:
        party = copy.deepcopy(PARTY)
        party_info = group.iloc[0].to_dict()
        party['parties']['first_name'] = party_info['cp_first_name']
        party['parties']['middle_initial'] = party_info['cp_middle_name']
        party['parties']['last_name'] = party_info['cp_last_name']
        party['parties']['party_type'] = 'person'

        # Note: can be index 0
        if (ma_index := group['cp_mailing_addr_id'].first_valid_index()) is not None:
            mailing_addr_data = group.loc[ma_index].to_dict()
        else:
            mailing_addr_data = None
        
        if (da_index := group['cp_delivery_addr_id'].first_valid_index()) is not None:
            delivery_addr_data = group.loc[da_index].to_dict()
        else:
            delivery_addr_data = None

        if mailing_addr_data:
            mailing_address = format_address_data(mailing_addr_data, 'ma_')
            party['addresses'].append(mailing_address)
        if delivery_addr_data:
            delivery_address = format_address_data(delivery_addr_data, 'da_')
            party['addresses'].append(delivery_address)

        formatted_party_roles = party['party_roles']
        for _, r in group.iterrows():
            if (role_code := r['cp_party_typ_cd']) not in ['INC', 'DIR']:
                continue
            role = 'incorporator' if role_code == 'INC' else 'director'
            party_role = copy.deepcopy(PARTY_ROLE)
            party_role['role'] = role
            party_role['appointment_date'] = r['cp_appointment_dt_str']
            party_role['cessation_date'] = r['cp_cessation_dt_str']
            formatted_party_roles.append(party_role)
        
        formatted_parties.append(party)
    
    return formatted_parties


def format_share_series_data(share_series_data: dict) -> dict:
    formatted_series = {
        'name': share_series_data['srs_series_nme'],
        'priority': int(share_series_data['srs_series_id']) if share_series_data['srs_series_id'] else None,
        'max_share_flag': share_series_data['srs_max_share_ind'],
        'max_shares': int(share_series_data['srs_share_quantity']) if share_series_data['srs_share_quantity'] else None,
        'special_rights_flag': share_series_data['srs_spec_right_ind']
    }

    return formatted_series


def format_share_classes_data(data: dict) -> list[dict]:
    share_classes_data = data['share_classes']

    if not share_classes_data:
        return []

    formatted_share_classes = []

    df = pd.DataFrame(share_classes_data)
    grouped_share_classes = df.groupby('ssc_share_class_id')

    for share_class_id, group in grouped_share_classes:
        share_class = copy.deepcopy(SHARE_CLASSES)
        share_class_info = group.iloc[0].to_dict()

        priority = int(share_class_info['ssc_share_class_id']) if share_class_info['ssc_share_class_id'] else None
        max_shares = int(share_class_info['ssc_share_quantity']) if share_class_info['ssc_share_quantity'] else None
        par_value = float(share_class_info['ssc_par_value_amt']) if share_class_info['ssc_par_value_amt'] else None
        
        # TODO: map NULL or custom input value of ssc_other_currency
        if (currency := share_class_info['ssc_currency_typ_cd']) == 'OTH':
            currency = share_class_info['ssc_other_currency']

        share_class['share_classes']['name'] = share_class_info['ssc_class_nme']
        share_class['share_classes']['priority'] = priority
        share_class['share_classes']['max_share_flag'] = share_class_info['ssc_max_share_ind']
        share_class['share_classes']['max_shares'] = max_shares
        share_class['share_classes']['par_value_flag'] = share_class_info['ssc_par_value_ind']
        share_class['share_classes']['par_value'] = par_value
        share_class['share_classes']['currency'] = currency
        share_class['share_classes']['special_rights_flag'] = share_class_info['ssc_spec_rights_ind']

        # Note: srs_share_class_id should be either None or equal to share_class_id
        matching_series = group[group['srs_share_class_id']==share_class_id]
        formatted_series = share_class['share_series']
        for _, r in matching_series.iterrows():
            formatted_series.append(format_share_series_data(r.to_dict()))

        formatted_share_classes.append(share_class)

    return formatted_share_classes


def format_aliases_data(data: dict) -> list[dict]:
    aliases_data = data['aliases']
    formatted_aliases = []

    for x in aliases_data:
        if x['cn_corp_name_typ_cd'] != 'TR':
            continue
        alias = copy.deepcopy(ALIAS)
        alias['alias'] = x['cn_corp_name']
        alias['type'] = 'TRANSLATION'
        formatted_aliases.append(alias)

    return formatted_aliases


def format_resolutions_data(data: dict) -> list[dict]:
    resolutions_data = data['resolutions']
    formatted_resolutions = []

    for x in resolutions_data:
        resolution = copy.deepcopy(RESOLUTION)
        resolution['resolution_date'] = x['r_resolution_dt_str']
        resolution['type'] = 'SPECIAL'
        formatted_resolutions.append(resolution)

    return formatted_resolutions


def format_filings_data(data: dict) -> list[dict]:
    # filing info in business
    business_update_dict = {}

    filings_data = data['filings']
    formatted_filings = []
    last_state_filing_idx = -1
    idx = 0
    for x in filings_data:
        event_file_type = x['event_file_type']
        # TODO: build a new complete filing event mapper (WIP)
        filing_type, filing_subtype = get_target_filing_type(event_file_type)
        # skip the unsupported ones
        if not filing_type:
            print(f'❗ Skip event filing type: {event_file_type}')
            unsupported_event_file_types.add(event_file_type)
            continue

        effective_date = x['f_effective_dt_str']
        if not effective_date:
            effective_date = x['e_event_dt_str']

        filing_json, meta_data = build_filing_json_meta_data(filing_type, filing_subtype,
                                                             effective_date, x)

        filing = copy.deepcopy(FILING)

        # make it None if no valid value
        if not (user_id := x['u_user_id']):
            user_id = x['u_full_name'] if x['u_full_name'] else None

        filing = {
            **filing,
            'filing_date': effective_date,
            'filing_type': filing_type,
            'filing_sub_type': filing_subtype,
            'completion_date': effective_date,
            'effective_date': effective_date,
            'filing_json': filing_json,
            'meta_data': meta_data,
            'submitter_id': user_id  # will be updated to real user_id when loading data into db
        }

        formatted_filings.append(filing)

        # update business info based on filing
        if keys := LEAR_FILING_BUSINESS_UPDATE_MAPPING.get(filing_type):
            if filing_type in ['putBackOn', 'restoration']:
                value = None
            else:
                value = effective_date
            business_update_dict.update({k: value for k in keys})
        # save state filing index
        if filing_type in LEAR_STATE_FILINGS:
            last_state_filing_idx = idx
        
        idx += 1

    return {
        'filings': formatted_filings,
        'update_business_info': business_update_dict,
        'state_filing_index': last_state_filing_idx
    }


def format_users_data(users_data: list) -> list:
    formatted_users = []

    for x in users_data:
        user = copy.deepcopy(USER)
        event_file_types = x['event_file_types'].split(',')
        # skip users if all event_file_type is unsupported
        if not any(get_target_filing_type(ef)[0] for ef in event_file_types):
            continue
        
        if not (username := x['u_user_id']):
            username = x['u_full_name']

        # skip if both u_user_id and u_full_name is empty
        if not username:
            continue

        user = {
            **user,
            'username': username,
            'firstname': x['u_first_name'],
            'middlename': x['u_middle_name'],
            'lastname': x['u_last_name'],
            'email': x['u_email_addr'],
            'creation_date': x['earliest_event_dt_str']
        }

        formatted_users.append(user)

    return formatted_users


def formatted_data_cleanup(data: dict) -> dict:
    filings_business = data['filings']
    data['updates'] = {
        'businesses': filings_business['update_business_info'],
        'state_filing_index': filings_business['state_filing_index']
    }
    data['filings'] = filings_business['filings']

    return data



def get_data_formatters() -> dict:
    ret = {
        'businesses': format_business_data,
        'offices': format_offices_data,
        'parties': format_parties_data,
        'share_classes': format_share_classes_data,
        'aliases': format_aliases_data,
        'resolutions': format_resolutions_data,
        'filings': format_filings_data
    }
    return ret


def get_target_filing_type(event_file_type: str) -> tuple[str, str]:
    filing_type, filing_subtype = None, None
    if value := EVENT_FILING_LEAR_TARGET_MAPPING.get(event_file_type):
        if isinstance(value, list):
            filing_type, filing_subtype = value[0], value[1]
        else:
            filing_type = value

    return filing_type, filing_subtype


def build_filing_json_meta_data(filing_type: str, filing_subtype: str, effective_date: str, data: dict) -> tuple[dict, dict]:
    filing_json = copy.deepcopy(FILING_JSON)
    filing_json['filing'][filing_type] = {}

    meta_data = {
        'colinFilingInfo': {
            'eventType': data['e_event_type_cd'],
            'filingType': data['f_filing_type_cd']
        },
        'isLedgerPlaceholder': True,
    }

    if filing_type == 'annualReport':
        meta_data['annualReport'] = {
            'annualReportFilingYear': int(effective_date[:4]),
        }
    elif filing_type == 'dissolution':
        meta_data['dissolution'] = {
            'dissolutionType': filing_subtype,
        }
        filing_json['filing']['dissolution'] = {
            'dissolutionType': filing_subtype,
            'dissolutionDate': effective_date[:10],
        }
    # TODO: populate meta_data for correction to display correct filing name

    return filing_json, meta_data


def build_epoch_filing(business_id: int) -> dict:
    now = datetime.utcnow().replace(tzinfo=pytz.UTC)
    filing = copy.deepcopy(FILING)
    filing = {
        **filing,
        'filing_type': 'lear_tombstone',
        'business_id': business_id,
        'filing_date': now.isoformat(),
        'completion_date': now.isoformat(),
        'effective_date': now.isoformat(),
        'status': 'TOMBSTONE'
    }
    return filing


def load_data(conn: Connection, table_name: str, data: dict, conflict_column: str=None) -> int:
    columns = ', '.join(data.keys())
    values = ', '.join([format_value(v) for v in data.values()])

    if conflict_column:
        conflict_value = format_value(data[conflict_column])
        check_query = f"select id from {table_name} where {conflict_column} = {conflict_value}"
        check_result = conn.execute(text(check_query)).scalar()
        if check_result:
            return check_result

    query = f"""insert into {table_name} ({columns}) values ({values}) returning id"""

    result = conn.execute(text(query))
    id = result.scalar()

    return id


def update_data(conn: Connection, table_name: str, data: dict, id: int) -> bool:
    update_pairs = [f'{k} = {format_value(v)}' for k, v in data.items()]
    update_pairs_str = ', '.join(update_pairs)
    query = f"""update {table_name} set {update_pairs_str} where id={id}"""

    result = conn.execute(text(query))

    return result.rowcount > 0


def format_value(value) -> str:
    if value is None:
        return 'NULL'
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, dict):
        return f"'{json.dumps(value)}'"
    else:
        # Note: handle single quote issue
        value = str(value).replace("'", "''")
        return f"'{value}'"
