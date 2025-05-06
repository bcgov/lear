import copy
import datedelta
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Final, Optional

import pandas as pd
import pytz
from sqlalchemy import Connection, bindparam, text
from tombstone.tombstone_base_data import (ALIAS, AMALGAMATION, FILING,
                                           FILING_JSON, IN_DISSOLUTION,
                                           JURISDICTION, OFFICE, OFFICES_HELD,
                                           PARTY, PARTY_ROLE, RESOLUTION,
                                           SHARE_CLASSES, USER)
from tombstone.tombstone_mappings import (EVENT_FILING_DISPLAY_NAME_MAPPING,
                                          EVENT_FILING_LEAR_TARGET_MAPPING,
                                          LEAR_FILING_BUSINESS_UPDATE_MAPPING,
                                          LEAR_STATE_FILINGS,
                                          LEGAL_TYPE_CHANGE_FILINGS,
                                          NO_FILING_EVENT_FILE_TYPES,
                                          SKIPPED_EVENT_FILE_TYPES,
                                          EventFilings)

all_unsupported_types = set()
date_format_with_tz: Final = '%Y-%m-%d %H:%M:%S%z'


def format_business_data(data: dict) -> dict:
    business_data = data['businesses'][0]
    # Note: only ACT or HIS
    state = business_data['state']
    business_data['state'] = 'ACTIVE' if state == 'ACT' else 'HISTORICAL'

    if last_ar_date := business_data['last_ar_date']:
        last_ar_year = int(last_ar_date.split('-')[0])
        last_ar_date = last_ar_date + ' 00:00:00+00:00'
    else:
        last_ar_date = None
        last_ar_year = None

    last_ar_reminder_year = business_data['last_ar_reminder_year']

    # last_ar_reminder_year can be None if send_ar_ind is false or the business is in the 1st financial year
    if business_data['send_ar_ind'] and last_ar_reminder_year is None:
        last_ar_reminder_year = last_ar_year

    formatted_business = {
        **business_data,
        'last_ar_date': last_ar_date,
        'last_ar_year': last_ar_year,
        'last_ar_reminder_year': last_ar_reminder_year,
        'fiscal_year_end_date': business_data['founding_date'],
        'last_ledger_timestamp': business_data['founding_date'],
        'last_modified': datetime.now(tz=timezone.utc).isoformat()
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
        'street': street or '',
        'street_additional': street_additional or '',
        'city': address_data[f'{prefix}city'] or '',
        'region': address_data[f'{prefix}province'] or '',
        'country': address_data[f'{prefix}country_typ_cd'],
        'postal_code': address_data[f'{prefix}postal_cd'] or '',
        'delivery_instructions': delivery_instructions or ''
    }
    return formatted_address


def format_offices_data(data: dict) -> list[dict]:
    offices_data = data['offices']
    formatted_offices = []
    # TODO: support other office types
    office_mapping = {
        'RC': 'recordsOffice',
        'RG': 'registeredOffice',
        'LQ': 'liquidationRecordsOffice',
        'DS': 'custodialOffice'
        # Additional office type codes can be added here in the future
    }

    for x in offices_data:
        # Note: only process RC, RG, LQ now (done in SQL)
        if (office_type := x['o_office_typ_cd']) not in office_mapping.keys():
            continue
        # Skip ceased DS (it's only used for ceased custodian)
        if office_type == 'DS' and x['o_end_event_id'] is not None:
            continue

        office = copy.deepcopy(OFFICE)
        office['offices']['office_type'] = office_mapping[office_type]

        mailing_address = format_address_data(x, 'ma_')
        delivery_address = format_address_data(x, 'da_')

        office['addresses'].append(mailing_address)
        office['addresses'].append(delivery_address)

        formatted_offices.append(office)

    return formatted_offices


