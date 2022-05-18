# Copyright © 2022 Province of British Columbia
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
"""File processing rules and actions for the registration of a business."""
import copy, json, requests
from contextlib import suppress
from http import HTTPStatus
from typing import Dict

import dpath
from legal_api.models import Business, Filing, RegistrationBootstrap
from legal_api.services.bootstrap import AccountService
from legal_api.utils.datetime import datetime

from ..filing_meta import FilingMeta
from .filing_components import business_info, business_profile, filings
from .filing_components.offices import update_offices
from .filing_components.parties import update_parties
from flask import current_app

def update_affiliation(business: Business, filing: Filing):
    """Create an affiliation for the business and remove the bootstrap."""
    try:

        # TODO affiliation to an account does not need to happen.  only entity creation in auth is req'd.
        #  used for testing purposes to see how things look in entity dashboard - remove when done testing
        # rv = AccountService.create_affiliation(
        #     # account=bootstrap.account,
        #     account=2596,
        #     business_registration=business.identifier,
        #     business_name=business.legal_name,
        #     corp_type_code=business.legal_type
        # )

        account_svc_entity_url = current_app.config.get('ACCOUNT_SVC_ENTITY_URL')
        token = AccountService.get_bearer_token()

        if not token:
            return HTTPStatus.UNAUTHORIZED

        # Create an entity record
        entity_data = json.dumps({'businessIdentifier': business.identifier,
                                  'corpTypeCode': business.legal_type,
                                  'name': business.legal_name
                                  })
        entity_record = requests.post(
            url=account_svc_entity_url,
            headers={**AccountService.CONTENT_TYPE_JSON,
                     'Authorization': AccountService.BEARER + token},
            data=entity_data,
            timeout=AccountService.timeout
        )


    except Exception as err:  # pylint: disable=broad-except; note out any exception, but don't fail the call
        # sentry_sdk.capture_message(
        #     f'Queue Error: Affiliation error for filing:{filing.id}, with err:{err}',
        #     level='error'
        # )
        print(f'Queue Error: Affiliation error for filing:{filing.id}, with err:{err}')



def process(business: Business,  # pylint: disable=too-many-branches
            filing: Dict,
            filing_rec: Filing,
            filing_meta: FilingMeta,
            filing_event_data: Dict):  # pylint: disable=too-many-branches
    """Process the incoming registration filing."""
    # Extract the filing information for registration
    registration_filing = filing.get('filing', {}).get('registration')
    filing_meta.registration = {}
    corp_num = registration_filing['business']['identifier']
    tax_id = filing_event_data['c_bn_15']

    if not registration_filing:
        # raise QueueException(f'Registration legal_filing:registration missing from {filing_rec.id}')
        raise Exception(f'Registration legal_filing:registration missing from {filing_rec.id}')

    if business:
        # raise QueueException(f'Business Already Exist: Registration legal_filing:registration {filing_rec.id}')
        raise Exception(f'Business Already Exist: Registration legal_filing:registration {filing_rec.id}')

    business_info_obj = registration_filing.get('nameRequest')

    # Initial insert of the business record
    business = Business()
    business = business_info.update_business_info(corp_num, tax_id, business, business_info_obj, filing_rec)
    business.founding_date = datetime.fromisoformat(registration_filing.get('startDate'))
    if (naics := registration_filing.get('business', {}).get('naics')):
        # TODO resolve 150 length issue
        business_info.update_naics_info(business, naics)

    business.state = Business.State.ACTIVE

    if nr_number := business_info_obj.get('nrNumber', None):
        filing_meta.registration = {**filing_meta.registration,
                                    **{'nrNumber': nr_number,
                                       'legalName': business_info_obj.get('legalName', None)}}

    if not business:
        # raise QueueException(f'Registration {filing_rec.id}, Unable to create business.')
        raise Exception(f'Registration {filing_rec.id}, Unable to create business.')

    if offices := registration_filing['offices']:
        update_offices(business, offices)

    if parties := registration_filing.get('parties'):
        update_parties(business, parties, filing_rec)

    # update court order, if any is present
    with suppress(IndexError, KeyError, TypeError):
        court_order_json = dpath.util.get(filing, '/registration/courtOrder')
        filings.update_filing_court_order(filing_rec, court_order_json)

    # Update the filing json with identifier and founding date.
    registration_json = copy.deepcopy(filing_rec.filing_json)
    registration_json['filing']['business'] = {}
    registration_json['filing']['business']['identifier'] = business.identifier
    registration_json['filing']['registration']['business']['identifier'] = business.identifier
    registration_json['filing']['business']['legalType'] = business.legal_type
    registration_json['filing']['business']['foundingDate'] = business.founding_date.isoformat()
    filing_rec._filing_json = registration_json  # pylint: disable=protected-access; bypass to update filing data

    return business, filing_rec, filing_meta
