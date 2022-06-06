from .firm_filing_base_json import get_base_registration_filing_json, get_base_change_registration_filing_json
from .firm_filing_data_utils import get_certified_by, get_street_additional, get_party_role_type, get_party_type



class FirmFilingJsonFactoryService:

    def __init__(self, event_filing_data: dict):
        self._event_filing_data = event_filing_data
        self._filing_data = event_filing_data['data']
        self._event_id = self._filing_data['f_event_id']
        self._prev_event_id = self._filing_data.get('prev_event_filing_data', {}).get('f_event_id', None)
        self._target_lear_filing_type = self._filing_data['target_lear_filing_type']
        self._corp_type_cd = self._filing_data['c_corp_type_cd']


    def get_filing_json(self):
        filing_json = None

        if self._target_lear_filing_type == 'registration':
            filing_json = self.get_registration_filing_json()
        elif self._target_lear_filing_type == 'changeOfRegistration':
            filing_json = self.get_change_registration_filing_json()

        return filing_json


    def get_registration_filing_json(self):
        result = self.build_registration_filing()
        return result


    def build_registration_filing(self):
        num_parties = len(self._filing_data['corp_parties'])
        filing_dict = get_base_registration_filing_json(num_parties)

        self.populate_header(filing_dict)
        self.populate_filing_business(filing_dict)
        self.populate_registration(filing_dict)
        return filing_dict


    def get_change_registration_filing_json(self):
        result = self.build_change_registration_filing()
        return result


    def build_change_registration_filing(self):
        num_parties = len(self._filing_data['corp_parties'])
        filing_dict = get_base_change_registration_filing_json(num_parties)

        self.populate_header(filing_dict)
        self.populate_filing_business(filing_dict)
        self.populate_change_registration(filing_dict)
        return filing_dict


    def populate_header(self, filing_dict: dict):
        header = filing_dict['filing']['header']
        effective_dts = self._filing_data['f_effective_dts']
        effective_dt_str = effective_dts.strftime('%Y-%m-%d')
        header['date'] = effective_dt_str

        certified_by = get_certified_by(self._filing_data)
        header['certifiedBy'] = certified_by
        header['folioNumber'] = self._filing_data['p_folio_num']


    def populate_filing_business(self, filing_dict: dict):
        business_dict = filing_dict['filing']['business']
        business_dict['legalType'] = self._filing_data['c_corp_type_cd']
        business_dict['identifier'] = self._filing_data['c_corp_num']
        business_dict['foundingDate'] = str(self._filing_data['bd_business_start_date'])


    def populate_registration(self, filing_dict: dict):
        registration_dict = filing_dict['filing']['registration']

        registration_dict['businessType'] = self._filing_data['c_corp_type_cd']
        registration_dict['startDate'] = str(self._filing_data['c_recognition_dts'])

        self.populate_registration_business(registration_dict)
        self.populate_registration_offices(registration_dict)
        self.populate_registration_parties(registration_dict)
        self.populate_registration_nr(registration_dict)


    def populate_change_registration(self, filing_dict: dict):
        change_registration_dict = filing_dict['filing']['changeOfRegistration']

        if self._filing_data.get('bd_start_event_id', None):
            self.populate_registration_business(change_registration_dict)
        else:
            del change_registration_dict['business']

        if len(self._filing_data['offices']) > 0:
            self.populate_registration_offices(change_registration_dict)
        else:
            del change_registration_dict['offices']

        if len(self._filing_data['corp_parties']) > 0:
            self.populate_registration_parties(change_registration_dict)
        else:
            del change_registration_dict['parties']

        if self._filing_data.get('cn_start_event_id') and self._filing_data.get('cn_corp_name'):
            self.populate_registration_nr(change_registration_dict)
        else:
            del change_registration_dict['nameRequest']


    def populate_registration_offices(self, registration_dict: dict):
        office = registration_dict['offices']['businessOffice']
        if len(self._filing_data['offices']) == 0:
            del registration_dict['offices']['businessOffice']

        if len(self._filing_data['offices']) > 0:
            filing_data_office = self._filing_data['offices'][0]

            mailing_addr = office['mailingAddress']
            self.populate_address(mailing_addr, filing_data_office, 'ma_')

            delivery_addr = office['deliveryAddress']
            self.populate_address(delivery_addr, filing_data_office, 'da_')


    def populate_registration_parties(self, registration_dict: dict):
        parties = registration_dict['parties']

        for idx, party in enumerate(parties):
            filing_data_party = self._filing_data['corp_parties'][idx]
            self.populate_registration_party(party, filing_data_party)

            mailing_addr_id = filing_data_party['ma_addr_id']
            if mailing_addr_id:
                mailing_addr = party['mailingAddress']
                self.populate_address(mailing_addr, filing_data_party, 'ma_')
            else:
                del party['mailingAddress']

            delivery_addr_id = filing_data_party['da_addr_id']
            if delivery_addr_id:
                delivery_addr = party['deliveryAddress']
                self.populate_address(delivery_addr, filing_data_party, 'da_')
            else:
                del party['deliveryAddress']


    def populate_registration_party(self, party_dict: dict, filing_party_data: dict):
        party_role_dict = party_dict['roles'][0]
        party_officer_dict = party_dict['officer']

        self.populate_party_role(party_role_dict, filing_party_data)
        self.populate_party_officer(party_officer_dict, filing_party_data)


    def populate_party_role(self, party_role: dict, filing_party_data: dict):
        party_role_type = get_party_role_type(self._corp_type_cd, filing_party_data['cp_party_typ_cd'])
        party_role['roleType'] = party_role_type
        party_role['appointmentDate'] = filing_party_data['cp_appointment_dt']


    def is_previous_colin_party(self, filing_party_data: dict):
        start_event_id = filing_party_data['cp_start_event_id']
        prev_party_id = filing_party_data['cp_prev_party_id']

        if prev_party_id or \
                (not prev_party_id and
                 self._prev_event_id and
                 start_event_id != self._event_id):
            return True

        return False


    def populate_officer_json(self, officer: dict, filing_party_data: dict, party_type: str, to_upper=False):
        if to_upper:
            officer['email'] = filing_party_data.get('cp_email_address', '').upper()
            officer['lastName'] = filing_party_data.get('cp_last_name', '').upper()
            officer['firstName'] = filing_party_data.get('cp_first_name', '').upper()
            officer['middleName'] = filing_party_data.get('cp_middle_name', '').upper()
            officer['partyType'] = party_type
            officer['organizationName'] = filing_party_data.get('cp_business_name', '').upper()
            officer['identifier'] = filing_party_data['cp_bus_company_num']
        else:
            officer['email'] = filing_party_data.get('cp_email_address', '')
            officer['lastName'] = filing_party_data.get('cp_last_name', '')
            officer['firstName'] = filing_party_data.get('cp_first_name', '')
            officer['middleName'] = filing_party_data.get('cp_middle_name', '')
            officer['partyType'] = party_type
            officer['organizationName'] = filing_party_data.get('cp_business_name', '')
            officer['identifier'] = filing_party_data['cp_bus_company_num']


    def populate_previous_party_officer_json(self, officer: dict, filing_party_data: dict):
        prev_party_id = filing_party_data['cp_prev_party_id']

        if prev_party_id:
            prev_parties = self._filing_data['prev_event_filing_data']['corp_parties']
            prev_party_match = next(prev_party
                                    for prev_party in prev_parties
                                    if prev_party['cp_corp_party_id'] == prev_party_id)
            prev_party_type = get_party_type(prev_party_match)
            prev_officer = {}
            prev_officer['email'] = prev_party_match.get('cp_email_address', '').upper()
            prev_officer['lastName'] = prev_party_match.get('cp_last_name', '').upper()
            prev_officer['firstName'] = prev_party_match.get('cp_first_name', '').upper()
            prev_officer['middleName'] = prev_party_match.get('cp_middle_name', '').upper()
            prev_officer['partyType'] = prev_party_type
            prev_officer['organizationName'] = prev_party_match.get('cp_business_name', '').upper()
            prev_officer['identifier'] = prev_party_match['cp_bus_company_num']
            officer['prev_colin_party'] = prev_officer
        else:
            prev_officer = {}
            party_type = get_party_type(filing_party_data)
            prev_officer['email'] = filing_party_data.get('cp_email_address', '').upper()
            prev_officer['lastName'] = filing_party_data.get('cp_last_name', '').upper()
            prev_officer['firstName'] = filing_party_data.get('cp_first_name', '').upper()
            prev_officer['middleName'] = filing_party_data.get('cp_middle_name', '').upper()
            prev_officer['partyType'] = party_type
            prev_officer['organizationName'] = filing_party_data.get('cp_business_name', '').upper()
            prev_officer['identifier'] = filing_party_data['cp_bus_company_num']
            officer['prev_colin_party'] = prev_officer


    def populate_party_officer(self, party_officer: dict, filing_party_data: dict):
        party_type = get_party_type(filing_party_data)
        self.populate_officer_json(party_officer, filing_party_data, party_type)
        if self.is_previous_colin_party(filing_party_data):
            self.populate_previous_party_officer_json(party_officer, filing_party_data)


    def populate_address(self, address_dict: dict, address_data_dict: dict, address_key_prefix: str):
        address_format_type_key = f'{address_key_prefix}address_format_type'
        address_format_type = address_data_dict[address_format_type_key]

        if address_format_type == 'BAS':
            # todo sort out how basic should work
            # populate_basic_address(address_dict, filing_data, address_key_prefix)
            self.populate_foreign_address(address_dict, address_data_dict, address_key_prefix)
        elif address_format_type == 'FOR':
            self.populate_foreign_address(address_dict, address_data_dict, address_key_prefix)
        elif address_format_type == 'ADV':
            # todo sort out how advanced should work
            # populate_advanced_address(address_dict, filing_data, address_key_prefix)
            self.populate_foreign_address(address_dict, address_data_dict, address_key_prefix)
        else:
            raise Exception('unknown address format type: ' + address_format_type)


    def populate_basic_address(self, address_dict: dict, address_data_dict: dict, address_key_prefix: str):

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


    def populate_advanced_address(self, address_dict: dict, address_data_dict: dict, address_key_prefix: str):
        raise Exception('still need to implement')


    def populate_foreign_address(self, address_dict: dict, address_data_dict: dict, address_key_prefix: str):
        postal_code_key = f'{address_key_prefix}postal_cd'
        city_key = f'{address_key_prefix}city'
        province_key = f'{address_key_prefix}province'
        country_key = f'{address_key_prefix}country_typ_cd'
        delivery_instructions_key = f'{address_key_prefix}delivery_instructions'
        addr_line_1_key = f'{address_key_prefix}addr_line_1'
        addr_line_2_key = f'{address_key_prefix}addr_line_2'
        addr_line_3_key = f'{address_key_prefix}addr_line_3'
        addr_line_2 = address_data_dict[addr_line_2_key]
        addr_line_3 = address_data_dict[addr_line_3_key]
        street_additional = get_street_additional(addr_line_2, addr_line_3)

        address_dict['postalCode'] = address_data_dict[postal_code_key]
        address_dict['addressCity'] = address_data_dict[city_key]
        address_dict['addressRegion'] = address_data_dict[province_key]
        address_dict['addressCountry'] = address_data_dict[country_key]
        address_dict['streetAddress'] = address_data_dict[addr_line_1_key]
        address_dict['streetAddressAdditional'] = street_additional
        address_dict['deliveryInstructions'] = address_data_dict[delivery_instructions_key]


    def populate_registration_business(self, registration_dict: dict):
        business_dict = registration_dict['business']
        naics_dict = business_dict['naics']
        business_dict['identifier'] = self._filing_data['c_corp_num']
        self.populate_naics(naics_dict)


    def populate_naics(self, naics_dict: dict):
        naics_dict['naicsCode'] = self._filing_data['bd_naics_code']
        naics_dict['naicsDescription'] = self._filing_data['bd_description']


    def populate_registration_nr(self, registration_dict: dict):
        nr_dict = registration_dict['nameRequest']
        nr_dict['nrNumber'] = self._filing_data['f_nr_num']
        nr_dict['legalName'] = self._filing_data['cn_corp_name']
        nr_dict['legalType'] = self._corp_type_cd
