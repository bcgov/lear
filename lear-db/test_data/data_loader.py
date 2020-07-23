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
from colin_api.models import CorpName
from dotenv import find_dotenv, load_dotenv
from flask import Flask
from legal_api import db
from legal_api.config import get_named_config
from legal_api.models import (
    Address,
    Alias,
    Business,
    Filing,
    Office,
    Party,
    PartyRole,
    Resolution,
    ShareClass,
    ShareSeries,
    User,
)
from legal_api.models.colin_event_id import ColinEventId
from pytz import timezone
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

BUSINESS_MODEL_INFO_TYPES = {
    Business.LegalTypes.BCOMP.value: [
        'business',
        'office',
        'parties',
        'sharestructure',
        'resolutions',
        'aliases'
    ],
    Business.LegalTypes.COOP.value: [
        'business',
        'office',
        'parties'
    ]
}


def get_oracle_info(corp_num: str, legal_type: str, info_type: str) -> dict:
    """Get current business info for (business, offices, directors, etc.)."""
    if info_type == 'aliases':
        info_type = f'names/{CorpName.TypeCodes.TRANSLATION.value}'

    url = f'{COLIN_API}/api/v1/businesses/{legal_type}/{corp_num}/{info_type}'
    if info_type == 'resolutions':
        url = f'{COLIN_API}/api/v1/businesses/internal/{legal_type}/{corp_num}/{info_type}'
    elif info_type == 'business':
        url = f'{COLIN_API}/api/v1/businesses/{legal_type}/{corp_num}'

    r = requests.get(url, timeout=TIMEOUT)
    if r.status_code != HTTPStatus.OK or not r.json():
        FAILED_CORPS.append(corp_num)
        print(f'skipping {corp_num} business {info_type} not found')
        return {'failed': True}
    return r.json()


def convert_to_datetime(datetime_str: str) -> datetime.datetime:
    """Convert given datetime string into a datetime obj."""
    datetime_obj = datetime.datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%S-00:00')
    datetime_utc_tz = datetime_obj.replace(tzinfo=timezone('UTC'))
    return datetime_utc_tz


def create_business(business_json: dict) -> Business:
    """Create a new business in lear via the model."""
    business = Business(
        identifier=business_json['business']['identifier'],
        founding_date=convert_to_datetime(business_json['business']['foundingDate']),
        last_ledger_timestamp=convert_to_datetime(business_json['business']['lastLedgerTimestamp']),
        legal_name=business_json['business']['legalName'],
        legal_type=business_json['business']['legalType'],
        last_modified=datetime.datetime.utcnow()
    )
    business.last_ar_date = datetime.datetime.fromisoformat(business_json['business']['lastArDate']) \
        if business_json['business']['lastArDate'] else None
    business.last_agm_date = datetime.datetime.fromisoformat(business_json['business']['lastAgmDate']) \
        if business_json['business']['lastAgmDate'] else business.last_ar_date
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


def create_share_class(share_class_info: dict) -> ShareClass:
    """Create a new share class and associated series."""
    share_class = ShareClass(
        name=share_class_info['name'],
        priority=share_class_info['priority'],
        max_share_flag=share_class_info['hasMaximumShares'],
        max_shares=share_class_info.get('maxNumberOfShares', None),
        par_value_flag=share_class_info['hasParValue'],
        par_value=share_class_info.get('parValue', None),
        currency=share_class_info.get('currency', None),
        special_rights_flag=share_class_info['hasRightsOrRestrictions'],
    )
    for series in share_class_info['series']:
        share_series = ShareSeries(
            name=series['name'],
            priority=series['priority'],
            max_share_flag=series['hasMaximumShares'],
            max_shares=series.get('maxNumberOfShares', None),
            special_rights_flag=series['hasRightsOrRestrictions']
        )
        share_class.series.append(share_series)
    return share_class


