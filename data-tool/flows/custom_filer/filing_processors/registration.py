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
from datetime import timedelta
from http import HTTPStatus
from typing import Dict

import dpath
from legal_api.models import Business, Filing, RegistrationBootstrap, Comment
from legal_api.services.bootstrap import AccountService
from legal_api.utils.datetime import datetime

from ..filing_meta import FilingMeta
from .filing_components import business_info, business_profile, filings
from .filing_components.offices import update_offices
from .filing_components.parties import update_parties
from flask import current_app

def update_affiliation(config, business: Business, filing: Filing):
    """Create an affiliation for the business and remove the bootstrap."""
    try:

        # TODO affiliation to an account does not need to happen.  only entity creation in auth is req'd.
        #  used for testing purposes to see how things look in entity dashboard - remove when done testing
        if config.AFFILIATE_ENTITY:
            account_id = config.AFFILIATE_ENTITY_ACCOUNT_ID
            pass_code = business_info.get_firm_affiliation_passcode(business.id)
            AccountService.create_affiliation(
                account=account_id,
                business_registration=business.identifier,
                business_name=business.legal_name,
                corp_type_code=business.legal_type,
                pass_code=pass_code
            )
        elif config.UPDATE_ENTITY:
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

    if not registration_filing:
        # raise QueueException(f'Registration legal_filing:registration missing from {filing_rec.id}')
        raise Exception(f'Registration legal_filing:registration missing from {filing_rec.id}')

    if business:
        # raise QueueException(f'Business Already Exist: Registration legal_filing:registration {filing_rec.id}')
        raise Exception(f'Business Already Exist: Registration legal_filing:registration {filing_rec.id}')

    business_info_obj = registration_filing.get('nameRequest')

    # Initial insert of the business record
    business = Business()
    business = business_info.update_business_info(corp_num, business, business_info_obj, filing_rec)
    if start_date := registration_filing.get('startDate'):
        business.start_date = datetime.fromisoformat(start_date) + timedelta(hours=8)
    business.founding_date = filing_rec.effective_date
    business.admin_freeze = filing_event_data['c_is_frozen']

    business_obj = registration_filing.get('business', {})
    if (naics := registration_filing.get('business', {}).get('naics')):
        business_info.update_naics_info(business, naics)
    business.tax_id = business_obj.get('taxId', None)
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

    if lt_notation := filing_event_data.get('lt_notation'):
        filing_rec.comments.append(
            Comment(
                comment=lt_notation,
                staff_id=filing_rec.submitter_id
            )
        )

    # Update the filing json with identifier and founding date.
    registration_json = copy.deepcopy(filing_rec.filing_json)
    registration_json['filing']['business'] = {}
    registration_json['filing']['business']['identifier'] = business.identifier
    registration_json['filing']['registration']['business']['identifier'] = business.identifier
    registration_json['filing']['business']['legalType'] = business.legal_type
    registration_json['filing']['business']['foundingDate'] = business.founding_date.isoformat()
    filing_rec._filing_json = registration_json  # pylint: disable=protected-access; bypass to update filing data

    return business, filing_rec, filing_meta


def post_process(business: Business, filing: Filing):
    """Post processing activities for registration.

    THIS SHOULD NOT ALTER THE MODEL
    """
    with suppress(IndexError, KeyError, TypeError):
        if err := business_profile.update_business_profile(
                business,
                filing.json['filing']['registration']['contactPoint']
        ):
            print(f'Queue Error: Update Business for filing:{filing.id}, error:{err}')
