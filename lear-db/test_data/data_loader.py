# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Loads the businesses from the COLIN_API, as provided in a csv file."""
import copy
import csv
import datetime
import os
from http import HTTPStatus

import pycountry
import requests
from dotenv import find_dotenv, load_dotenv
from flask import Flask
from legal_api import db
from legal_api.config import get_named_config
from legal_api.models import Address, Business, Filing, Office, Party, PartyRole, User
from legal_api.models.colin_event_id import ColinEventId
from sqlalchemy_continuum import versioning_manager

load_dotenv(find_dotenv())

FLASK_APP = Flask(__name__)
FLASK_APP.config.from_object(get_named_config('production'))
db.init_app(FLASK_APP)

COLIN_API = os.getenv('COLIN_API', None)
UPDATER_USERNAME = os.getenv('UPDATER_USERNAME')

ROWCOUNT = 0
TIMEOUT = 15
FAILED_CORPS = []
NEW_CORPS = []
LOADED_FILING_HISTORY = []
FAILED_FILING_HISTORY = []


def create_business(business_json: dict) -> Business:
    """Create a new business in lear via the model."""
    business = Business()
    business.identifier = business_json['business']['identifier']
    business.founding_date = business_json['business']['foundingDate']
    business.last_ledger_timestamp = business_json['business']['lastLedgerTimestamp']
    business.legal_name = business_json['business']['legalName']
    business.founding_date = business_json['business']['foundingDate']
    business.last_agm_date = datetime.date.fromisoformat(business_json['business']['lastAgmDate']) \
        if business_json['business']['lastAgmDate'] else None
    business.last_ar_date = datetime.date.fromisoformat(business_json['business']['lastArDate'])\
        if business_json['business']['lastArDate'] else business.last_agm_date
    business.legal_type = business_json['business']['legalType']
    return business


def create_address(address_json: dict, address_type: Address.ADDRESS_TYPES) -> Address:
    """Create a new address in lear via the model."""
    address = Address()
    address.address_type = address_type
    address.city = address_json['addressCity']
    address.country = pycountry.countries.search_fuzzy(address_json['addressCountry'])[0].alpha_2
    address.delivery_instructions = address_json['deliveryInstructions']
    address.postal_code = address_json['postalCode']
    address.region = address_json['addressRegion']
    address.street = address_json['streetAddress']
    address.street_additional = address_json['streetAddressAdditional']
    return address


def create_office(business: Business, addresses: list, office_type: str):
    """Create office and link it to business."""
    office = Office()
    office.office_type = office_type
    office.addresses = addresses

    if business.offices is None:
        business.offices = []

    business.offices.append(office)


def add_business_addresses(business: Business, offices_json: dict):
    """Add office addresses to business."""
    for office_type in offices_json:
        delivery_address = create_address(offices_json[office_type]['deliveryAddress'], Address.DELIVERY)
        mailing_address = None
        if offices_json[office_type].get('mailingAddress', None):
            mailing_address = create_address(offices_json[office_type]['mailingAddress'], Address.MAILING)
        else:
            # clone delivery to mailing
            mailing_address = copy.deepcopy(delivery_address)
            mailing_address.address_type = Address.MAILING

        create_office(business, [mailing_address, delivery_address], office_type)


def add_business_directors(business: Business, directors_json: dict):
    """Create directors and add them to business."""
    for director in directors_json['directors']:
        delivery_address = create_address(director['deliveryAddress'], Address.DELIVERY)

        # create person/organization get them if they already exist
        party = Party.find_by_name(
            first_name=director['officer'].get('firstName', '').upper(),
            last_name=director['officer'].get('lastName', '').upper(),
            organization_name=director.get('organization_name', '').upper()
        )
        if not party:
            party = Party(
                first_name=director['officer'].get('firstName', '').upper(),
                last_name=director['officer'].get('lastName', '').upper(),
                middle_initial=director['officer'].get('middleInitial', '').upper(),
                title=director.get('title', '').upper(),
                organization_name=director.get('organization_name', '').upper()
            )

        # add addresses to party
        party.delivery_address = delivery_address

        # create party role and link party to it
        party_role = PartyRole(
            role=PartyRole.RoleTypes.DIRECTOR.value,
            appointment_date=director.get('appointmentDate'),
            cessation_date=director.get('cessationDate'),
            party=party
        )

        business.party_roles.append(party_role)


def historic_filings_exist(business_id: int):
    """Check if there are historic filings for this business."""
    filings = Filing.get_filings_by_status(business_id, [Filing.Status.COMPLETED.value])
    for possible_historic in filings:
        if possible_historic.json['filing']['header']['date'] < '2019-03-08':
            return True
    return False


