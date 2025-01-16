from flows.common.filing_base_json import get_base_dissolution_filing_json, get_base_put_back_on_filing_json, \
    get_base_continuation_in_filing_json, get_base_correction_filing_json, get_base_ia_filing_json, \
    get_base_share_series_json, get_base_ar_filing_json
from .event_filing_service import OtherEventFilings
from .filing_data_utils import get_certified_by, get_party_role_type, get_party_type, \
    get_street_address, get_street_additional, AddressFormatType, get_effective_date_str, \
    get_alias_type, get_effective_date, get_effective_date_iso_format


class FilingJsonFactoryService:

    def __init__(self, event_filing_data: dict):
        self._event_filing_data = event_filing_data
        self._filing_data = event_filing_data['data']
        self._event_filing_type = event_filing_data['data']['event_file_type']
        self._target_lear_filing_type = self._filing_data['target_lear_filing_type']

        # dissolution filing only needs FCP as party.  remove existing parties when constructing filing json
        if self._target_lear_filing_type == 'dissolution':
            filing_data_parties = self._filing_data['corp_parties']
            filing_data_completing_party = next((filing_data_party
                                    for filing_data_party in filing_data_parties
                                    if filing_data_party and filing_data_party['cp_party_typ_cd'] == 'FCP'), None)
            self._completing_party = None
            if filing_data_completing_party:
                self._completing_party = filing_data_completing_party

        self._event_id = self._filing_data['e_event_id']
        self._prev_event_id = self._filing_data.get('prev_event_filing_data', {}).get('e_event_id', None)
        self._corp_type_cd = self._filing_data['c_corp_type_cd']


    def get_filing_json(self):
        filing_json = None

        if self._target_lear_filing_type == 'incorporationApplication':
            filing_json = self.get_ia_filing_json()
        elif self._target_lear_filing_type == 'annualReport':
            filing_json = self.get_ar_filing_json()
        elif self._target_lear_filing_type == 'continuationIn':
            filing_json = self.get_continuation_in_filing_json()
        elif self._target_lear_filing_type == 'correction':
            filing_json = self.get_correction_filing_json()
        elif self._target_lear_filing_type == 'dissolution':
            filing_json = self.get_voluntary_dissolution_filing_json()
        elif self._target_lear_filing_type == 'putBackOn':
            filing_json = self.get_put_back_on_filing_json()

        return filing_json


    def get_ia_filing_json(self):
        result = self.build_ia_filing()
        return result


    def build_ia_filing(self):
        num_parties = len(self._filing_data['corp_parties'])
        num_corp_names = len(self._filing_data['corp_names'])
        num_share_classes = len(self._filing_data['share_structure']['share_classes'])
        filing_root_dict = get_base_ia_filing_json(num_parties, num_corp_names, num_share_classes)

        self.populate_header(filing_root_dict)
        self.populate_business(filing_root_dict)
        self.populate_ia(filing_root_dict)
        return filing_root_dict


    def get_ar_filing_json(self):
        result = self.build_ar_filing()
        return result


    def build_ar_filing(self):
        directors = [p for p in self._filing_data['corp_parties'] if p['cp_party_typ_cd'] == 'DIR']
        num_directors = len(directors)
        filing_root_dict = get_base_ar_filing_json(num_directors)

        self.populate_header(filing_root_dict)
        self.populate_business(filing_root_dict)
        self.populate_ar(filing_root_dict)
        return filing_root_dict


    def get_continuation_in_filing_json(self):
        result = self.build_continuation_in_filing()
        return result


    def build_continuation_in_filing(self):
        num_parties = len(self._filing_data['corp_parties'])
        num_corp_names = len(self._filing_data['corp_names'])
        num_share_classes = len(self._filing_data['share_structure']['share_classes'])
        filing_root_dict = get_base_continuation_in_filing_json(num_parties, num_corp_names, num_share_classes)

        self.populate_header(filing_root_dict)
        self.populate_business(filing_root_dict)
        self.populate_continuation_in(filing_root_dict)
        return filing_root_dict


    def get_correction_filing_json(self):
        result = self.build_correction_filing()
        return result


    def build_correction_filing(self):
        num_parties = len(self._filing_data['corp_parties'])
        filing_root_dict = get_base_correction_filing_json(num_parties)

        self.populate_header(filing_root_dict)
        self.populate_business(filing_root_dict)
        self.populate_correction(filing_root_dict)
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


    def get_put_back_on_filing_json(self):
        result = self.build_put_back_on_filing()
        return result


    def build_put_back_on_filing(self):
        filing_root_dict = get_base_put_back_on_filing_json()

        self.populate_header(filing_root_dict)
        self.populate_business(filing_root_dict)
        self.populate_put_back_on(filing_root_dict)
        return filing_root_dict


    def populate_header(self, filing_root_dict: dict):
        header = filing_root_dict['filing']['header']
        effective_dt_str = get_effective_date_str(self._filing_data)
        header['date'] = effective_dt_str

        if OtherEventFilings.FILE_ANNBC == self._event_filing_type:
            header['effectiveDate'] = get_effective_date_iso_format(self._filing_data)

        certified_by = get_certified_by(self._filing_data)
        header['certifiedBy'] = certified_by


    def populate_business(self, filing_root_dict: dict):
        business_dict = filing_root_dict['filing']['business']
        business_dict['legalType'] = self._filing_data['c_corp_type_cd']
        business_dict['identifier'] = self._filing_data['c_corp_num']
        business_dict['foundingDate'] = str(self._filing_data['c_recognition_dts_pacific'])


    def populate_ia(self, filing_root_dict: dict):
        ia_dict = filing_root_dict['filing']['incorporationApplication']
        ia_dict['businessType'] = self._filing_data['c_corp_type_cd']

        self.populate_offices(ia_dict)
        self.populate_parties(ia_dict['parties'])
        self.populate_name_translations(ia_dict)
        self.populate_nr(ia_dict)
        if len(ia_dict['shareStructure']['shareClasses']) > 0:
            self.populate_share_structure(ia_dict)
        else:
            del ia_dict['shareStructure']

        if self._filing_data['c_admin_email']:
            self.populate_contact_point(ia_dict)
        else:
            del ia_dict['contactPoint']


    def populate_ar(self, filing_root_dict: dict):
        ar_dict = filing_root_dict['filing']['annualReport']

        self.populate_offices(ar_dict)
        self.populate_directors(ar_dict['directors'])
        ar_dict['nextARDate'] = self._filing_data['f_period_end_dt_str']
        ar_dict['annualReportDate'] = self._filing_data['f_period_end_dt_str']


    def populate_continuation_in(self, filing_root_dict: dict):
        continuation_in_dict = filing_root_dict['filing']['continuationIn']
        continuation_in_dict['businessType'] = self._filing_data['c_corp_type_cd']

        self.populate_offices(continuation_in_dict)
        self.populate_parties(continuation_in_dict['parties'])
        self.populate_name_translations(continuation_in_dict)
        self.populate_nr(continuation_in_dict)

        if len(continuation_in_dict['shareStructure']['shareClasses']) > 0:
            self.populate_share_structure(continuation_in_dict)
        else:
            del continuation_in_dict['shareStructure']

        if self._filing_data['c_admin_email']:
            self.populate_contact_point(continuation_in_dict)
        else:
            del continuation_in_dict['contactPoint']
        
        if filing_data_jurisdiction := self._filing_data['jurisdiction']:
            continuation_in_dict['business']['foundingDate'] = filing_data_jurisdiction['j_home_recogn_dt']
            continuation_in_dict['business']['identifier'] = filing_data_jurisdiction['j_home_juris_num']
            continuation_in_dict['business']['legalName'] = filing_data_jurisdiction['j_home_company_nme']
            self.populate_foreign_jurisdiction(filing_data_jurisdiction, continuation_in_dict)
        else:
            del continuation_in_dict['business']  # expro data in BC
            del continuation_in_dict['foreignJurisdiction']


    def populate_correction(self, filing_dict: dict):
        correction_dict = filing_dict['filing']['correction']
        correction_dict['type'] = 'STAFF'
        correction_dict['startDate'] = self._filing_data.get('bd_business_start_date_dt_str', None)
        correction_dict['comment'] = self._filing_data.get('lt_notation', None)
        corrected_event_filing_info = self._filing_data['corrected_event_filing_info']
        correction_dict['corrected_filing_event_id'] = str(corrected_event_filing_info['correctedEventId'])
        correction_dict['correctedFilingType'] = corrected_event_filing_info['learFilingType']

        if self._filing_data.get('bd_start_event_id', None):
            self.populate_filing_business(correction_dict)
        else:
            del correction_dict['business']

        if len(self._filing_data['offices']) > 0:
            self.populate_offices(correction_dict)
        else:
            del correction_dict['offices']

        if len(self._filing_data['corp_parties']) > 0:
            self.populate_parties(correction_dict['parties'])
        else:
            del correction_dict['parties']

        if self._filing_data.get('cn_start_event_id') and self._filing_data.get('cn_corp_name'):
            self.populate_nr(correction_dict)
        else:
            del correction_dict['nameRequest']

        if self._filing_data['c_admin_email']:
            self.populate_contact_point(correction_dict)
        else:
            del correction_dict['contactPoint']


    def populate_offices(self, offices_dict: dict):
        registered_office_json = offices_dict['offices']['registeredOffice']
        records_office_json = offices_dict['offices']['recordsOffice']

        if len(self._filing_data['offices']) == 0:
            del offices_dict['offices']
            return

        registered_office_filing_data = \
            next((o for o in self._filing_data['offices'] if o.get('o_office_typ_cd', '') == 'RG'), None)
        records_office_filing_data = \
            next((o for o in self._filing_data['offices'] if o.get('o_office_typ_cd', '') == 'RC'), None)

        if registered_office_filing_data:
            self.populate_office(registered_office_json, registered_office_filing_data)
        else:
            del registered_office_json

        if records_office_filing_data:
            self.populate_office(records_office_json, records_office_filing_data)
        else:
            del records_office_json


    def populate_office(self, office_json: dict, filing_data_office: dict):

        mailing_addr_id = filing_data_office['ma_addr_id']
        if mailing_addr_id:
            mailing_addr = office_json['mailingAddress']
            self.populate_address(mailing_addr, filing_data_office, 'ma_')
        else:
            del office_json['mailingAddress']

        delivery_addr_id = filing_data_office['da_addr_id']
        if delivery_addr_id:
            delivery_addr = office_json['deliveryAddress']
            self.populate_address(delivery_addr, filing_data_office, 'da_')
        else:
            del office_json['deliveryAddress']


    def populate_parties(self, parties_dict: dict):

        for idx, party in enumerate(parties_dict):
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


    def populate_directors(self, directors_dict: dict):

        for idx, party in enumerate(directors_dict):
            filing_data_party = self._filing_data['corp_parties'][idx]
            self.populate_director(party, filing_data_party)

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


    def populate_name_translations(self, filings_dict: dict):
        corp_names = filings_dict['nameTranslations']

        for idx, corp_name in enumerate(corp_names):
            filing_data_corp_name = self._filing_data['corp_names'][idx]
            corp_name['name'] = filing_data_corp_name['cn_corp_name']
            corp_name_typ_cd = filing_data_corp_name['cn_corp_name_typ_cd']
            alias_type = get_alias_type(corp_name_typ_cd)
            corp_name['type'] = alias_type


    def populate_completing_party(self, filings_dict: dict):
        party = filings_dict['parties'][0]

        filing_data_party = self._completing_party
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


    def populate_director(self, director_dict: dict, filing_party_data: dict):
        party_officer_dict = director_dict['officer']
        self.populate_director_officer(party_officer_dict, filing_party_data)
        director_dict['appointmentDate'] = filing_party_data['cp_appointment_dt']


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
            officer['lastName'] = filing_party_data.get('cp_last_name', '').upper()
            officer['firstName'] = filing_party_data.get('cp_first_name', '').upper()
            officer['middleName'] = filing_party_data.get('cp_middle_name', '').upper()
            officer['partyType'] = party_type
            officer['organizationName'] = filing_party_data.get('cp_business_name', '').upper()
            officer['identifier'] = filing_party_data['cp_bus_company_num']
        else:
            officer['lastName'] = filing_party_data.get('cp_last_name', '')
            officer['firstName'] = filing_party_data.get('cp_first_name', '')
            officer['middleName'] = filing_party_data.get('cp_middle_name', '')
            officer['partyType'] = party_type
            officer['organizationName'] = filing_party_data.get('cp_business_name', '')
            officer['identifier'] = filing_party_data['cp_bus_company_num']


    def populate_director_officer_json(self, officer: dict, filing_party_data: dict, party_type: str, to_upper=False):
        if to_upper:
            officer['lastName'] = filing_party_data.get('cp_last_name', '').upper()
            officer['firstName'] = filing_party_data.get('cp_first_name', '').upper()
            officer['middleInitial'] = filing_party_data.get('cp_middle_name', '').upper()
            officer['prevLastName'] = filing_party_data.get('cp_last_name', '').upper()
            officer['prevFirstName'] = filing_party_data.get('cp_first_name', '').upper()
            officer['prevMiddleInitial'] = filing_party_data.get('cp_middle_name', '').upper()
            officer['partyType'] = party_type
            officer['organizationName'] = filing_party_data.get('cp_business_name', '').upper()
            officer['identifier'] = filing_party_data['cp_bus_company_num']
        else:
            officer['lastName'] = filing_party_data.get('cp_last_name', '')
            officer['firstName'] = filing_party_data.get('cp_first_name', '')
            officer['middleInitial'] = filing_party_data.get('cp_middle_name', '')
            officer['prevLastName'] = filing_party_data.get('cp_last_name', '')
            officer['prevFirstName'] = filing_party_data.get('cp_first_name', '')
            officer['prevMiddleInitial'] = filing_party_data.get('cp_middle_name', '')
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
        prev_officer['lastName'] = prev_filing_party_data.get('cp_last_name', '').upper()
        prev_officer['firstName'] = prev_filing_party_data.get('cp_first_name', '').upper()
        prev_officer['middleName'] = prev_filing_party_data.get('cp_middle_name', '').upper()
        prev_officer['partyType'] = prev_party_type
        prev_officer['organizationName'] = prev_filing_party_data.get('cp_business_name', '').upper()
        if cp_bus_company_num := prev_filing_party_data.get('cp_bus_company_num'):
            prev_officer['identifier'] = cp_bus_company_num.upper()
        else:
            prev_officer['identifier'] = cp_bus_company_num
        prev_officer['appointmentDate'] = prev_filing_party_data['cp_appointment_dt']
        officer['prev_colin_party'] = prev_officer


    def populate_party_officer(self, party_officer: dict, filing_party_data: dict):
        party_type = get_party_type(filing_party_data)
        self.populate_officer_json(party_officer, filing_party_data, party_type)
        if self.is_previous_colin_party(filing_party_data):
            self.populate_previous_party_officer_json(party_officer, filing_party_data)


    def populate_director_officer(self, party_officer: dict, filing_party_data: dict):
        party_type = get_party_type(filing_party_data)
        self.populate_director_officer_json(party_officer, filing_party_data, party_type)
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
        business_dict['taxId'] = self._filing_data['c_bn']
        self.populate_naics(naics_dict)


    def populate_naics(self, naics_dict: dict):
        naics_dict['naicsCode'] = self._filing_data['bd_naics_code']
        naics_dict['naicsDescription'] = self._filing_data['bd_description']


    def populate_nr(self, filing_dict: dict):
        nr_dict = filing_dict['nameRequest']
        nr_dict['nrNumber'] = self._filing_data['f_nr_num']
        nr_dict['legalName'] = self._filing_data['cn_corp_name']
        nr_dict['legalType'] = self._corp_type_cd


    def populate_court_order(self, filing_dict: dict):
        court_order_dict = filing_dict['courtOrder']
        court_order_dict['orderDetails'] = self._filing_data['lt_notation']


    def populate_dissolution(self, filing_dict: dict):
        dissolution_dict = filing_dict['filing']['dissolution']
        trigger_dt_str = self._filing_data['e_trigger_dt_str']
        dissolution_dict['dissolutionDate'] = trigger_dt_str

        if self._completing_party:
            self.populate_completing_party(dissolution_dict)
        else:
            dissolution_dict['parties'] = []


    def populate_put_back_on(self, filing_dict: dict):
        pbo_dict = filing_dict['filing']['putBackOn']
        pbo_dict['details'] = self._filing_data['lt_notation']


    def populate_contact_point(self, filing_dict: dict):
        contact_point_dict = filing_dict['contactPoint']
        contact_point_dict['email'] = self._filing_data['c_admin_email']


    def populate_share_structure(self, filings_dict: dict):
        share_classes = filings_dict['shareStructure']['shareClasses']

        for idx, share_class in enumerate(share_classes):
            filing_data_share_class = self._filing_data['share_structure']['share_classes'][idx]
            self.populate_share_class(share_class, filing_data_share_class)


    def populate_share_class(self, share_class_dict: dict, filing_share_class_dict: dict):
        share_class_dict['name'] = filing_share_class_dict['ssc_class_nme']
        share_class_dict['currency'] = filing_share_class_dict['ssc_currency_typ_cd']
        share_class_dict['otherCurrency'] = filing_share_class_dict['ssc_other_currency']
        share_class_dict['hasParValue'] = filing_share_class_dict['ssc_par_value_ind']
        par_value = filing_share_class_dict['ssc_par_value_amt']
        share_class_dict['parValue'] = float(par_value) if par_value else None
        share_class_dict['hasMaximumShares'] = filing_share_class_dict['ssc_max_share_ind']
        share_class_dict['hasSpecialRights'] = filing_share_class_dict['ssc_spec_rights_ind']

        share_quantity = filing_share_class_dict['ssc_share_quantity']
        share_class_dict['maxNumberOfShares'] = int(share_quantity) if share_quantity else None
        self.populate_share_series(share_class_dict, filing_share_class_dict)


    def populate_share_series(self, share_class_dict: dict, filing_share_class_dict: dict):
        if not(filing_data_share_series := filing_share_class_dict['share_series']):
            return

        for series_data_dict in filing_data_share_series:
            series_dict = get_base_share_series_json()
            series_dict['name'] = series_data_dict['srs_series_nme']
            series_dict['hasMaximumShares'] = series_data_dict['srs_max_share_ind']

            share_quantity = series_data_dict['srs_share_quantity']
            series_dict['maxNumberOfShares'] = int(share_quantity) if share_quantity else None

            series_dict['hasSpecialRights'] = series_data_dict['srs_spec_right_ind']
            share_class_dict['series'].append(series_dict)


    def populate_foreign_jurisdiction(self, filing_data_jurisdiction: dict, filing_dict: dict):
        jurisdiction_dict = filing_dict['foreignJurisdiction']

        jurisdiction_dict['legalName'] = filing_data_jurisdiction['j_home_company_nme']
        jurisdiction_dict['identifier'] = filing_data_jurisdiction['j_home_juris_num']
        jurisdiction_dict['incorporationDate'] = filing_data_jurisdiction['j_home_recogn_dt']
        jurisdiction_dict['country'] = None
        jurisdiction_dict['region'] = None

        can_jurisdiction_code = filing_data_jurisdiction['j_can_jur_typ_cd']
        other_jurisdiction_desc = filing_data_jurisdiction['j_othr_juris_desc']

        # when canadian jurisdiction, ignore othr_juris_desc
        if can_jurisdiction_code != 'OT':
            jurisdiction_dict['country'] = 'CA'
            jurisdiction_dict['region'] = 'FEDERAL' if can_jurisdiction_code == 'FD' else can_jurisdiction_code
        # when other jurisdiction and len(othr_juris_desc) = 2, then othr_juris_desc is country code
        elif can_jurisdiction_code == 'OT' and len(other_jurisdiction_desc) == 2:
            jurisdiction_dict['country'] = other_jurisdiction_desc
        # when other jurisdiction and len(othr_juris_desc) = 6, then othr_juris_desc contains both
        # region code and country code (like "US, SS"). Ignore any other cases.
        elif can_jurisdiction_code == 'OT' and len(other_jurisdiction_desc) == 6:
            jurisdiction_dict['country'] = other_jurisdiction_desc[:2]
            jurisdiction_dict['region'] = other_jurisdiction_desc[4:]
