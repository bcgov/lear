# pylint: disable=invalid-name
"""ExcelConverter - convert spreadsheet to objects."""
import xlrd
from flask import json
from legal_api import db
from legal_api.models.business import Address, Business, Director, Filing
from legal_api.models.colin_event_id import ColinEventId
from legal_api.models.office import Office, OfficeType
from sqlalchemy_continuum import versioning_manager

from data_reset_tool.converter.utils import SheetName


class ExcelConverter:
    """ExcelConverter - convert spreadsheet to objects."""

    def create_businesses_from_file(self, a_file, input_business_identifier, rebuild):
        """Create a business and sub-objects (filings, addresses, etc.) from spreadsheet."""
        book = xlrd.open_workbook(file_contents=a_file.stream.read())

        # Start to process the sheet with the businesses
        business_sheet = book.sheet_by_name(SheetName.BUSINESS.value)
        business_list = []

        business_rows = list(business_sheet.get_rows())
        iterrows = iter(business_rows)

        # (skipping the header line)
        next(iterrows)

        for row in iterrows:
            row_business_identifier = self.__get_business_identifier(row)

            # If business_identifier is provided then only process this row if the BI matches
            if input_business_identifier and not input_business_identifier == row_business_identifier:
                continue

            # If we are rebuilding, everything is already dropped. otherwise delete this single business
            if not rebuild:
                # If this business is already in the database, delete it
                self.__delete_business(row_business_identifier)

            business = self.__create_business_from_row(row, book)
            business_list.append(business)
        return business_list

    def delete_business(self, input_business_identifier):
        """Delete a business and all sub-items from db."""
        self.__delete_business(input_business_identifier)
        db.session.commit()

    def __get_business_identifier(self, row):
        return self.__get_value_from_row(row, 0)

    @classmethod
    def __delete_business(cls, identifier):
        existing_business = Business.find_by_identifier(identifier)
        if existing_business:
            for f in existing_business.filings.all():
                f._payment_token = None  # pylint: disable=protected-access

                for colin_event_id in f.colin_event_ids:
                    db.session.delete(colin_event_id)

                f.save()
                db.session.delete(f)

            for mailing_address in existing_business.mailing_address.all():
                db.session.delete(mailing_address)
            for delivery_address in existing_business.delivery_address.all():
                db.session.delete(delivery_address)
            for office in existing_business.offices.all():
                db.session.delete(office)

            db.session.delete(existing_business)

    def __create_business_from_row(self, row, book):
        # Get the business properties and create the business
        business = Business(identifier=self.__get_value_from_row(row, 0),
                            legal_name=self.__get_value_from_row(row, 1),
                            legal_type=self.__get_value_from_row(row, 2),
                            founding_date=self.__get_value_from_row(row, 3),
                            dissolution_date=self.__get_value_from_row(row, 4),
                            last_ar_date=self.__get_value_from_row(row, 5),
                            last_agm_date=self.__get_value_from_row(row, 6),
                            fiscal_year_end_date=self.__get_value_from_row(
                                row, 7),
                            tax_id=self.__get_value_from_row(row, 8),
                            last_ledger_id=self.__get_value_from_row(row, 9),
                            last_remote_ledger_id=self.__get_value_from_row(
                                row, 10),
                            last_ledger_timestamp=self.__get_value_from_row(
                                row, 11),
                            last_modified=self.__get_value_from_row(row, 12)
                            )
        business.save()
        self.__add_directors(business, book)
        self.__add_business_addresses(business, book)
        self.__add_filings(business, book)
        db.session.commit()
        return business

    def __add_directors(self, business, book):
        # Get the director properties and create the directors
        director_sheet = book.sheet_by_name(SheetName.DIRECTOR.value)
        iter_director_rows = iter(director_sheet.get_rows())
        # (skipping the header line)
        next(iter_director_rows)
        for director_row in iter_director_rows:
            if director_row[0].value == business.identifier:
                director = Director(
                    business_id=business.id,
                    first_name=self.__get_value_from_row(director_row, 1),
                    middle_initial=self.__get_value_from_row(director_row, 2),
                    last_name=self.__get_value_from_row(director_row, 3),
                    title=self.__get_value_from_row(director_row, 4),
                    appointment_date=self.__get_value_from_row(
                        director_row, 5),
                    cessation_date=self.__get_value_from_row(director_row, 6)
                )
                self.__add_director_addresses(
                    business.identifier, director, book)

                business.directors.append(director)
                db.session.add(director)
                director.save()

    def __add_director_addresses(self, business_identifier, director, book):
        # Find Mailing and Delivery Addresses
        director_address_sheet = book.sheet_by_name(
            SheetName.DIRECTOR_ADDRESS.value)
        iter_director_address_rows = iter(director_address_sheet.get_rows())
        # (skipping the header line)
        next(iter_director_address_rows)
        for director_address_row in iter_director_address_rows:
            da_business_identifier = self.__get_value_from_row(
                director_address_row, 0)
            da_first_name = self.__get_value_from_row(director_address_row, 1)
            da_last_name = self.__get_value_from_row(director_address_row, 2)
            if da_business_identifier == business_identifier and da_first_name == director.first_name \
                    and da_last_name == director.last_name:
                address = Address(
                    address_type=self.__get_value_from_row(
                        director_address_row, 3),
                    street=self.__get_value_from_row(director_address_row, 4),
                    street_additional=self.__get_value_from_row(
                        director_address_row, 5),
                    city=self.__get_value_from_row(director_address_row, 6),
                    region=self.__get_value_from_row(director_address_row, 7),
                    country=self.__get_value_from_row(director_address_row, 8),
                    postal_code=self.__get_value_from_row(
                        director_address_row, 9),
                    delivery_instructions=self.__get_value_from_row(
                        director_address_row, 10)
                )
                address.save()
                if address.address_type == Address.MAILING:
                    director.mailing_address = address
                    director.mailing_address_id = address.id
                elif address.address_type == Address.DELIVERY:
                    director.delivery_address = address
                    director.delivery_address_id = address.id

            # If the mailing anddress and the delivery address are both found, no need to continue
            if director.mailing_address_id and director.delivery_address_id:
                break

    def __add_business_addresses(self, business, book):
        registered_office_type_id = OfficeType.REGISTERED
        records_office_type_id = OfficeType.RECORDS

        # Get the business address properties and create the business addresses
        business_address_sheet = book.sheet_by_name(
            SheetName.BUSINESS_ADDRESS.value)
        iter_business_address_rows = iter(business_address_sheet.get_rows())
        # (skipping the header line)
        next(iter_business_address_rows)
        registered_office = None
        records_office = None
        for business_address_row in iter_business_address_rows:
            business_offices = business.offices.all()

            if business_address_row[0].value == business.identifier:
                office_type = self.__get_value_from_row(business_address_row, 1)
                office = None

                # Create the appropriate office if it does not exist
                if (office_type == OfficeType.REGISTERED) and not registered_office:
                    # Create registered office
                    registered_office = Office(
                        business_id=business.id,
                        office_type=registered_office_type_id
                    )
                    db.session.add(registered_office)
                    business_offices.append(registered_office)
                elif (office_type == OfficeType.RECORDS) and not records_office:
                    # Create records office
                    records_office = Office(
                        business_id=business.id,
                        office_type=records_office_type_id
                    )
                    db.session.add(records_office)
                    business_offices.append(records_office)

                # Set the office to use to save the address
                if office_type == OfficeType.REGISTERED:
                    office = registered_office
                elif office_type == OfficeType.RECORDS:
                    office = records_office

                address = Address(
                    address_type=self.__get_value_from_row(business_address_row, 2),
                    street=self.__get_value_from_row(business_address_row, 3),
                    street_additional=self.__get_value_from_row(business_address_row, 4),
                    city=self.__get_value_from_row(business_address_row, 5),
                    region=self.__get_value_from_row(business_address_row, 6),
                    country=self.__get_value_from_row(business_address_row, 7),
                    postal_code=self.__get_value_from_row(business_address_row, 8),
                    # delivery_instructions=self.__get_value_from_row(business_address_row, 9),
                    office_id=office.id,
                    business_id=business.id
                )
                db.session.add(address)
                office.addresses.append(address)
            db.session.commit()

    def __add_filings(self, business, book):
        # Get the filings properties and create the filings
        filings_sheet = book.sheet_by_name(SheetName.FILING.value)
        iter_filings_rows = iter(filings_sheet.get_rows())
        # (skipping the header line)
        next(iter_filings_rows)
        for filing_row in iter_filings_rows:
            transaction_id = None
            if filing_row[0].value == business.identifier:

                # If the filing is completed, it has to contain a transaction ID
                status = self.__get_value_from_row(filing_row, 9)
                if Filing.Status.COMPLETED.value == status:
                    uow = versioning_manager.unit_of_work(db.session)
                    transaction = uow.create_transaction(db.session)
                    transaction_id = transaction.id

                filing = Filing(
                    _completion_date=self.__get_value_from_row(filing_row, 2),
                    _filing_date=self.__get_value_from_row(filing_row, 3),
                    _filing_type=self.__get_value_from_row(filing_row, 4),
                    effective_date=self.__get_value_from_row(filing_row, 5),
                    _payment_token=self.__get_value_from_row(filing_row, 6),
                    _payment_completion_date=self.__get_value_from_row(
                        filing_row, 7),
                    _status=status,
                    paper_only=self.__get_value_from_row(filing_row, 10),
                    # transaction_id comes from continuuum
                    transaction_id=transaction_id
                )
                filing.business_id = business.id

                # need to convert this first before storing
                filing_value = self.__get_value_from_row(filing_row, 1)
                if filing_value:
                    filing._filing_json = json.loads(filing_value)  # pylint: disable=protected-access

                business.filings.append(filing)
                db.session.add(filing)
                db.session.commit()

                # add colin event ids
                colin_event_ids = self.__get_value_from_row(filing_row, 8)

                if colin_event_ids:
                    # convert string to list
                    colin_event_ids = eval(colin_event_ids)

                    for colin_event_id in colin_event_ids:
                        colin_event_id_obj = ColinEventId(
                            colin_event_id=colin_event_id,
                            filing_id=filing.id
                        )
                        filing.colin_event_ids.append(colin_event_id_obj)
                        db.session.add(filing)

                    db.session.commit()

    @classmethod
    def __get_value_from_row(cls, row, index):
        return row[index].value if row[index].value else None
