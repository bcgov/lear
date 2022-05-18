from .firm_filing_base_json import get_base_sp_registration_json
from .firm_filing_data_utils import get_certified_by, get_street_additional, get_party_role_type, get_party_type

def get_registration_sp_filing_json(filing_data: dict):
    result = build_registration_sp_filing(filing_data)
    return result


def build_registration_sp_filing(filing_data: dict):
    num_parties = len(filing_data['corp_parties'])
    filing_dict = get_base_sp_registration_json(num_parties)
    corp_type_cd = filing_data['c_corp_type_cd']

    populate_header(filing_dict, filing_data)
    populate_filing_business(filing_dict, filing_data)
    populate_registration(filing_dict, filing_data, corp_type_cd)
    return filing_dict


def populate_header(filing_dict: dict, filing_data: dict):
    header = filing_dict['filing']['header']
    effective_dts = filing_data['f_effective_dts']
    effective_dt_str = effective_dts.strftime('%Y-%m-%d')
    header['date'] = effective_dt_str

    certified_by = get_certified_by(filing_data)
    header['certifiedBy'] = certified_by
    header['folioNumber'] = filing_data['p_folio_num']


def populate_filing_business(filing_dict: dict, filing_data: dict):
    business_dict = filing_dict['filing']['business']
    business_dict['legalType'] = filing_data['c_corp_type_cd']
    business_dict['identifier'] = filing_data['c_corp_num']
    business_dict['foundingDate'] = str(filing_data['bd_business_start_date'])

def populate_registration(filing_dict: dict, filing_data: dict, corp_type_cd: str):
    registration_dict = filing_dict['filing']['registration']

    registration_dict['businessType'] = filing_data['c_corp_type_cd']
    registration_dict['startDate'] = str(filing_data['c_recognition_dts'])

    populate_registration_business(registration_dict, filing_data)
    populate_registration_offices(registration_dict, filing_data)
    populate_registration_parties(registration_dict, filing_data, corp_type_cd)
    populate_registration_nr(registration_dict, filing_data)


def populate_registration_offices(registration_dict: dict, filing_data: dict):
    office = registration_dict['offices']['businessOffice']
    filing_data_office = filing_data['offices'][0]

    mailing_addr = office['mailingAddress']
    populate_address(mailing_addr, filing_data_office, 'ma_')

    delivery_addr = office['deliveryAddress']
    populate_address(delivery_addr, filing_data_office, 'da_')


def populate_registration_parties(registration_dict: dict, filing_data: dict, corp_type_cd: str):
    parties = registration_dict['parties']

    for idx, party in enumerate(parties):
        filing_data_party = filing_data['corp_parties'][idx]
        populate_registration_party(party, filing_data_party, corp_type_cd)

        mailing_addr_id = filing_data_party['ma_addr_id']
        if mailing_addr_id:
            mailing_addr = party['mailingAddress']
            populate_address(mailing_addr, filing_data_party, 'ma_')
        else:
            del party['mailingAddress']

        delivery_addr_id = filing_data_party['da_addr_id']
        if delivery_addr_id:
            delivery_addr = party['deliveryAddress']
            populate_address(delivery_addr, filing_data_party, 'da_')
        else:
            del party['deliveryAddress']


def populate_registration_party(party_dict: dict, filing_party_data: dict, corp_type_cd: str):
    party_role_dict = party_dict['roles'][0]
    party_officer_dict = party_dict['officer']

    populate_party_role(party_role_dict, filing_party_data, corp_type_cd)
    populate_party_officer(party_officer_dict, filing_party_data)


def populate_party_role(party_role: dict, filing_party_data: dict, corp_type_cd: str):
    party_role_type = get_party_role_type(corp_type_cd, filing_party_data['cp_party_typ_cd'])
    party_role['roleType'] = party_role_type
    party_role['appointmentDate'] = filing_party_data['cp_appointment_dt']


