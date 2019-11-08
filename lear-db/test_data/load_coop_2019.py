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
import logging
import os
import sys
from http import HTTPStatus

import psycopg2
import pycountry
import requests
from dotenv import load_dotenv, find_dotenv

from flask import Flask
from legal_api import db
from legal_api.config import get_named_config
from legal_api.models import Address, Business, Director, Filing
from sqlalchemy_continuum import versioning_manager
from sqlalchemy import text


load_dotenv(find_dotenv())

FLASK_APP = Flask(__name__)
FLASK_APP.config.from_object(get_named_config('production'))
db.init_app(FLASK_APP)

COLIN_API = os.getenv('COLIN_API', None)
if not COLIN_API:
    print('ERROR, no COLIN_API defined.')


def create_business(db, business_json):
    business = Business()
    business.identifier = business_json['business']['identifier']
    business.founding_date = business_json['business']['foundingDate']
    business.last_ledger_timestamp = business_json['business']['lastLedgerTimestamp']
    business.legal_name = business_json['business']['legalName']
    business.founding_date = business_json['business']['foundingDate']
    business.last_agm_date = datetime.date.fromisoformat(business_json['business']['lastAgmDate'])
    business.last_ar_date = datetime.date.fromisoformat(business_json['business']['lastArDate'])\
        if business_json['business']['lastArDate'] else business.last_agm_date
    business.legal_type = business_json['business']['legalType']
    return business


def create_delivery_address(delivery_json):

    delivery_address = Address()
    delivery_address.address_type = Address.DELIVERY
    delivery_address.city = delivery_json['addressCity']
    # delivery_address.country = delivery_json['addressCountry']
    delivery_address.country = 'CA'
    delivery_address.delivery_instructions = delivery_json['deliveryInstructions']
    delivery_address.postal_code = delivery_json['postalCode']
    # delivery_address.region = delivery_json['addressRegion']
    delivery_address.region = 'BC'
    delivery_address.street = delivery_json['streetAddress']
    delivery_address.street_additional = delivery_json['streetAddressAdditional']
    return delivery_address


def add_business_addresses(business, offices_json):

    delivery_address = create_delivery_address(offices_json['deliveryAddress'])
    business.delivery_address.append(delivery_address)

    mailing_address = None
    if offices_json['mailingAddress'] == None:
        # clone delivery to mailing
        mailing_address = copy.deepcopy(delivery_address)
    else:
        mailing_address = Address()
        mailing_json = offices_json['mailingAddress']
        mailing_address.city = mailing_json['addressCity']
        mailing_address.country = pycountry.countries.search_fuzzy(
            mailing_json['addressCountry'])[0].alpha_2
        mailing_address.delivery_instructions = mailing_json['deliveryInstructions']
        mailing_address.postal_code = mailing_json['postalCode']
        mailing_address.region = mailing_json['addressRegion']
        mailing_address.street = mailing_json['streetAddress']
        mailing_address.street_additional = mailing_json['streetAddressAdditional']
    mailing_address.address_type = Address.MAILING
    business.mailing_address.append(mailing_address)


def add_business_directors(business, directors_json):
    for director in directors_json['directors']:
        delivery_address = create_delivery_address(director['deliveryAddress'])

        officer = director['officer']
        d = Director()
        d.first_name = officer['firstName']
        d.last_name = officer['lastName']
        d.middle_initial = officer['middleInitial']
        d.appointment_date = datetime.date.fromisoformat(
            director['appointmentDate'])
        d.title = director['title']
        d.delivery_address = delivery_address
        business.directors.append(d)


def historic_filings_exist(business_id):
    filings = Filing.get_filings_by_status(business_id, [Filing.Status.COMPLETED.value])
    for possible_historic in filings:
        if possible_historic.json['filing']['header']['date'] < '2019-03-08':
            return True
    return False


rowcount = 0
TIMEOUT = 15

with open('coops.csv', 'r') as csvfile:
    reader = csv.DictReader(csvfile)
    with FLASK_APP.app_context():
        for row in reader:
            rowcount += 1
            print('loading: ', row['CORP_NUM'])

            try:
                business = Business.find_by_identifier(row['CORP_NUM'])
                if not business:
                    try:

                        # get business info
                        r = requests.get(
                            COLIN_API + '/api/v1/businesses/' + row['CORP_NUM'],
                            timeout=TIMEOUT)
                        if r.status_code != HTTPStatus.OK \
                                or not r.json():
                            print('skipping ' + row['CORP_NUM'] +
                                  ' business info not found')
                            continue
                        business_json = r.json()

                        # get business offices
                        r = requests.get(
                            COLIN_API + '/api/v1/businesses/' +
                            row['CORP_NUM'] + '/office',
                            timeout=TIMEOUT)
                        if r.status_code != HTTPStatus.OK \
                                or not r.json():
                            print('skipping ' + row['CORP_NUM'] +
                                  ' business offices not found')
                            continue
                        offices_json = r.json()

                        # get business directors
                        r = requests.get(
                            COLIN_API + '/api/v1/businesses/' +
                            row['CORP_NUM'] + '/directors',
                            timeout=TIMEOUT)
                        if r.status_code != HTTPStatus.OK \
                                or not r.json():
                            print('skipping ' + row['CORP_NUM'] +
                                  ' business directors not found')
                            continue
                        directors_json = r.json()
                    except requests.exceptions.Timeout as timeout:
                        print('colin_api request timed out getting corporation details.')
                        continue

                    uow = versioning_manager.unit_of_work(db.session)
                    transaction = uow.create_transaction(db.session)

                    business = create_business(db, business_json)
                    add_business_addresses(business, offices_json)
                    add_business_directors(business, directors_json)
                    db.session.add(business)

                    filing = Filing()
                    # filing.filing_date = datetime.datetime.utcnow
                    filing.filing_json = {'filing':
                                          {'header':
                                           {'name': 'lear_epoch'}
                                           }}
                    filing.transaction_id = transaction.id
                    db.session.add(filing)
                    db.session.commit()

                    # assign filing to business (now that business record has been comitted and id exists)
                    filing.business_id = business.id
                    db.session.add(filing)
                    db.session.commit()
                else:
                    print('->business info already exists -- skipping corp load')

                if not historic_filings_exist(business.id):
                    try:
                        # get historic filings
                        r = requests.get(COLIN_API + '/api/v1/businesses/' + row['CORP_NUM'] + '/filings/historic',
                                         timeout=TIMEOUT)
                        if r.status_code != HTTPStatus.OK or not r.json():
                            print(f'skipping history for {row["CORP_NUM"]} historic filings not found')

                        for historic_filing in r.json():
                            uow = versioning_manager.unit_of_work(db.session)
                            transaction = uow.create_transaction(db.session)
                            filing = Filing()
                            filing_date = historic_filing['filing']['header']['date']
                            filing.filing_date = datetime.datetime.strptime(filing_date, '%Y-%m-%d')
                            filing.business_id = business.id
                            filing.filing_json = historic_filing
                            filing.transaction_id = transaction.id
                            filing_type = historic_filing['filing']['header']['name']
                            filing.colin_event_id = historic_filing['filing'][filing_type]['eventId']
                            filing.paper_only = True
                            db.session.add(filing)
                            db.session.commit()

                    except requests.exceptions.Timeout as timeout:
                        print('colin_api request timed out getting historic filings.')
                else:
                    print('->historic filings already exist - skipping history load')
            except Exception as err:
                # db.session.rollback()
                print(err)
                exit(-1)


print(f'processed: {rowcount} rows')
