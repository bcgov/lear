from .firm_filing_base_json import get_base_registration_filing_json, get_base_change_registration_filing_json, \
    get_base_dissolution_filing_json
from .firm_filing_data_utils import get_certified_by, get_party_role_type, get_party_type, \
    get_street_address, get_street_additional, AddressFormatType


class FirmFilingJsonFactoryService:

    def __init__(self, event_filing_data: dict):
        self._event_filing_data = event_filing_data
        self._filing_data = event_filing_data['data']
        self._target_lear_filing_type = self._filing_data['target_lear_filing_type']
        # dissolution filing only needs FCP as party.  remove existing parties which is required for other files
        if self._target_lear_filing_type == 'dissolution':
            filing_data_parties = self._filing_data['corp_parties']
            filing_data_completing_party = next((filing_data_party
                                    for filing_data_party in filing_data_parties
                                    if filing_data_party and filing_data_party['cp_party_typ_cd'] == 'FCP'), None)
            if filing_data_completing_party:
                self._filing_data['corp_parties'] = [filing_data_completing_party]
            else:
                self._filing_data['corp_parties'] = []

        self._event_id = self._filing_data['f_event_id']
        self._prev_event_id = self._filing_data.get('prev_event_filing_data', {}).get('f_event_id', None)
        self._corp_type_cd = self._filing_data['c_corp_type_cd']


    def get_filing_json(self):
        filing_json = None

        if self._target_lear_filing_type == 'registration':
            filing_json = self.get_registration_filing_json()
        elif self._target_lear_filing_type == 'changeOfRegistration':
            filing_json = self.get_change_registration_filing_json()
        elif self._target_lear_filing_type == 'dissolution':
            filing_json = self.get_voluntary_dissolution_filing_json()

        return filing_json


    def get_registration_filing_json(self):
        result = self.build_registration_filing()
        return result


    def build_registration_filing(self):
        num_parties = len(self._filing_data['corp_parties'])
        filing_root_dict = get_base_registration_filing_json(num_parties)

        self.populate_header(filing_root_dict)
        self.populate_business(filing_root_dict)
        self.populate_registration(filing_root_dict)
        return filing_root_dict


    def get_change_registration_filing_json(self):
        result = self.build_change_registration_filing()
        return result


    def build_change_registration_filing(self):
        num_parties = len(self._filing_data['corp_parties'])
        filing_root_dict = get_base_change_registration_filing_json(num_parties)

        self.populate_header(filing_root_dict)
        self.populate_business(filing_root_dict)
        self.populate_change_registration(filing_root_dict)
        return filing_root_dict


    def get_voluntary_dissolution_filing_json(self):
        result = self.build_voluntary_dissolution_filing()
        return result


    def build_voluntary_dissolution_filing(self):
        filing_root_dict = get_base_dissolution_filing_json('voluntary')

        self.populate_header(filing_root_dict)
        self.populate_business(filing_root_dict)
        self.populate_dissolution(filing_root_dict)
        return filing_root_dict


    def populate_header(self, filing_root_dict: dict):
        header = filing_root_dict['filing']['header']
        effective_dt_str= self._filing_data['f_effective_dt_str']
        header['date'] = effective_dt_str

        certified_by = get_certified_by(self._filing_data)
        header['certifiedBy'] = certified_by
        header['folioNumber'] = self._filing_data['p_folio_num']


    def populate_business(self, filing_root_dict: dict):
        business_dict = filing_root_dict['filing']['business']
        business_dict['legalType'] = self._filing_data['c_corp_type_cd']
        business_dict['identifier'] = self._filing_data['c_corp_num']
        business_dict['foundingDate'] = str(self._filing_data['c_recognition_dts_utc'])


    def populate_registration(self, filing_root_dict: dict):
        registration_dict = filing_root_dict['filing']['registration']

        registration_dict['businessType'] = self._filing_data['c_corp_type_cd']
        registration_dict['startDate'] = str(self._filing_data['c_recognition_dts_utc'])

        self.populate_filing_business(registration_dict)
        self.populate_offices(registration_dict)
        self.populate_parties(registration_dict)
        self.populate_nr(registration_dict)


    def populate_change_registration(self, filing_dict: dict):
        change_registration_dict = filing_dict['filing']['changeOfRegistration']

        if self._filing_data.get('bd_start_event_id', None):
            self.populate_filing_business(change_registration_dict)
        else:
            del change_registration_dict['business']

        if len(self._filing_data['offices']) > 0:
            self.populate_offices(change_registration_dict)
        else:
            del change_registration_dict['offices']

        if len(self._filing_data['corp_parties']) > 0:
            self.populate_parties(change_registration_dict)
        else:
            del change_registration_dict['parties']

        if self._filing_data.get('cn_start_event_id') and self._filing_data.get('cn_corp_name'):
            self.populate_nr(change_registration_dict)
        else:
            del change_registration_dict['nameRequest']


    def populate_offices(self, registration_dict: dict):
        office = registration_dict['offices']['businessOffice']
        if len(self._filing_data['offices']) == 0:
            del registration_dict['offices']['businessOffice']

        if len(self._filing_data['offices']) > 0:
            filing_data_office = self._filing_data['offices'][0]

            mailing_addr = office['mailingAddress']
            self.populate_address(mailing_addr, filing_data_office, 'ma_')

            delivery_addr = office['deliveryAddress']
            self.populate_address(delivery_addr, filing_data_office, 'da_')


    def populate_parties(self, filings_dict: dict):
        parties = filings_dict['parties']

        for idx, party in enumerate(parties):
                filing_data_party = self._filing_data['corp_parties'][idx]
                self.populate_party(party, filing_data_party)

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


    def populate_party(self, party_dict: dict, filing_party_data: dict):
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
            if self.can_populate_prev_officer_with_current_officer(filing_party_data):
                self.populate_previous_party_officer(officer, filing_party_data)
            else:
                prev_parties = self._filing_data['prev_event_filing_data']['corp_parties']
                prev_party_match = next(prev_party
                                        for prev_party in prev_parties
                                        if prev_party['cp_corp_party_id'] == prev_party_id)
                self.populate_previous_party_officer(officer, prev_party_match)
        else:
            self.populate_previous_party_officer(officer, filing_party_data)


    def can_populate_prev_officer_with_current_officer(self, filing_party_data: dict):
        if not filing_party_data.get('cp_prev_party_id'):
            return False

        cp_start_event_id = filing_party_data['cp_start_event_id']
        cp_end_event_id = filing_party_data['cp_end_event_id']

        if self._event_id != cp_start_event_id and \
            (not cp_end_event_id or cp_end_event_id > self._event_id):
            return True

        return False


    def populate_previous_party_officer(self, officer: dict, prev_filing_party_data: dict):
        prev_officer = {}
        prev_party_type = get_party_type(prev_filing_party_data)
        prev_officer['email'] = prev_filing_party_data.get('cp_email_address', '').upper()
        prev_officer['lastName'] = prev_filing_party_data.get('cp_last_name', '').upper()
        prev_officer['firstName'] = prev_filing_party_data.get('cp_first_name', '').upper()
        prev_officer['middleName'] = prev_filing_party_data.get('cp_middle_name', '').upper()
        prev_officer['partyType'] = prev_party_type
        prev_officer['organizationName'] = prev_filing_party_data.get('cp_business_name', '').upper()
        prev_officer['identifier'] = prev_filing_party_data['cp_bus_company_num']
        officer['prev_colin_party'] = prev_officer


    def populate_party_officer(self, party_officer: dict, filing_party_data: dict):
        party_type = get_party_type(filing_party_data)
        self.populate_officer_json(party_officer, filing_party_data, party_type)
        if self.is_previous_colin_party(filing_party_data):
            self.populate_previous_party_officer_json(party_officer, filing_party_data)


    def populate_address(self, address_dict: dict, address_data_dict: dict, address_key_prefix: str):
        address_format_type_key = f'{address_key_prefix}address_format_type'
        address_format_type = address_data_dict[address_format_type_key]

        if address_format_type == AddressFormatType.BASIC:
            self.populate_basic_address(address_dict, address_data_dict, address_key_prefix)
        elif address_format_type == AddressFormatType.FOREIGN:
            self.populate_foreign_address(address_dict, address_data_dict, address_key_prefix)
        elif address_format_type == AddressFormatType.ADVANCED:
            self.populate_advanced_address(address_dict, address_data_dict, address_key_prefix)
        else:
            raise Exception('unknown address format type: ' + address_format_type)


    def populate_basic_address(self, address_dict: dict, address_data_dict: dict, address_key_prefix: str):
        postal_code_key = f'{address_key_prefix}postal_cd'
        city_key = f'{address_key_prefix}city'
        province_key = f'{address_key_prefix}province'
        country_key = f'{address_key_prefix}country_typ_cd'
        delivery_instructions_key = f'{address_key_prefix}delivery_instructions'
        street_address = get_street_address(AddressFormatType.BASIC, address_data_dict, address_key_prefix)
        street_additional = get_street_additional(AddressFormatType.BASIC, address_data_dict, address_key_prefix)

        address_dict['postalCode'] = address_data_dict[postal_code_key]
        address_dict['addressCity'] = address_data_dict[city_key]
        address_dict['addressRegion'] = address_data_dict[province_key]
        address_dict['addressCountry'] = address_data_dict[country_key]
        address_dict['streetAddress'] = street_address
        address_dict['streetAddressAdditional'] = street_additional
        address_dict['deliveryInstructions'] = address_data_dict[delivery_instructions_key]


    def populate_advanced_address(self, address_dict: dict, address_data_dict: dict, address_key_prefix: str):
        postal_code_key = f'{address_key_prefix}postal_cd'
        city_key = f'{address_key_prefix}city'
        province_key = f'{address_key_prefix}province'
        country_key = f'{address_key_prefix}country_typ_cd'
        delivery_instructions_key = f'{address_key_prefix}delivery_instructions'
        street_address = get_street_address(AddressFormatType.ADVANCED, address_data_dict, address_key_prefix)
        street_additional = get_street_additional(AddressFormatType.ADVANCED, address_data_dict, address_key_prefix)

        address_dict['postalCode'] = address_data_dict[postal_code_key]
        address_dict['addressCity'] = address_data_dict[city_key]
        address_dict['addressRegion'] = address_data_dict[province_key]
        address_dict['addressCountry'] = address_data_dict[country_key]
        address_dict['streetAddress'] = street_address
        address_dict['streetAddressAdditional'] = street_additional
        address_dict['deliveryInstructions'] = address_data_dict[delivery_instructions_key]


    def populate_foreign_address(self, address_dict: dict, address_data_dict: dict, address_key_prefix: str):
        postal_code_key = f'{address_key_prefix}postal_cd'
        city_key = f'{address_key_prefix}city'
        province_key = f'{address_key_prefix}province'
        country_key = f'{address_key_prefix}country_typ_cd'
        delivery_instructions_key = f'{address_key_prefix}delivery_instructions'
        street_address = get_street_address(AddressFormatType.FOREIGN, address_data_dict, address_key_prefix)
        street_additional = get_street_additional(AddressFormatType.FOREIGN, address_data_dict, address_key_prefix)

        address_dict['postalCode'] = address_data_dict[postal_code_key]
        address_dict['addressCity'] = address_data_dict[city_key]
        address_dict['addressRegion'] = address_data_dict[province_key]
        address_dict['addressCountry'] = address_data_dict[country_key]
        address_dict['streetAddress'] = street_address
        address_dict['streetAddressAdditional'] = street_additional
        address_dict['deliveryInstructions'] = address_data_dict[delivery_instructions_key]


    def populate_filing_business(self, filing_dict: dict):
        business_dict = filing_dict['business']
        naics_dict = business_dict['naics']
        business_dict['identifier'] = self._filing_data['c_corp_num']
        self.populate_naics(naics_dict)


    def populate_naics(self, naics_dict: dict):
        naics_dict['naicsCode'] = self._filing_data['bd_naics_code']
        naics_dict['naicsDescription'] = self._filing_data['bd_description']


    def populate_nr(self, filing_dict: dict):
        nr_dict = filing_dict['nameRequest']
        nr_dict['nrNumber'] = self._filing_data['f_nr_num']
        nr_dict['legalName'] = self._filing_data['cn_corp_name']
        nr_dict['legalType'] = self._corp_type_cd


    def populate_dissolution(self, filing_dict: dict):
        dissolution_dict = filing_dict['filing']['dissolution']
        effective_dt_str = self._filing_data['f_effective_dt_str']
        dissolution_dict['dissolutionDate'] = effective_dt_str

        if len(self._filing_data['corp_parties']) > 0:
            self.populate_parties(dissolution_dict)
        else:
            dissolution_dict['parties'] = []