def load_historic_filings(corp_num: str, business: Business):
    """Load historic filings for a business."""
    try:
        # get historic filings
        r = requests.get(f'{COLIN_API}/api/v1/businesses/{corp_num}/filings/historic', timeout=TIMEOUT)
        if r.status_code != HTTPStatus.OK or not r.json():
            print(f'skipping history for {corp_num} historic filings not found')

        else:
            for historic_filing in r.json():
                uow = versioning_manager.unit_of_work(db.session)
                transaction = uow.create_transaction(db.session)
                filing = Filing()
                filing_date = historic_filing['filing']['header']['date']
                filing.filing_date = datetime.datetime.strptime(filing_date, '%Y-%m-%d')
                filing.business_id = business.id
                filing.filing_json = historic_filing
                for colin_id in filing.filing_json['filing']['header']['colinIds']:
                    colin_event_id = ColinEventId()
                    colin_event_id.colin_event_id = colin_id
                    filing.colin_event_ids.append(colin_event_id)
                filing.transaction_id = transaction.id
                filing._filing_type = historic_filing['filing']['header']['name']
                filing.paper_only = True
                filing.effective_date = datetime.datetime.strptime(
                    historic_filing['filing']['header']['effectiveDate'], '%Y-%m-%d')
                updater_user = User.find_by_username(UPDATER_USERNAME)
                filing.submitter_id = updater_user.id
                filing.source = Filing.Source.COLIN.value

                db.session.add(filing)

            # only commit after all historic filings were added successfully
            db.session.commit()
            LOADED_FILING_HISTORY.append(corp_num)

    except requests.exceptions.Timeout:
        print('rolling back partial changes...')
        db.session.rollback()
        FAILED_FILING_HISTORY.append(corp_num)
        print('colin_api request timed out getting historic filings.')
    except Exception as err:
        print('rolling back partial changes...')
        db.session.rollback()
        FAILED_FILING_HISTORY.append(corp_num)
        raise err


def load_corps(csv_filepath: str = 'corp_nums/corps_to_load.csv'):
    """Load corps in given csv file from oracle into postgres."""
    global ROWCOUNT
    with open(csv_filepath, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        with FLASK_APP.app_context():
            for row in reader:
                corp_num = row['CORP_NUM']
                print('loading: ', corp_num)
                added = False
                ROWCOUNT += 1
                try:
                    business = Business.find_by_identifier(corp_num)
                    if not business:
                        try:
                            # get business info
                            r = requests.get(
                                COLIN_API + '/api/v1/businesses/' + corp_num,
                                timeout=TIMEOUT
                            )
                            if r.status_code != HTTPStatus.OK or not r.json():
                                FAILED_CORPS.append(corp_num)
                                print(f'skipping {corp_num} business info not found')
                                continue
                            business_json = r.json()

                            # get business offices
                            r = requests.get(
                                COLIN_API + '/api/v1/businesses/' +
                                corp_num + '/office',
                                timeout=TIMEOUT)
                            if r.status_code != HTTPStatus.OK \
                                    or not r.json():
                                FAILED_CORPS.append(corp_num)
                                print('skipping ' + corp_num + ' business offices not found')
                                continue
                            offices_json = r.json()

                            # get business directors
                            r = requests.get(f'{COLIN_API}/api/v1/businesses/{corp_num}/parties', timeout=TIMEOUT)
                            if r.status_code != HTTPStatus.OK \
                                    or not r.json():
                                FAILED_CORPS.append(corp_num)
                                print(f'skipping {corp_num} business directors not found')
                                continue
                            directors_json = r.json()
                        except requests.exceptions.Timeout:
                            FAILED_CORPS.append(corp_num)
                            print('colin_api request timed out getting corporation details.')
                            continue

                        uow = versioning_manager.unit_of_work(db.session)
                        transaction = uow.create_transaction(db.session)
                        try:
                            business = create_business(db, business_json)
                            add_business_addresses(business, offices_json)
                            add_business_directors(business, directors_json)
                            db.session.add(business)
                            filing = Filing()
                            filing.filing_json = {
                                'filing': {
                                    'header': {
                                        'name': 'lear_epoch'
                                    },
                                    'business': business.json()
                                }
                            }
                            filing._filing_type = 'lear_epoch'
                            filing.source = Filing.Source.COLIN.value
                            filing.transaction_id = transaction.id
                            db.session.add(filing)
                            db.session.commit()

                            # assign filing to business (now that business record has been comitted and id exists)
                            filing.business_id = business.id
                            db.session.add(filing)
                            db.session.commit()
                            added = True
                            NEW_CORPS.append(corp_num)
                        except Exception as err:
                            print(err)
                            print(f'skipping {corp_num} missing info')
                            FAILED_CORPS.append(corp_num)
                    else:
                        added = True
                        print('-> business info already exists -- skipping corp load')

                    if added and not historic_filings_exist(business.id):
                        load_historic_filings(corp_num=corp_num)
                    else:
                        print('-> historic filings already exist - skipping history load')
                except Exception as err:
                    print(err)
                    exit(-1)


if __name__ == '__main__':
    print(f'processed: {ROWCOUNT} rows')
    print(f'Successfully loaded  {len(NEW_CORPS)}')
    print(f'Failed to load {len(FAILED_CORPS)}')
    print(f'Histories loaded for {len(LOADED_FILING_HISTORY)}')
    print(f'Histories failed for {len(FAILED_FILING_HISTORY)}')