def format_parties_data(data: dict) -> list[dict]:
    parties_data = data['parties']
    offices_data = data['offices']

    if not parties_data:
        return []

    formatted_parties = []

    # Map role codes to role names
    role_mapping = {
        'DIR': 'director',
        'OFF': 'officer',
        'RCC': 'custodian',
        'RCM': 'receiver',
        'LIQ': 'liquidator',
        # Additional roles can be added here in the future
    }

    # Only officers use prev_party_id = 0, exclude them in prev_party_ids set
    prev_party_ids = {x['cp_prev_party_id'] for x in parties_data \
                      if x['cp_prev_party_id'] not in (None, Decimal('0'))}

    # Format party
    for party_info in parties_data:
        # Skip if it's not the latest party
        if party_info['cp_corp_party_id'] in prev_party_ids:
            continue
        party = copy.deepcopy(PARTY)
        party['parties']['cp_full_name'] = party_info['cp_full_name']
        party['parties']['first_name'] = (party_info['cp_first_name'] or '').upper()
        party['parties']['middle_initial'] = (party_info['cp_middle_name'] or '').upper()
        party['parties']['last_name'] = (party_info['cp_last_name'] or '').upper()
        party['parties']['party_type'] = 'person' if party_info['cp_full_name'] else 'organization'
        party['parties']['title'] = ''
        party['parties']['organization_name'] = (party_info['cp_business_name'] or '').upper()
        party['parties']['email'] = ''
        party['parties']['identifier'] = ''

        # Format party role
        formatted_party_roles = party['party_roles']

        if (role_code := party_info['cp_party_typ_cd']) not in role_mapping.keys():
            continue

        role = role_mapping[role_code]  # Will raise KeyError if role_code not in mapping

        party_role = copy.deepcopy(PARTY_ROLE)
        party_role['role'] = role

        appointment_date = None
        earliest_party_info = find_earliest_party(party_info, parties_data)
        if appointment_date := earliest_party_info['cp_appointment_dt_str']:
            appointment_date = appointment_date + ' 00:00:00+00:00'
        party_role['appointment_date'] = appointment_date

        cessation_date = None
        if role_code in ('LIQ', 'RCM', 'RCC'):
            if end_event_date := party_info['cp_end_event_dt_str']:
                cessation_date = end_event_date + ' 00:00:00+00:00'
        elif cessation_date := party_info['cp_cessation_dt_str']:
            cessation_date = cessation_date + ' 00:00:00+00:00'
        party_role['cessation_date'] = cessation_date

        formatted_party_roles.append(party_role)

        # Prepare to format party addresses 
        # Note: can be index 0
        if party_info['cp_mailing_addr_id'] is not None:
            mailing_addr_data = party_info
        else:
            mailing_addr_data = None

        if party_info['cp_delivery_addr_id'] is not None:
            delivery_addr_data = party_info
        else:
            delivery_addr_data = None

        # Special case for custodian address
        custodian_office = next((
            office for office in offices_data if (
                office['o_office_typ_cd'] == 'DS' and
                office['o_start_event_id'] == party_info['cp_start_event_id']
            )
        ), None)
        if (
            any(party_role['role'] == 'custodian' for party_role in formatted_party_roles) and 
            not mailing_addr_data and
            not delivery_addr_data and
            custodian_office
        ):
            mailing_addr_data = custodian_office
            delivery_addr_data = custodian_office

        # Format party addresses
        if mailing_addr_data:
            mailing_address = format_address_data(mailing_addr_data, 'ma_')
            party['addresses'].append(mailing_address)
        if delivery_addr_data:
            delivery_address = format_address_data(delivery_addr_data, 'da_')
            party['addresses'].append(delivery_address)

        formatted_parties.append(party)

    return formatted_parties


def find_earliest_party(curr_party: dict, parties_data: list[dict]) -> dict:
    prev_party = next(
        (x for x in parties_data if x['cp_corp_party_id'] == curr_party['cp_prev_party_id']),
        None
    )
    if not prev_party:
        return curr_party
    return find_earliest_party(prev_party, parties_data)


def format_offices_held_data(data: dict) -> list[dict]:
    offices_held_data = data['offices_held']

    if not offices_held_data:
        return []

    formatted_offices_held = []

    title_mapping = {
        'ASC': 'ASSISTANT_SECRETARY',
        'CEO': 'CEO',
        'CFO': 'CFO',
        'CHR': 'CHAIR',
        'OTH': 'OTHER_OFFICES',
        'PRE': 'PRESIDENT',
        'SEC': 'SECRETARY',
        'TRE': 'TREASURER',
        'VIP': 'VICE_PRESIDENT'
    }

    for x in offices_held_data:
        office_held = copy.deepcopy(OFFICES_HELD)
        office_held['cp_full_name'] = x['cp_full_name']
        office_held['title'] = title_mapping[x['oh_officer_typ_cd']] # map to enum val
        formatted_offices_held.append(office_held)

    return formatted_offices_held


