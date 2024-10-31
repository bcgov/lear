import re
import datetime

from flows.common.filing_data_utils import get_is_frozen

def clean_corp_party_data(filing_data: dict):
    corp_parties_data = filing_data['corp_parties']
    corp_type = filing_data['c_corp_type_cd']

    for corp_party in corp_parties_data:
        # corp party type related cleaning/validation
        corp_party_type = corp_party['cp_party_typ_cd']
        if not corp_party_type:
            raise Exception('no corp party type provided')

        # clean addresses
        if corp_party['ma_addr_id']:
            clean_address_data(corp_party, 'ma_')
        if corp_party['da_addr_id']:
            clean_address_data(corp_party, 'da_')


def copy_address_data(source_address_prefix: str, target_address_prefix: str, corp_party: dict):
    corp_party[f'{target_address_prefix}addr_id'] = corp_party[f'{source_address_prefix}addr_id']
    corp_party[f'{target_address_prefix}province'] = corp_party[f'{source_address_prefix}province']
    corp_party[f'{target_address_prefix}country_typ_cd'] = corp_party[f'{source_address_prefix}country_typ_cd']
    corp_party[f'{target_address_prefix}postal_cd'] = corp_party[f'{source_address_prefix}postal_cd']
    corp_party[f'{target_address_prefix}addr_line_1'] = corp_party[f'{source_address_prefix}addr_line_1']
    corp_party[f'{target_address_prefix}addr_line_2'] = corp_party[f'{source_address_prefix}addr_line_2']
    corp_party[f'{target_address_prefix}addr_line_3'] = corp_party[f'{source_address_prefix}addr_line_3']
    corp_party[f'{target_address_prefix}city'] = corp_party[f'{source_address_prefix}city']
    corp_party[f'{target_address_prefix}address_format_type'] = corp_party[f'{source_address_prefix}address_format_type']
    corp_party[f'{target_address_prefix}delivery_instructions'] = corp_party[f'{source_address_prefix}delivery_instructions']
    corp_party[f'{target_address_prefix}unit_no'] = corp_party[f'{source_address_prefix}unit_no']
    corp_party[f'{target_address_prefix}unit_type'] = corp_party[f'{source_address_prefix}unit_type']
    corp_party[f'{target_address_prefix}civic_no'] = corp_party[f'{source_address_prefix}civic_no']
    corp_party[f'{target_address_prefix}civic_no_suffix'] = corp_party[f'{source_address_prefix}civic_no_suffix']
    corp_party[f'{target_address_prefix}street_name'] = corp_party[f'{source_address_prefix}street_name']
    corp_party[f'{target_address_prefix}street_type'] = corp_party[f'{source_address_prefix}street_type']
    corp_party[f'{target_address_prefix}street_direction'] = corp_party[f'{source_address_prefix}street_direction']
    corp_party[f'{target_address_prefix}lock_box_no'] = corp_party[f'{source_address_prefix}lock_box_no']
    corp_party[f'{target_address_prefix}installation_type'] = corp_party[f'{source_address_prefix}installation_type']
    corp_party[f'{target_address_prefix}installation_name'] = corp_party[f'{source_address_prefix}installation_name']
    corp_party[f'{target_address_prefix}installation_qualifier'] = corp_party[f'{source_address_prefix}installation_qualifier']
    corp_party[f'{target_address_prefix}route_service_type'] = corp_party[f'{source_address_prefix}route_service_type']
    corp_party[f'{target_address_prefix}route_service_no'] = corp_party[f'{source_address_prefix}route_service_no']


def clean_offices_data(filing_data: dict):
    offices_data = filing_data['offices']

    for office in offices_data:
        if office['ma_addr_id']:
            clean_address_data(office, 'ma_')
        if office['da_addr_id']:
            clean_address_data(office, 'da_')


def clean_address_data(address_data: dict, address_prefix: str):
    address_format_type_key = f'{address_prefix}address_format_type'
    address_format_type = address_data[address_format_type_key]

    if not address_format_type:
        raise Exception('no address format type provided')

    if address_format_type == 'OR':
        address_format_type = 'FOR'
        address_data[address_format_type_key] = address_format_type
        return

    if address_format_type not in ('BAS', 'FOR', 'ADV'):
        raise Exception('unknown address format type: ' + address_format_type)


def clean_corp_data(config, filing_data: dict):
    # corp_num = filing_data['c_corp_num']

    # corp_name_mapping_dict = get_custom_corp_names()
    #
    # if corp_name := corp_name_mapping_dict.get(corp_num):
    #     corp_name_suffix = config.CORP_NAME_SUFFIX
    #     corp_name = f'{corp_name}{corp_name_suffix}'
    #     filing_data['curr_corp_name'] = corp_name
    #     filing_data['cn_corp_name'] = corp_name

    is_frozen = get_is_frozen(filing_data)
    filing_data['c_is_frozen'] = is_frozen


def clean_event_data(filing_data: dict):
    e_event_dts = filing_data['e_event_dts_pacific']
    # for events where date created is not known, use previous event/filing data.
    # LEAR has issues re-creating versioning history for outputs if we don't do this
    if e_event_dts.year == 1 and len(filing_data.get('prev_event_filing_data')) > 0:
        prev_f_effective_dt_str = filing_data['prev_event_filing_data']['f_effective_dt_str']
        prev_f_effective_dts_pacific = filing_data['prev_event_filing_data']['f_effective_dts_pacific']
        new_f_effective_dts_pacific = prev_f_effective_dts_pacific + datetime.timedelta(seconds=1)

        filing_data['e_event_dt_str'] = prev_f_effective_dt_str
        filing_data['e_event_dts_pacific'] = new_f_effective_dts_pacific
        filing_data['f_effective_dt_str'] = prev_f_effective_dt_str
        filing_data['f_effective_dts_pacific'] = new_f_effective_dts_pacific