def populate_party_officer(party_officer: dict, filing_party_data: dict):
    party_role_type = filing_party_data['cp_party_typ_cd']
    party_type = get_party_type(party_role_type, filing_party_data)
    party_officer['email'] = filing_party_data['cp_email_address']
    party_officer['lastName'] = filing_party_data['cp_last_name']
    party_officer['firstName'] = filing_party_data['cp_first_name']
    party_officer['middleName'] = filing_party_data['cp_middle_name']
    party_officer['partyType'] = party_type
    party_officer['organizationName'] = filing_party_data['cp_business_name']
    party_officer['identifier'] = filing_party_data['cp_bus_company_num']


def populate_address(address_dict: dict, filing_data: dict, address_key_prefix: str):
    address_format_type_key = f'{address_key_prefix}address_format_type'
    address_format_type = filing_data[address_format_type_key]

    if address_format_type == 'BAS':
        # todo sort out how basic should work
        # populate_basic_address(address_dict, filing_data, address_key_prefix)
        populate_foreign_address(address_dict, filing_data, address_key_prefix)
    elif address_format_type == 'FOR':
        populate_foreign_address(address_dict, filing_data, address_key_prefix)
    elif address_format_type == 'ADV':
        # todo sort out how advanced should work
        # populate_advanced_address(address_dict, filing_data, address_key_prefix)
        populate_foreign_address(address_dict, filing_data, address_key_prefix)
    else:
        raise Exception('unknown address format type: ' + address_format_type)


def populate_basic_address(address_dict: dict, filing_data: dict, address_key_prefix: str):

    unit_type_key = f'{address_key_prefix}unit_type'
    unit_no_key = f'{address_key_prefix}unit_no'
    civic_no_key = f'{address_key_prefix}civic_no'
    civic_no_suffix_key = f'{address_key_prefix}civic_no_suffix'
    street_name_key = f'{address_key_prefix}street_name'
    street_type_key = f'{address_key_prefix}street_type'
    street_direction_key = f'{address_key_prefix}street_direction'

    postal_code_key = f'{address_key_prefix}postal_cd'
    city_key = f'{address_key_prefix}city'
    province_key = f'{address_key_prefix}province'


def populate_advanced_address(address_dict: dict, filing_data: dict, address_key_prefix: str):
    raise Exception('still need to implement')


def populate_foreign_address(address_dict: dict, filing_data: dict, address_key_prefix: str):
    postal_code_key = f'{address_key_prefix}postal_cd'
    city_key = f'{address_key_prefix}city'
    province_key = f'{address_key_prefix}province'
    country_key = f'{address_key_prefix}country_typ_cd'
    delivery_instructions_key = f'{address_key_prefix}delivery_instructions'
    addr_line_1_key = f'{address_key_prefix}addr_line_1'
    addr_line_2_key = f'{address_key_prefix}addr_line_2'
    addr_line_3_key = f'{address_key_prefix}addr_line_3'
    addr_line_2 = filing_data[addr_line_2_key]
    addr_line_3 = filing_data[addr_line_3_key]
    street_additional = get_street_additional(addr_line_2, addr_line_3)

    address_dict['postalCode'] = filing_data[postal_code_key]
    address_dict['addressCity'] = filing_data[city_key]
    address_dict['addressRegion'] = filing_data[province_key]
    address_dict['addressCountry'] = filing_data[country_key]
    address_dict['streetAddress'] = filing_data[addr_line_1_key]
    address_dict['streetAddressAdditional'] = street_additional
    address_dict['deliveryInstructions'] = filing_data[delivery_instructions_key]


def populate_registration_business(registration_dict: dict, filing_data: dict):
    business_dict = registration_dict['business']
    naics_dict = business_dict['naics']

    business_dict['identifier'] = filing_data['c_corp_num']

    populate_naics(naics_dict, filing_data)


def populate_naics(naics_dict: dict, filing_data: dict):
    naics_dict['naicsCode'] = filing_data['bd_naics_code']
    naics_dict['naicsDescription'] = filing_data['bd_description']


def populate_registration_nr(registration_dict: dict, filing_data: dict):
    nr_dict = registration_dict['nameRequest']

    nr_dict['nrNumber'] = filing_data['f_nr_num']
    nr_dict['legalName'] = filing_data['cn_corp_name']
    nr_dict['legalType'] = filing_data['c_corp_type_cd']
