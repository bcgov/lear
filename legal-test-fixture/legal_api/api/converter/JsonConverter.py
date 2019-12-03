from flask import json, jsonify
from legal_api.models.business import Business, Director, Address
from legal_api.models.office import Office, OfficeType
import logging
from legal_api.api.converter.utils import format_date, format_non_date, format_boolean, format_json


class JsonConverter():

    def convert_to_json(self, business_list):
        json_list = []

        # convert each business to JSON
        for business in business_list:
            json_list.append(self.__json_business(business))

        # return a single JSON object
        return jsonify({'businesses': json_list})

    def __json_business(self, business):

        offices = business.offices.all()
        registeredOffice = self.__create_office_addresses(offices, OfficeType.REGISTERED)
        recordsOffice = self.__create_office_addresses(offices, OfficeType.RECORDS)

        d = {
            'identifier': format_non_date(business.identifier),
            'legalName': format_non_date(business.legal_name),
            'legalType': format_non_date(business.legal_type),
            'foundingDate': format_date(business.founding_date),
            'dissolutionDate': format_date(business.dissolution_date),
            'lastAnnualReport': format_date(business.last_ar_date),
            'lastAnnualGeneralMeetingDate': format_date(business.last_agm_date),
            'fiscalYearEndDate': format_date(business.fiscal_year_end_date),
            'taxId': format_non_date(business.tax_id),
            'lastLedgerId': format_non_date(business.last_ledger_id),
            'lastRemoteLedgerId': format_non_date(business.last_remote_ledger_id),
            'lastLedgerTimestamp': format_date(business.last_ledger_timestamp),
            'submitterUserId': format_non_date(business.submitter_userid),
            'lastModified': format_date(business.last_modified),
            'directors': self.__json_directors(business.directors),
            'registeredOffice': registeredOffice,
            OfficeType.REGISTERED: format_non_date(registeredOffice),
            OfficeType.RECORDS: format_non_date(recordsOffice),
            'filings': self.__json_filings(business.filings)
        }

        return d

    def __json_directors(self, directors):
        directors_json_list = []

        for director in directors:
            d = {
                'firstName': format_non_date(director.first_name),
                'middleInitial': format_non_date(director.middle_initial),
                'lastName': format_non_date(director.last_name),
                'title': format_non_date(director.title),
                'appointmentDate': format_date(director.appointment_date),
                'cessationDate': format_date(director.cessation_date),
                'deliveryAddress': self.__format_address(director.delivery_address),
                'mailingAddress': self.__format_address(director.mailing_address)
            }
            directors_json_list.append(d)

        return directors_json_list

    def __format_address(self, value):
        return_value = None
        if value:
            return_value = {
                'addressType': format_non_date(value.address_type),
                'street': format_non_date(value.street),
                'streetAdditional': format_non_date(value.street_additional),
                'city': format_non_date(value.city),
                'region': format_non_date(value.region),
                'country': format_non_date(value.country),
                'postalCode': format_non_date(value.postal_code)
            }
        return return_value

    def __json_filings(self, filings):
        filings_json_list = []

        for filing in filings:
            d = {
                'completionDate': format_date(filing._completion_date),
                'filingDate': format_date(filing._filing_date),
                'filingType': format_non_date(filing._filing_type),
                'effectiveDate': format_date(filing.effective_date),
                'paymentToken': format_non_date(filing._payment_token),
                'paymentCompletionDate': format_date(filing._payment_completion_date),
                'colinEventId': format_non_date(filing.colin_event_id),
                'status': format_non_date(filing._status),
                'paperOnly': format_boolean(filing.paper_only),
                # Don't want to use format_json here because we're
                # running jsonify later and it will get all escaped
                'filingJson': format_non_date(filing._filing_json)
            }
            filings_json_list.append(d)

        return filings_json_list

    def __create_office_addresses(self, offices, office_type):
        office_addresses = None
        for office in offices:
            if office_type == office.office_type:
                mailing_address = None
                delivery_address = None

                office_addresses = office.addresses.all()
                for office_address in office_addresses:
                    if office_address.address_type == Address.MAILING:
                        mailing_address = office_address
                    elif office_address.address_type == Address.DELIVERY:
                        delivery_address = office_address
                office_addresses = {
                    'mailingAddress': self.__format_address(mailing_address),
                    'deliveryAddress': self.__format_address(delivery_address)
                }
        return office_addresses

