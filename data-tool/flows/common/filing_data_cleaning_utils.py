import re
import datetime

from .data.firms_data import get_custom_corp_names
from .filing_data_utils import get_is_frozen


def clean_naics_data(filing_data: dict):

    naics_code = filing_data['bd_naics_code']
    naics_desc = filing_data['bd_description']

    if naics_code:
        if is_naics_code_format(naics_code):
            naics_desc = re.sub(r"\s*\[NAICS-\d{6}\]", '', naics_desc)
            naics_desc = naics_desc.strip()
            filing_data['bd_description'] = naics_desc
        elif naics_code == 'N/A' or naics_code == '0000':
            filing_data['bd_naics_code'] = None
        else:
            filing_data['bd_description'] = f'{naics_desc} (NAICS - {naics_code})'
    else:
        filing_data['bd_naics_code'] = None

    if naics_desc:
        naics_desc = re.sub(r"\s*\[NAICS-N/A\]", '', naics_desc)
        naics_desc = naics_desc.strip()
        filing_data['bd_description'] = naics_desc


def is_naics_code_format(value: str) -> bool:
    """Determine whether input value is a valid NAICS code format."""
    pattern = '\\d{6}'
    result = bool(re.fullmatch(pattern, value))
    return result


def clean_corp_party_data(filing_data: dict):
    corp_parties_data = filing_data['corp_parties']
    corp_type = filing_data['c_corp_type_cd']

    for corp_party in corp_parties_data:
        # corp party type related cleaning/validation
        corp_party_type = corp_party['cp_party_typ_cd']
        if not corp_party_type:
            raise Exception('no corp party type provided')

        if corp_party_type in ('FIO'):
            if (not corp_party['cp_first_name'] and not corp_party['cp_last_name']
                    and not corp_party['cp_middle_name']) \
                    and (corp_party['cp_business_name'] or corp_party['cp_bus_company_num']):
                corp_party_type = 'FBO'
                break
            if not(corp_party['cp_first_name'] or corp_party['cp_last_name'] or corp_party['cp_middle_name']):
                raise Exception(f'no first, last or middle name provided for {corp_party_type}')

            corp_party['cp_business_name'] = ''
            corp_party['cp_bus_company_num'] = None
        elif corp_party_type == 'FCP':
            if not(corp_party['cp_first_name'] or corp_party['cp_last_name'] or corp_party['cp_middle_name']
                   or corp_party['cp_business_name']):
                raise Exception(f'no cp_business_name provided or first, last or middle name provided for {corp_party_type}')

            if corp_party['cp_first_name'] or corp_party['cp_last_name'] or corp_party['cp_middle_name']:
                corp_party['cp_business_name'] = ''
                corp_party['cp_bus_company_num'] = None
            else:
                corp_party['cp_first_name'] = ''
                corp_party['cp_last_name'] = ''
                corp_party['cp_middle_name'] = ''
        elif corp_party_type == 'FBO':
            corp_party['cp_first_name'] = ''
            corp_party['cp_last_name'] = ''
            corp_party['cp_middle_name'] = ''

        # clean addresses
        if corp_party['ma_addr_id']:
            clean_address_data(corp_party, 'ma_')
        if corp_party['da_addr_id']:
            clean_address_data(corp_party, 'da_')
        # if partner or proprietor delivery address does not exist use mailing address
        elif not corp_party['da_addr_id'] and corp_party_type in ('FIO', 'FBO'):
            copy_address_data('ma_', 'da_', corp_party)


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
    corp_num = filing_data['c_corp_num']

    corp_name_mapping_dict = get_custom_corp_names()

    if corp_name := corp_name_mapping_dict.get(corp_num):
        corp_name_suffix = config.CORP_NAME_SUFFIX
        corp_name = f'{corp_name}{corp_name_suffix}'
        filing_data['curr_corp_name'] = corp_name
        filing_data['cn_corp_name'] = corp_name

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