def add_business_offices(business: Business, offices_json: dict):
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
        mailing_address = create_address(director['mailingAddress'], Address.MAILING)
        # create person/organization or get them if they already exist for corp
        party = PartyRole.find_party_by_name(
            business_id=business.id,
            first_name=director['officer'].get('firstName', '').upper(),
            last_name=director['officer'].get('lastName', '').upper(),
            middle_initial=director['officer'].get('middleInitial', '').upper(),
            org_name=director.get('organization_name', '').upper()
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
        party.mailing_address = mailing_address

        # create party role and link party to it
        party_role = PartyRole(
            role=PartyRole.RoleTypes.DIRECTOR.value,
            appointment_date=director.get('appointmentDate'),
            cessation_date=director.get('cessationDate'),
            party=party
        )

        business.party_roles.append(party_role)


def add_business_shares(business: Business, shares_json: dict):
    """Create shares and add them to business."""
    for share_class_info in shares_json['shareClasses']:
        share_class = create_share_class(share_class_info)
        business.share_classes.append(share_class)


def add_business_resolutions(business: Business, resolutions_json: dict):
    """Create resolutions and add them to business."""
    for resolution_date in resolutions_json['resolutionDates']:
        resolution = Resolution(resolution_date=resolution_date)
        business.resolutions.append(resolution)


def add_business_aliases(business: Business, aliases_json: dict):
    """Create name translations and add them to business."""
    for name_obj in aliases_json['names']:
        alias = Alias(alias=name_obj['legalName'])
        business.aliases.append(alias)


def history_needed(business: Business):
    """Check if there is history to load for this business."""
    if business.legal_type != Business.LegalTypes.COOP.value:
        return False
    filings = Filing.get_filings_by_status(business.id, [Filing.Status.COMPLETED.value])
    for possible_historic in filings:
        if possible_historic.json['filing']['header']['date'] < '2019-03-08':
            return False
    return True


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
                    if business:
                        added = True
                        print('-> business info already exists -- skipping corp load')
                    else:
                        legal_type = Business.LegalTypes.BCOMP.value
                        if corp_num[:2] == Business.LegalTypes.COOP.value:
                            legal_type = Business.LegalTypes.COOP.value
                        try:
                            # get current company info
                            business_current_info = {}
                            for info_type in BUSINESS_MODEL_INFO_TYPES[legal_type]:
                                business_current_info[info_type] = get_oracle_info(
                                    corp_num=corp_num,
                                    legal_type=legal_type,
                                    info_type=info_type
                                )
                                if business_current_info[info_type].get('failed', False):
                                    raise Exception(f'could not load {info_type}')

                        except requests.exceptions.Timeout:
                            FAILED_CORPS.append(corp_num)
                            print('colin_api request timed out getting corporation details.')
                            continue

                        except Exception as err:
                            print(f'exception: {err}')
                            print(f'skipping load for {corp_num}, exception occurred getting company info')
                            continue

                        uow = versioning_manager.unit_of_work(db.session)
                        transaction = uow.create_transaction(db.session)
                        try:
                            # add BC prefix to non coop identifiers
                            if legal_type != Business.LegalTypes.COOP.value:
                                business_current_info['business']['business']['identifier'] = 'BC' + \
                                    business_current_info['business']['business']['identifier']

                            # add company to postgres db
                            business = create_business(business_current_info['business'])
                            add_business_offices(business, business_current_info['office'])
                            add_business_directors(business, business_current_info['parties'])
                            if legal_type == Business.LegalTypes.BCOMP.value:
                                add_business_shares(business, business_current_info['sharestructure'])
                                add_business_resolutions(business, business_current_info['resolutions'])
                                add_business_aliases(business, business_current_info['aliases'])
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
                            business.filings.append(filing)
                            business.save()
                            added = True
                            NEW_CORPS.append(corp_num)
                        except Exception as err:
                            print(err)
                            print(f'skipping {corp_num} missing info')
                            FAILED_CORPS.append(corp_num)

                    if added and history_needed(business=business):
                        load_historic_filings(corp_num=corp_num, business=business)
                    else:
                        print('-> historic filings not needed - skipping history load')
                except Exception as err:
                    print(err)
                    exit(-1)


if __name__ == '__main__':
    load_corps(csv_filepath='corp_nums/corps_to_load.csv')
    print(f'processed: {ROWCOUNT} rows')
    print(f'Successfully loaded  {len(NEW_CORPS)}')
    print(f'Failed to load {len(FAILED_CORPS)}')
    print(f'Histories loaded for {len(LOADED_FILING_HISTORY)}')
    print(f'Histories failed for {len(FAILED_FILING_HISTORY)}')