def format_share_series_data(share_series_data: dict) -> dict:
    max_shares = int(share_series_data['srs_share_quantity']) if share_series_data['srs_share_quantity'] else None
    formatted_series = {
        'name': format_share_name(share_series_data['srs_series_nme']),
        'priority': int(share_series_data['srs_series_id']) if share_series_data['srs_series_id'] else None,
        'max_share_flag': (max_shares > 0 if max_shares else False),
        'max_shares': max_shares if (max_shares and max_shares > 0) else None,
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

        currency_additioanl = None
        if (currency := share_class_info['ssc_currency_typ_cd']) == 'OTH':
            if (other_currency := share_class_info['ssc_other_currency']) and other_currency.strip() == 'CAD':
                currency = 'CAD'
            else:
                currency = 'OTHER'  # TODO: to confirm the code used in LEAR in the end
                currency_additioanl = other_currency

        share_class['share_classes']['name'] = format_share_name(share_class_info['ssc_class_nme'])
        share_class['share_classes']['priority'] = priority
        share_class['share_classes']['max_share_flag'] = (max_shares > 0 if max_shares else False)
        share_class['share_classes']['max_shares'] = max_shares if (max_shares and max_shares > 0) else None
        share_class['share_classes']['par_value_flag'] = (par_value > 0 if par_value else False)
        share_class['share_classes']['par_value'] = par_value if (par_value and par_value > 0) else None
        share_class['share_classes']['currency'] = currency
        share_class['share_classes']['currency_additional'] = currency_additioanl
        share_class['share_classes']['special_rights_flag'] = share_class_info['ssc_spec_rights_ind']

        # Note: srs_share_class_id should be either None or equal to share_class_id
        matching_series = group[group['srs_share_class_id'] == share_class_id]
        formatted_series = share_class['share_series']
        for _, r in matching_series.iterrows():
            formatted_series.append(format_share_series_data(r.to_dict()))

        formatted_share_classes.append(share_class)

    return formatted_share_classes


def format_share_name(name: str):
    expected_suffix = ' Shares'
    if not name or name.endswith(expected_suffix):
        return name

    if name.endswith(' shares'):
        name = name.removesuffix(' shares')

    return f'{name}{expected_suffix}'


def format_aliases_data(data: dict) -> list[dict]:
    aliases_data = data['aliases']
    formatted_aliases = []

    for x in aliases_data:
        if x['cn_corp_name_typ_cd'] != 'TR':
            continue
        alias = copy.deepcopy(ALIAS)
        alias['alias'] = (x['cn_corp_name'] or '').upper()
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


def format_jurisdictions_data(data: dict, event_id: Decimal) -> dict:
    jurisdictions_data = data['jurisdictions']

    matched_jurisdictions = [
        item for item in jurisdictions_data if item.get('j_start_event_id') == event_id
    ]

    if not matched_jurisdictions:
        return None

    formatted_jurisdiction = copy.deepcopy(JURISDICTION)
    jurisdiction_info = matched_jurisdictions[0]

    formatted_jurisdiction['legal_name'] = jurisdiction_info['j_home_company_nme']
    formatted_jurisdiction['identifier'] = jurisdiction_info['j_home_juris_num']
    formatted_jurisdiction['incorporation_date'] = jurisdiction_info['j_home_recogn_dt']
    formatted_jurisdiction['expro_identifier'] = jurisdiction_info['j_bc_xpro_num']
    formatted_jurisdiction['country'] = None
    formatted_jurisdiction['region'] = None

    can_jurisdiction_code = jurisdiction_info['j_can_jur_typ_cd'] or ''
    other_jurisdiction_desc = jurisdiction_info['j_othr_juris_desc'] or ''

    # when canadian jurisdiction, ignore othr_juris_desc
    if can_jurisdiction_code != 'OT':
        formatted_jurisdiction['country'] = 'CA'
        formatted_jurisdiction['region'] = 'FEDERAL' if can_jurisdiction_code == 'FD' else can_jurisdiction_code
    # when other jurisdiction and len(othr_juris_desc) = 2, then othr_juris_desc is country code
    elif can_jurisdiction_code == 'OT' and len(other_jurisdiction_desc) == 2:
        formatted_jurisdiction['country'] = other_jurisdiction_desc
    # when other jurisdiction and len(othr_juris_desc) = 6, then othr_juris_desc contains both
    # region code and country code (like "US, SS"). Ignore any other cases.
    elif can_jurisdiction_code == 'OT' and len(other_jurisdiction_desc) == 6:
        formatted_jurisdiction['country'] = other_jurisdiction_desc[:2]
        formatted_jurisdiction['region'] = other_jurisdiction_desc[4:]
    else:
        # add placeholder for unavailable information
        formatted_jurisdiction['country'] = 'UNKNOWN'

    return formatted_jurisdiction


def format_filings_data(data: dict) -> dict:
    # filing info in business
    business_update_dict = {}
    current_unsupported_types = set()

    filings_data = data['filings']
    formatted_filings = []
    state_filing_idx = -1
    idx = 0
    withdrawn_filing_idx = -1
    for x in filings_data:
        event_file_type = x['event_file_type']
        # skip event_file_type that we don't need to support
        if event_file_type in SKIPPED_EVENT_FILE_TYPES or event_file_type in NO_FILING_EVENT_FILE_TYPES:
            print(f'💡 Skip event filing type: {event_file_type}')
            continue
        # TODO: build a new complete filing event mapper (WIP)
        raw_filing_type, raw_filing_subtype = get_target_filing_type(event_file_type)
        # skip the unsupported ones (need to support in the future)
        if not raw_filing_type and event_file_type not in NO_FILING_EVENT_FILE_TYPES:
            print(f'❗ Unsupported event filing type: {event_file_type}')
            current_unsupported_types.add(event_file_type)
            all_unsupported_types.add(event_file_type)
            continue

        # get converted filing_type and filing_subtype
        if raw_filing_type == 'conversion':
            if isinstance(raw_filing_subtype, tuple):
                filing_type, filing_subtype = raw_filing_subtype
            else:
                filing_type = raw_filing_subtype
                filing_subtype = None
            raw_filing_subtype = None
        else:
            filing_type = raw_filing_type
            filing_subtype = raw_filing_subtype

        effective_date = x['ce_effective_dt_str'] or x['f_effective_dt_str'] or x['e_event_dt_str']
        if filing_type == 'annualReport':
            effective_date = x['f_period_end_dt_str']

        filing_date = x['ce_effective_dt_str'] or x['e_event_dt_str']
        trigger_date = x['e_trigger_dt_str']

        filing_json, meta_data = build_filing_json_meta_data(raw_filing_type, filing_type, filing_subtype,
                                                             effective_date, x)

        filing_body = copy.deepcopy(FILING['filings'])
        jurisdiction = None
        amalgamation = None
        consent_continuation_out = None

        user_id = get_username(x)

        if (
            raw_filing_type == 'conversion'
            or raw_filing_subtype == 'involuntary'
            or event_file_type in ['SYSDL_NULL', 'ADCORP_NULL', 'ADFIRM_NULL', 'ADMIN_NULL']
        ):
            hide_in_ledger = True
        else:
            hide_in_ledger = False

        if x['f_withdrawn_event_id']:
            if filing_type in [
                'amalgamationApplication',
                'incorporationApplication',
                'continuationIn'
            ]:
                raise Exception('Stop migrating withdrawn corp')
            status = 'WITHDRAWN'
            completion_date = None
            withdrawn_filing_idx = idx
        else:
            status = 'COMPLETED'
            completion_date = effective_date

        filing_body = {
            **filing_body,
            'filing_date': filing_date,
            'filing_type': raw_filing_type,
            'filing_sub_type': raw_filing_subtype,
            'completion_date': completion_date,
            'effective_date': effective_date,
            'filing_json': filing_json,
            'meta_data': meta_data,
            'hide_in_ledger': hide_in_ledger,
            'status': status,
            'submitter_id': user_id,  # will be updated to real user_id when loading data into db
        }

        # conversion still need to populate create-new-business info
        # based on converted filing type
        if filing_type == 'continuationIn':
            jurisdiction = format_jurisdictions_data(data, x['e_event_id'])
        elif filing_type == 'amalgamationApplication':
            amalgamation = format_amalgamations_data(data, x['e_event_id'], effective_date, filing_subtype)
        elif filing_type == 'noticeOfWithdrawal':
            filing_body['withdrawn_filing_id'] = withdrawn_filing_idx  # will be updated to real filing_id when loading data
            withdrawn_filing_idx = -1
        elif filing_type in ('consentContinuationOut', 'consentAmalgamationOut'):
            consent_continuation_out = format_consent_continuation_out(filing_type, effective_date)

        comments = format_filing_comments_data(data, x['e_event_id'])

        colin_event_ids = {'colin_event_id': x['e_event_id']}
        filing = {
            'filings': filing_body,
            'jurisdiction': jurisdiction,
            'amalgamations': amalgamation,
            'comments': comments,
            'colin_event_ids': colin_event_ids,
            'consent_continuation_out': consent_continuation_out
        }

        formatted_filings.append(filing)

        # update business info based on filing
        keys = LEAR_FILING_BUSINESS_UPDATE_MAPPING.get(filing_type, [])
        for k in keys:
            business_update_dict[k] = get_business_update_value(k, effective_date, trigger_date,
                                                                filing_type, filing_subtype)
        # save state filing index
        if filing_type in LEAR_STATE_FILINGS and x['e_event_id'] == x['cs_state_event_id']:
            state_filing_idx = idx

        idx += 1

    return {
        'filings': formatted_filings,
        'update_business_info': business_update_dict,
        'state_filing_index': state_filing_idx,
        'unsupported_types': current_unsupported_types,
    }

def format_consent_continuation_out(filing_type: str, effective_date_str: str):
    expiry_date = get_expiry_date(effective_date_str)
    consent_continuation_out = {
        'consent_type': 'continuation_out' if filing_type == 'consentContinuationOut' else 'amalgamation_out',
        'expiry_date': expiry_date.isoformat(),
        'foreign_jurisdiction': '',
        'foreign_jurisdiction_region': '',
    }

    return consent_continuation_out


def get_expiry_date(effective_date_str: str) -> datetime:
    pst = pytz.timezone('America/Vancouver')
    effective_date = datetime.strptime(effective_date_str, date_format_with_tz)
    effective_date = effective_date.astimezone(pst)
    _date = effective_date.replace(hour=23, minute=59, second=0, microsecond=0)
    _date += datedelta.datedelta(months=6)

    # Setting legislation timezone again after adding 6 months to recalculate the UTC offset and DST info
    _date = _date.astimezone(pst)

    # Adjust day light savings. Handle DST +-1 hour changes
    dst_offset_diff = effective_date.dst() - _date.dst()
    _date += dst_offset_diff

    return _date.astimezone(pytz.timezone('GMT'))


def format_amalgamations_data(data: dict, event_id: Decimal, amalgamation_date: str, amalgamation_type: str) -> dict:
    amalgamations_data = data['amalgamations']

    matched_amalgamations = [
        item for item in amalgamations_data if item.get('e_event_id') == event_id
    ]

    if not matched_amalgamations:
        return None

    formatted_amalgmation = copy.deepcopy(AMALGAMATION)
    amalgamation_info = matched_amalgamations[0]

    formatted_amalgmation['amalgamations']['amalgamation_date'] = amalgamation_date
    formatted_amalgmation['amalgamations']['court_approval'] = bool(amalgamation_info['f_court_approval'])

    formatted_amalgmation['amalgamations']['amalgamation_type'] = amalgamation_type
    formatted_tings = formatted_amalgmation['amalgamating_businesses']
    for ting in matched_amalgamations:
        formatted_tings.append(format_amalgamating_businesses(ting))

    return formatted_amalgmation


def format_amalgamating_businesses(ting_data: dict) -> dict:
    formatted_ting = {}
    role = 'holding' if ting_data['adopted_corp_ind'] else 'amalgamating'

    foreign_identifier = None
    if not (ting_data['ting_corp_num'].startswith('BC') or
            ting_data['ting_corp_num'].startswith('Q') or
            ting_data['ting_corp_num'].startswith('C')):
        foreign_identifier = ting_data['ting_corp_num']

    if foreign_identifier:
        foreign_jurisdiction = 'CA'
        foreign_jurisdiction_region = ting_data['can_jur_typ_cd']
        if foreign_jurisdiction_region == 'OT':
            foreign_jurisdiction = 'US'
            foreign_jurisdiction_region = ting_data['othr_juri_desc']
        formatted_ting = {
            'foreign_jurisdiction': foreign_jurisdiction,
            'foreign_name': ting_data['foreign_nme'],
            'foreign_identifier': foreign_identifier,
            'role': role,
            'foreign_jurisdiction_region': foreign_jurisdiction_region
        }
    else:
        formatted_ting = {
            'ting_identifier': ting_data['ting_corp_num'],
            'role': role,
        }

    return formatted_ting


def format_filing_comments_data(data: dict, event_id: Decimal) -> list:
    filing_comments_data = data['filing_comments']

    matched_filing_comments = [
        item for item in filing_comments_data if item.get('e_event_id') == event_id
    ]

    if not matched_filing_comments:
        return None

    formatted_filing_comments = []
    for x in matched_filing_comments:
        if c := x['lt_notation']:
            timestamp = x['lt_ledger_text_dts_str']
            # Note that only a small number of lt_user_id is BCOMPS,
            # others are None
            # TODO: investigate BCOMPS related stuff
            staff_id = x['lt_user_id']
        else:
            c = x['cl_ledger_desc']
            timestamp = None
            staff_id = None
        comment = {
            'comment': c,
            'timestamp': timestamp,
            'staff_id': staff_id,  # will be updated to real staff_id when loading data into db
        }

        formatted_filing_comments.append(comment)

    return formatted_filing_comments


def format_business_comments_data(data: dict) -> list:
    business_comments_data = data['business_comments']
    formatted_business_comments = []

    for x in business_comments_data:
        c = x['cc_comments'] if x['cc_comments'] else x['cc_accession_comments']
        staff_id = get_username(x)
        comment = {
            'comment': c,
            'timestamp': x['cc_comments_dts_str'],
            'staff_id': staff_id,  # will be updated to real staff_id when loading data into db
        }
        formatted_business_comments.append(comment)

    return formatted_business_comments


def format_in_dissolution_data(data: dict) -> dict:
    if not (in_dissolution_data := data['in_dissolution']):
        return None

    in_dissolution_data = in_dissolution_data[0]

    formatted_in_dissolution = copy.deepcopy(IN_DISSOLUTION)
    batch = formatted_in_dissolution['batches']
    batch_processiong = formatted_in_dissolution['batch_processing']
    furnishing = formatted_in_dissolution['furnishings']

    utc_now_str = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    batch['start_date'] = utc_now_str

    corp_state = in_dissolution_data['cs_state_type_cd']

    batch_processiong['business_identifier'] = in_dissolution_data['cs_corp_num']
    batch_processiong['created_date'] = batch_processiong['last_modified'] = utc_now_str
    batch_processiong['trigger_date'] = in_dissolution_data['e_trigger_dts_str']
    batch_processiong['meta_data'] = {
        'importFromColin': True,
        'colinDissolutionState': corp_state,
    }

    furnishing['business_identifier'] = in_dissolution_data['cs_corp_num']
    furnishing['created_date'] = furnishing['last_modified'] = furnishing['processed_date'] = utc_now_str
    furnishing['meta_data'] = {
        'importFromColin': True,
        'colinDissolutionState': corp_state,
    }

    if corp_state in ('D1F', 'D1T'):
        # stage 1
        batch_processiong['step'] = 'WARNING_LEVEL_1'
        overdue_ar = True if corp_state == 'D1F' else False
        batch_processiong['meta_data'] = {
            **batch_processiong['meta_data'],
            'overdueARs': overdue_ar,
            'overdueTransition': not overdue_ar,
            'stage_1_date': utc_now_str,
        }

        furnishing['furnishing_type'] = 'MAIL'  # as placeholder
        furnishing['furnishing_name'] = 'DISSOLUTION_COMMENCEMENT_NO_AR' if overdue_ar \
            else 'DISSOLUTION_COMMENCEMENT_NO_TR'
    else:
        # stage 2
        batch_processiong['step'] = 'WARNING_LEVEL_2'
        overdue_ar = True if corp_state == 'D2F' else False
        batch_processiong['meta_data'] = {
            **batch_processiong['meta_data'],
            'overdueARs': overdue_ar,
            'overdueTransition': not overdue_ar,
            'stage_2_date': utc_now_str,
        }

        furnishing['furnishing_type'] = 'GAZETTE'
        furnishing['furnishing_name'] = 'INTENT_TO_DISSOLVE'

    return formatted_in_dissolution


def format_users_data(users_data: list) -> list:
    formatted_users = []

    for x in users_data:
        user = copy.deepcopy(USER)
        event_file_types = x['event_file_types'].split(',')
        # skip users if all event_file_type is unsupported or not users for staff comments
        if not any(get_target_filing_type(ef)[0] for ef in event_file_types) \
                and not any(ef == 'STAFF_COMMENT' for ef in event_file_types):
            continue

        username = get_username(x)

        if not username:
            continue

        user = {
            **user,
            'username': username,
            'email': x['u_email_addr'],
            'creation_date': x['earliest_event_dt_str']
        }

        formatted_users.append(user)

    return formatted_users


def format_out_data_data(data: dict) -> dict:
    out_data = data.get('out_data')
    if not out_data:
        return {}

    out_data = out_data[0]
    country, region = map_country_region(out_data['can_jur_typ_cd'])

    date_field = {
        'HCO': 'continuation_out_date',
        'HAO': 'amalgamation_out_date'
    }.get(out_data['state_type_cd'])

    formatted_out_data = {
        'foreign_jurisdiction': country,
        'foreign_jurisdiction_region': region,
        'foreign_legal_name': out_data['home_company_nme'],
        date_field: out_data['cont_out_dt'],
    }

    return formatted_out_data


def map_country_region(can_jur_typ_cd):
    if can_jur_typ_cd != 'OT':
        country = 'CA'
        region = 'FEDERAL' if can_jur_typ_cd == 'FD' else can_jur_typ_cd
    else:  # placeholder for other
        country = 'UNKNOWN'
        region = 'UNKNOWN'

    return country, region


def formatted_data_cleanup(data: dict) -> dict:
    filings_business = data['filings']
    data['updates'] = {
        'businesses': filings_business['update_business_info'],
        'state_filing_index': filings_business['state_filing_index']
    }
    data['unsupported_types'] = filings_business['unsupported_types']

    data['filings'] = filings_business['filings']

    data['admin_email'] = data['businesses']['admin_email']
    del data['businesses']['admin_email']
    data['pass_code'] = data['businesses']['pass_code']
    del data['businesses']['pass_code']

    data['businesses'].update(data['out_data'])
    return data


def get_data_formatters() -> dict:
    ret = {
        'businesses': format_business_data,
        'offices': format_offices_data,
        'parties': format_parties_data,
        'offices_held': format_offices_held_data,
        'share_classes': format_share_classes_data,
        'aliases': format_aliases_data,
        'resolutions': format_resolutions_data,
        'filings': format_filings_data,
        'comments': format_business_comments_data,  # only for business level, filing level will be formatted ith filings
        'in_dissolution': format_in_dissolution_data,
        'out_data': format_out_data_data,  # continuation/amalgamation out
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


def get_business_update_value(key: str, effective_date: str, trigger_date: str, filing_type: str, filing_subtype: str) -> str:
    if filing_type == 'putBackOn':
        value = None
    elif filing_type == 'putBackOff':
        if key == 'restoration_expiry_date':
            value = None
        else:
            value = effective_date
    elif filing_type == 'restoration':
        if key == 'restoration_expiry_date' and \
                filing_subtype in ['limitedRestoration', 'limitedRestorationExtension']:
            value = trigger_date
        else:
            value = None
    else:
        value = effective_date

    return value


def build_filing_json_meta_data(raw_filing_type: str, filing_type: str, filing_subtype: str, effective_date: str, data: dict) -> tuple[dict, dict]:
    filing_json = copy.deepcopy(FILING_JSON)
    filing_json['filing'][raw_filing_type] = {}
    # if conversion has conv filing type, set filing_json
    if raw_filing_type != filing_type and filing_type:
        filing_json['filing'][filing_type] = {}

    meta_data = {
        'colinFilingInfo': {
            'eventType': data['e_event_type_cd'],
            'filingType': data['f_filing_type_cd'],
            'eventId': int(data['e_event_id'])
        },
        'isLedgerPlaceholder': True,
        'colinDisplayName': get_colin_display_name(data)
    }

    if raw_filing_type == 'conversion':
        # will populate state filing info for conversion in the following steps
        # based on converted filing type and converted filing subtype
        if filing_type in LEAR_STATE_FILINGS:
            state_change = True
        else:
            state_change = False
        if filing_type == 'changeOfName':
            name_change = True
            filing_json['filing']['changeOfName'] = {
                'fromLegalName': data['old_corp_name'],
                'toLegalName': data['new_corp_name'],
            }
            meta_data['changeOfName'] = {
                'fromLegalName': data['old_corp_name'],
                'toLegalName': data['new_corp_name'],
            }
        else:
            name_change = False
        filing_json['filing']['conversion'] = {
            'convFilingType': filing_type,
            'convFilingSubType': filing_subtype,
            'stateChange': state_change,
            'nameChange': name_change,
        }
        meta_data['conversion'] = {
            'convFilingType': filing_type,
            'convFilingSubType': filing_subtype,
            'stateChange': state_change,
            'nameChange': name_change,
        }

    if filing_type == 'annualReport':
        meta_data['annualReport'] = {
            'annualReportFilingYear': int(effective_date[:4]),
        }
    elif filing_type == 'dissolution':
        dissolution_date = effective_date[:10]
        meta_data['dissolution'] = {
            'dissolutionType': filing_subtype,
            'dissolutionDate':  dissolution_date,
        }
        filing_json['filing']['dissolution'] = {
            'dissolutionType': filing_subtype,
            'dissolutionDate':  dissolution_date,
        }
    elif filing_type == 'restoration':
        if filing_subtype in ['limitedRestoration', 'limitedRestorationExtension']:
            expiry_date = data['e_trigger_dt_str'][:10]
            meta_data['restoration'] = {
                'expiry': expiry_date,
            }
            filing_json['filing']['restoration'] = {
                'expiry': expiry_date,
            }
        filing_json['filing']['restoration'] = {
            **filing_json['filing']['restoration'],
            'type': filing_subtype,
        }
    elif filing_type == 'alteration':
        meta_data['alteration'] = {}
        if (event_file_type := data['event_file_type']) in LEGAL_TYPE_CHANGE_FILINGS.keys():
            meta_data['alteration'] = {
                **meta_data['alteration'],
                'fromLegalType': LEGAL_TYPE_CHANGE_FILINGS[event_file_type][0],
                'toLegalType': LEGAL_TYPE_CHANGE_FILINGS[event_file_type][1],
            }
        if (old_corp_name := data['old_corp_name']) and (new_corp_name := data['new_corp_name']):
            meta_data['alteration'] = {
                **meta_data['alteration'],
                'fromLegalName': old_corp_name,
                'toLegalName': new_corp_name,
            }
    elif filing_type == 'correction':
        if (event_file_type := data['event_file_type']) == 'FILE_CO_LI':
            meta_data['correction'] = {
                'commentOnly': True
            }
    elif filing_type == 'putBackOff':
        if (event_file_type := data['event_file_type']) == 'SYSDL_NULL':
            filing_json['filing']['putBackOff'] = {
                'details': 'Put back off filing due to expired limited restoration.'
            }
            meta_data['putBackOff'] = {
                'reason': 'Limited Restoration Expired',
                'expiryDate': effective_date[:10]
            }
    elif filing_type in ('amalgamationOut', 'continuationOut'):
        country, region = map_country_region(data['out_can_jur_typ_cd'])
        meta_data[filing_type] = {
                'country': country,
                'region': region,
                'legalName': data['out_home_company_nme'],
                f'{filing_type}Date': data['cont_out_dt'][:10]
            }
        if data['out_othr_juri_desc']:
            meta_data[filing_type]['otherJurisdictionDesc'] = data['out_othr_juri_desc']

    if withdrawn_ts_str := data['f_withdrawn_event_ts_str']:
        withdrawn_ts = datetime.strptime(withdrawn_ts_str, date_format_with_tz)
        meta_data = {
            **meta_data,
            'withdrawnDate': withdrawn_ts.isoformat()
        }

    # TODO: populate meta_data for correction to display correct filing name

    return filing_json, meta_data


def get_colin_display_name(data: dict) -> str:
    event_file_type = data['event_file_type']
    name = EVENT_FILING_DISPLAY_NAME_MAPPING.get(event_file_type)

    # Annual Report
    if event_file_type == EventFilings.FILE_ANNBC.value:
        ar_dt_str = data['f_period_end_dt_str']
        ar_dt = datetime.strptime(ar_dt_str, date_format_with_tz)
        suffix = ar_dt.strftime('%b %d, %Y').upper()
        name = f'{name} - {suffix}'

    # Change of Directors
    elif event_file_type == EventFilings.FILE_NOCDR.value:
        if not data['f_change_at_str']:
            name = f'{name} - Address Change or Name Correction Only'

    # Conversion Ledger
    elif event_file_type == EventFilings.FILE_CONVL.value:
        name = data['cl_ledger_title_txt']

    return name


def build_epoch_filing(business_id: int) -> dict:
    now = datetime.utcnow().replace(tzinfo=pytz.UTC)
    filing = copy.deepcopy(FILING['filings'])
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


def get_username(data: dict) -> str:
    first_name = data.get('u_first_name')
    middle_name = data.get('u_middle_name')
    last_name = data.get('u_last_name')

    username = ' '.join([name for name in [first_name, middle_name, last_name] if name])
    if not username:
        username = data.get('u_user_id')
    if not username:
        username = data.get('p_cc_holder_name')

    return username


def load_data(conn: Connection,
              table_name: str,
              data: dict,
              conflict_column: str = None,
              conflict_error: bool = False,
              expecting_id: bool = True,
              versioned: bool = True) -> Optional[int]:
    columns = ', '.join(data.keys())
    placeholders = ', '.join([f':{key}' for key in data.keys()])

    if conflict_column:
        conflict_value = data[conflict_column]
        check_query = f"select id from {table_name} where {conflict_column} = :conflict_value"
        check_result = conn.execute(text(check_query), {'conflict_value': format_value(conflict_value)}).scalar()
        if check_result:
            if not conflict_error:
                return check_result
            else:
                raise Exception('Trying to reload corp existing in db, run delete script first')

    query = f"""insert into {table_name} ({columns}) values ({placeholders})"""
    if expecting_id:
        query = query + ' returning id'

    result = conn.execute(text(query), format_params(data))

    id = result.scalar() if expecting_id else None

    if versioned and expecting_id:
        data['id'] = id
        data['transaction_id'] = -1  # placeholder value
        data['operation_type'] = 0
        versioned_columns = ', '.join(data.keys())
        versioned_placeholders = ', '.join([f':{key}' for key in data.keys()])
        versioned_query = f"""insert into {table_name}_version ({versioned_columns}) values ({versioned_placeholders})"""
        conn.execute(text(versioned_query), format_params(data))

    return id


def update_data(conn: Connection,
                table_name: str,
                data: dict, column: str,
                value: any,
                versioned: bool = True) -> int:
    update_pairs = [f'{k} = :{k}' for k in data.keys()]
    update_pairs_str = ', '.join(update_pairs)
    query = f"""update {table_name} set {update_pairs_str} where {column}=:condition_value returning id"""

    params = copy.deepcopy(data)
    params['condition_value'] = value

    result = conn.execute(text(query), format_params(params))
    id = result.scalar()

    if versioned:
        versioned_query = f"""update {table_name}_version set {update_pairs_str} where {column}=:condition_value"""
        conn.execute(text(versioned_query), format_params(params))

    return id


def update_versioning(conn: Connection,
                      transaction_id: int,
                      versioning_mapper: dict) -> None:
    for k, v in versioning_mapper.items():
        query = f"""update {k} set transaction_id = {transaction_id} where id in :ids"""
        conn.execute(text(query).bindparams(bindparam('ids', expanding=True)), {'ids': v})


def format_value(value) -> str:
    if isinstance(value, dict):
        return json.dumps(value)
    return value


def format_params(data: dict) -> dict:
    formatted = {}
    for k, v in data.items():
        formatted[k] = format_value(v)
    return formatted
