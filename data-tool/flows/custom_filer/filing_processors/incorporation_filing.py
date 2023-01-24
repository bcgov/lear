# Copyright © 2020 Province of British Columbia
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
"""File processing rules and actions for the incorporation of a business."""
import copy, json, requests
from contextlib import suppress
from http import HTTPStatus
from typing import Dict

from legal_api.models import Business, Document, Filing, RegistrationBootstrap
from legal_api.services.bootstrap import AccountService

from ..filing_meta import FilingMeta
from .filing_components import aliases, business_info, business_profile, filings, shares
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
            AccountService.create_affiliation(
                account=account_id,
                business_registration=business.identifier,
                business_name=business.legal_name,
                corp_type_code=business.legal_type
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
        print(f'Queue Error: Affiliation error for filing:{filing.id}, with err:{err}')
        raise Exception(f'Queue Error: Affiliation error for filing:{filing.id}, with err:{err}')


def process(business: Business,  # pylint: disable=too-many-branches,too-many-locals
            filing: Dict,
            filing_rec: Filing,
            filing_meta: FilingMeta,
            filing_event_data: Dict):  # pylint: disable=too-many-branches
    """Process the incoming incorporation filing."""
    # Extract the filing information for incorporation
    incorp_filing = filing.get('filing', {}).get('incorporationApplication')
    filing_meta.incorporation_application = {}

    if not incorp_filing:
        print(f'IA legal_filing:incorporationApplication missing from {filing_rec.id}')
        raise Exception(f'IA legal_filing:incorporationApplication missing from {filing_rec.id}')
    if business:
        print(f'Business Already Exist: IA legal_filing:incorporationApplication {filing_rec.id}')
        raise Exception(f'Business Already Exist: IA legal_filing:incorporationApplication {filing_rec.id}')

    business_info_obj = incorp_filing.get('nameRequest')
    corp_num = filing['filing']['business']['identifier']

    # Initial insert of the business record
    business = Business()
    business = business_info.update_business_info(corp_num, business, business_info_obj, filing_rec)
    business.send_ar_ind = filing_event_data['c_send_ar_ind']
    business.state = Business.State.ACTIVE

    if nr_number := business_info_obj.get('nrNumber', None):
        filing_meta.incorporation_application = {**filing_meta.incorporation_application,
                                                 **{'nrNumber': nr_number,
                                                    'legalName': business_info_obj.get('legalName', None)}}

    if not business:
        print(f'IA incorporationApplication {filing_rec.id}, Unable to create business.')
        raise Exception(f'IA incorporationApplication {filing_rec.id}, Unable to create business')

    if offices := incorp_filing['offices']:
        update_offices(business, offices)

    if parties := incorp_filing.get('parties'):
        update_parties(business, parties, filing_rec)

    if share_structure := incorp_filing.get('shareStructure'):
        shares.update_share_structure(business, share_structure)

    if name_translations := incorp_filing.get('nameTranslations'):
        aliases.update_aliases(business, name_translations)

    if court_order := incorp_filing.get('courtOrder'):
        filings.update_filing_court_order(filing_rec, court_order)

    if not filing_rec.colin_event_ids:
        # Update the filing json with identifier and founding date.
        ia_json = copy.deepcopy(filing_rec.filing_json)
        if not ia_json['filing'].get('business'):
            ia_json['filing']['business'] = {}
        ia_json['filing']['business']['identifier'] = business.identifier
        ia_json['filing']['business']['legalType'] = business.legal_type
        ia_json['filing']['business']['foundingDate'] = business.founding_date.isoformat()
        filing_rec._filing_json = ia_json  # pylint: disable=protected-access; bypass to update filing data
    return business, filing_rec, filing_meta


def post_process(business: Business, filing: Filing):
    """Post processing activities for incorporations.

    THIS SHOULD NOT ALTER THE MODEL
    """
    with suppress(IndexError, KeyError, TypeError):
        if err := business_profile.update_business_profile(
            business,
            filing.json['filing']['incorporationApplication']['contactPoint']
        ):
            print(f'Queue Error: Update Business for filing:{filing.id}, error:{err}')
