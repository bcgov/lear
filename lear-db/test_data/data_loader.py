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
import csv
import os
from http import HTTPStatus

import requests
from colin_api.models.filing import Filing as ColinFiling
from dotenv import find_dotenv, load_dotenv
from flask import Flask
from legal_api import db
from legal_api.config import get_named_config
from legal_api.models import (
    Business,
    Filing,
)
from legal_api.services import queue
from legal_api.models.colin_event_id import ColinEventId
from sqlalchemy_continuum import versioning_manager


load_dotenv(find_dotenv())

FLASK_APP = Flask(__name__)
FLASK_APP.config.from_object(get_named_config('production'))
db.init_app(FLASK_APP)
queue.init_app(FLASK_APP)

COLIN_API = os.getenv('COLIN_API', None)
UPDATER_USERNAME = os.getenv('UPDATER_USERNAME')

ROWCOUNT = 0
TIMEOUT = 15
FAILED_CORPS = []
NEW_CORPS = []
LOADED_FILING_HISTORY = []
FAILED_FILING_HISTORY = []

def load_corps(csv_filepath: str = 'corp_nums/corps_to_load.csv'):
    """Load corps in given csv file from oracle into postgres."""
    global ROWCOUNT
    with open(csv_filepath, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        with FLASK_APP.app_context():
            for row in reader:
                corp_num = row['CORP_NUM']
                added = False
                ROWCOUNT += 1
                try:
                    legal_type = Business.LegalTypes.COOP.value
                    if corp_num[:2] != Business.LegalTypes.COOP.value:
                        legal_type = Business.LegalTypes.COMP.value
                        corp_num = 'BC' + corp_num[-7:]

                    business = Business.find_by_identifier(corp_num)
                    if business:
                        added = True
                        print('-> business info already exists -- skipping corp load')
                        continue

                    filing_event = get_data_load_required_filing_event(legal_type, corp_num)
                    if not filing_event:
                        print('no icorp app or conversion ledger event found -- skipping corp load')
                        continue

                    colin_filing_type = filing_event.get('filing_typ_cd')
                    filing_type = get_filing_type(legal_type, colin_filing_type)
                    colin_filing = get_filing(filing_type, legal_type, filing_event, FLASK_APP)
                    if not colin_filing:
                        print('no filing retrieved from filing event -- skipping corp load')
                        continue

                    uow = versioning_manager.unit_of_work(db.session)
                    transaction = uow.create_transaction(db.session)
                    filing = create_filing(filing_type, colin_filing, filing_event.get('event_id'), corp_num, transaction)
                    filing.save()

                    #push to queue
                    payload = {'filing': {'id': filing.id}}
                    queue.publish_json(payload)
                    added = True
                    NEW_CORPS.append(corp_num)

                except requests.exceptions.Timeout:
                    FAILED_CORPS.append(corp_num)
                    print('colin_api request timed out getting corporation details.')
                    continue

                except Exception as err:
                    print(err)
                    print(f'skipping load for {corp_num}, exception occurred getting company info')
                    FAILED_CORPS.append(corp_num)
                    continue

def create_filing(filing_type, colin_filing, colin_event_id, corp_num, transaction):
    """Create legal api filing using colin filing as base"""
    effective_date = colin_filing['filing']['business']['foundingDate']
    colin_filing['filing']['business']['identifier'] = corp_num
    filing = Filing(effective_date=effective_date, filing_json=colin_filing)
    filing._filing_type = filing_type
    filing.filing_date = effective_date
    colin_event = ColinEventId()
    colin_event.colin_event_id = colin_event_id
    filing.colin_event_ids.append(colin_event)

    # Override the state setting mechanism
    filing.skip_status_listener = True
    filing._status = 'PENDING'
    filing.source = Filing.Source.COLIN.value
    filing.transaction_id = transaction.id
    return filing

def get_data_load_required_filing_event(legal_type, corp_num):
    """Determine whether corp has required filings types (incorp app or conversion ledger)"""
    events = get_filing_events_for_corp(legal_type, corp_num)
    match = next((x for x in events if x.get('filing_typ_cd')
                  in ['OTINC', 'BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONVL']), None)
    return match

def get_filing_events_for_corp(legal_type, corp_num):
    """Retrieve filing events for a given corp"""
    colin_corp_num = corp_num
    if(legal_type == Business.LegalTypes.COMP.value):
        colin_corp_num = corp_num[-7:]

    r = requests.get(f'{COLIN_API}/api/v1/businesses/event/corp_num/{colin_corp_num}', timeout=TIMEOUT)
    if r.status_code != HTTPStatus.OK or not r.json():
        return None

    events = dict(r.json()).get('events', [])
    return events

def get_filing(colin_filing_type, legal_type, event_info: dict = None, application: Flask = None):  # pylint: disable=redefined-outer-name
    """Get filing for a given event from colin"""
    identifier = event_info['corp_num']
    event_id = event_info['event_id']
    print(f'{COLIN_API}/api/v1/businesses/{legal_type}/{identifier}/filings/{colin_filing_type}?eventId={event_id}')
    response = requests.get(
        f'{COLIN_API}/api/v1/businesses/{legal_type}/{identifier}/filings/{colin_filing_type}?eventId={event_id}'
    )
    filing = dict(response.json())
    return filing

def get_filing_type(legal_type, filing_typ_cd):
    """Get generic filing type """
    filing_types = ColinFiling.FILING_TYPES.keys()
    match = next((x for x in filing_types
                  if filing_typ_cd in ColinFiling.FILING_TYPES.get(x).get('type_code_list')),
                 None)
    return match


if __name__ == '__main__':
    load_corps(csv_filepath='corp_nums/corps_to_load.csv')
    print(f'processed: {ROWCOUNT} rows')
    print(f'Successfully loaded  {len(NEW_CORPS)}')
    print(f'Failed to load {len(FAILED_CORPS)}')
