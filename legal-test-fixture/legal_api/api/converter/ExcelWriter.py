from flask import jsonify
from datetime import datetime
from legal_api.models.business import Business, Director, Address, Filing
from legal_api.api.converter.utils import format_date, format_non_date, format_boolean, format_json, SheetName
import xlwt
import logging


class ExcelWriter():

    __business_sheet = None
    __business_address_sheet = None
    __director_sheet = None
    __director_address_sheet = None
    __filing_sheet = None

    # row_num is offset by 1 because of the header row
    __business_sheet_row_index = 1
    __business_address_sheet_row_index = 1
    __director_sheet_row_index = 1
    __director_address_sheet_row_index = 1
    __filing_sheet_row_index = 1

    def convert_to_excel(self, business_list):
        book = xlwt.Workbook(encoding='ascii')

        # Add the sheets
        self.__business_sheet = book.add_sheet(SheetName.BUSINESS.value)
        self.__business_address_sheet = book.add_sheet(
            SheetName.BUSINESS_ADDRESS.value)
        self.__director_sheet = book.add_sheet(SheetName.DIRECTOR.value)
        self.__director_address_sheet = book.add_sheet(
            SheetName.DIRECTOR_ADDRESS.value)
        self.__filing_sheet = book.add_sheet(SheetName.FILING.value)

        # Write header lines
        self.__write_header_lines()

        for business in business_list:
            self.__write_business_to_excel(business)

        return book

    def __write_header_lines(self):
        business_sheet_headings = [
            'identifier',
            'legal_name',
            'legal_type',
            'founding_date',
            'dissolution_date',
            'last_ar_date',
            'last_agm_date',
            'fiscal_year_end_date',
            'tax_id',
            'last_ledger_id',
            'last_remote_ledger_id',
            'last_ledger_timestamp',
            'last_modified'
        ]
        for i, business_sheet_heading in enumerate(business_sheet_headings):
            self.__business_sheet.write(
                0, i, format_non_date(business_sheet_heading))

        business_address_sheet_headings = [
            'business',
            'address_type',
            'street',
            'street_additional',
            'city',
            'region',
            'country',
            'postal_code',
            'delivery_instructions'
        ]
        for i, business_address_sheet_heading in enumerate(business_address_sheet_headings):
            self.__business_address_sheet.write(
                0, i, format_non_date(business_address_sheet_heading))

        director_sheet_headings = [
            'business',
            'first_name',
            'middle_initial',
            'last_name',
            'title',
            'appointment_date',
            'cessation_date',
        ]
        for i, director_sheet_heading in enumerate(director_sheet_headings):
            self.__director_sheet.write(
                0, i, format_non_date(director_sheet_heading))

        director_address_sheet_headings = [
            'business',
            'first_name',
            'last_name',
            'address_type',
            'street',
            'street_additional',
            'city',
            'region',
            'country',
            'postal_code',
            'delivery_instructions'
        ]
        for i, director_address_sheet_heading in enumerate(director_address_sheet_headings):
            self.__director_address_sheet.write(
                0, i, format_non_date(director_address_sheet_heading))

        filing_sheet_headings = [
            'business',
            'filing_json',
            'completion_date',
            'filing_date',
            'filing_type',
            'effective_date',
            'payment_id',
            'payment_completion_date',
            'colin_event_id',
            'status',
            'paper_only',
        ]
        for i, filing_sheet_heading in enumerate(filing_sheet_headings):
            self.__filing_sheet.write(
                0, i, format_non_date(filing_sheet_heading))

    def __write_business_to_excel(self, business):

        self.__business_sheet.write(
            self.__business_sheet_row_index, 0, format_non_date(business.identifier))
        self.__business_sheet.write(
            self.__business_sheet_row_index, 1, format_non_date(business.legal_name))
        self.__business_sheet.write(
            self.__business_sheet_row_index, 2, format_non_date(business.legal_type))
        self.__business_sheet.write(
            self.__business_sheet_row_index, 3, format_date(business.founding_date))
        self.__business_sheet.write(
            self.__business_sheet_row_index, 4, format_date(business.dissolution_date))
        self.__business_sheet.write(
            self.__business_sheet_row_index, 5, format_date(business.last_ar_date))
        self.__business_sheet.write(
            self.__business_sheet_row_index, 6, format_date(business.last_agm_date))
        self.__business_sheet.write(
            self.__business_sheet_row_index, 7, format_date(business.fiscal_year_end_date))
        self.__business_sheet.write(
            self.__business_sheet_row_index, 8, format_non_date(business.tax_id))
        self.__business_sheet.write(
            self.__business_sheet_row_index, 9, format_non_date(business.last_ledger_id))
        self.__business_sheet.write(self.__business_sheet_row_index, 10, format_non_date(
            business.last_remote_ledger_id))
        self.__business_sheet.write(self.__business_sheet_row_index, 11, format_date(
            business.last_ledger_timestamp))
        self.__business_sheet.write(
            self.__business_sheet_row_index, 12, format_date(business.last_modified))

        self.__business_sheet_row_index += 1

        directors = business.directors.all()
        for director in directors:
            self.__write_director_to_excel(business.identifier, director)

        offices = business.offices.all()
        for office in offices:
            office_addresses = office.addresses.all()
            for office_address in office_addresses:
                self.__write_business_address_to_excel(business.identifier, office.office_type, office_address)

        filings = business.filings.all()
        for filing in filings:
            self.__write_filing_to_excel(business.identifier, filing)

    def __write_director_to_excel(self, business_identifier, director):
        self.__director_sheet.write(
            self.__director_sheet_row_index, 0, format_non_date(business_identifier))
        self.__director_sheet.write(
            self.__director_sheet_row_index, 1, format_non_date(director.first_name))
        self.__director_sheet.write(
            self.__director_sheet_row_index, 2, format_non_date(director.middle_initial))
        self.__director_sheet.write(
            self.__director_sheet_row_index, 3, format_non_date(director.last_name))
        self.__director_sheet.write(
            self.__director_sheet_row_index, 4, format_non_date(director.title))
        self.__director_sheet.write(
            self.__director_sheet_row_index, 5, format_date(director.appointment_date))
        self.__director_sheet.write(
            self.__director_sheet_row_index, 6, format_date(director.cessation_date))

        delivery_address = director.delivery_address
        if (delivery_address):
            self.__write_director_address_to_excel(
                business_identifier, director, delivery_address, self.__director_sheet_row_index)

        mailing_address = director.mailing_address
        if (mailing_address):
            self.__write_director_address_to_excel(
                business_identifier, director, mailing_address, self.__director_sheet_row_index)

        self.__director_sheet_row_index += 1

    def __write_director_address_to_excel(self, business_identifier, director, director_address, director_row_reference):
        self.__director_address_sheet.write(
            self.__director_address_sheet_row_index, 0, format_non_date(business_identifier))
        self.__director_address_sheet.write(
            self.__director_address_sheet_row_index, 1, format_non_date(director.first_name))
        self.__director_address_sheet.write(
            self.__director_address_sheet_row_index, 2, format_non_date(director.middle_initial))
        self.__director_address_sheet.write(
            self.__director_address_sheet_row_index, 3, format_non_date(director_address.address_type))
        self.__director_address_sheet.write(
            self.__director_address_sheet_row_index, 4, format_non_date(director_address.street))
        self.__director_address_sheet.write(
            self.__director_address_sheet_row_index, 5, format_non_date(director_address.street_additional))
        self.__director_address_sheet.write(
            self.__director_address_sheet_row_index, 6, format_non_date(director_address.city))
        self.__director_address_sheet.write(
            self.__director_address_sheet_row_index, 7, format_non_date(director_address.region))
        self.__director_address_sheet.write(
            self.__director_address_sheet_row_index, 8, format_non_date(director_address.country))
        self.__director_address_sheet.write(
            self.__director_address_sheet_row_index, 9, format_non_date(director_address.postal_code))
        self.__director_address_sheet.write(self.__director_address_sheet_row_index, 10, format_non_date(
            director_address.delivery_instructions))
        # Need to add the row reference so that it can be linked with a specific director (matching by name was bad)
        self.__director_address_sheet.write(self.__director_address_sheet_row_index, 11, format_non_date(
            director_row_reference))

        self.__director_address_sheet_row_index += 1

    def __write_business_address_to_excel(self, business_identifier, office_type, business_address):
        self.__business_address_sheet.write(
            self.__business_address_sheet_row_index, 0, format_non_date(business_identifier))
        self.__business_address_sheet.write(
            self.__business_address_sheet_row_index, 1, format_non_date(office_type))
        self.__business_address_sheet.write(
            self.__business_address_sheet_row_index, 2, format_non_date(business_address.address_type))
        self.__business_address_sheet.write(
            self.__business_address_sheet_row_index, 3, format_non_date(business_address.street))
        self.__business_address_sheet.write(
            self.__business_address_sheet_row_index, 4, format_non_date(business_address.street_additional))
        self.__business_address_sheet.write(
            self.__business_address_sheet_row_index, 5, format_non_date(business_address.city))
        self.__business_address_sheet.write(
            self.__business_address_sheet_row_index, 6, format_non_date(business_address.region))
        self.__business_address_sheet.write(
            self.__business_address_sheet_row_index, 7, format_non_date(business_address.country))
        self.__business_address_sheet.write(
            self.__business_address_sheet_row_index, 8, format_non_date(business_address.postal_code))
        self.__business_address_sheet.write(self.__business_address_sheet_row_index, 9, format_non_date(
            business_address.delivery_instructions))

        self.__business_address_sheet_row_index += 1

    def __write_filing_to_excel(self, business_identifier, filing):
        self.__filing_sheet.write(
            self.__filing_sheet_row_index, 0, format_non_date(business_identifier))

        self.__filing_sheet.write(
            self.__filing_sheet_row_index, 1, format_json(filing._filing_json))
        self.__filing_sheet.write(
            self.__filing_sheet_row_index, 2, format_date(filing._completion_date))
        self.__filing_sheet.write(
            self.__filing_sheet_row_index, 3, format_date(filing._filing_date))
        self.__filing_sheet.write(
            self.__filing_sheet_row_index, 4, format_non_date(filing._filing_type))
        self.__filing_sheet.write(
            self.__filing_sheet_row_index, 5, format_date(filing.effective_date))
        self.__filing_sheet.write(
            self.__filing_sheet_row_index, 6, format_non_date(filing._payment_token))

        self.__filing_sheet.write(self.__filing_sheet_row_index, 7, format_date(
            filing._payment_completion_date))
        self.__filing_sheet.write(
            self.__filing_sheet_row_index, 8, format_non_date(filing.colin_event_id))
        self.__filing_sheet.write(
            self.__filing_sheet_row_index, 9, format_non_date(filing.status))
        self.__filing_sheet.write(
            self.__filing_sheet_row_index, 10, format_boolean(filing.paper_only))

        self.__filing_sheet_row_index += 1
