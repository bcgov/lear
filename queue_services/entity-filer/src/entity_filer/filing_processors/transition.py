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
"""File processing rules and actions for the transition of a business."""
import datetime
from http import HTTPStatus
from typing import Dict

import sentry_sdk
from entity_queue_common.service_utils import QueueException
from legal_api.models import Business, Filing
from legal_api.services.bootstrap import AccountService

from entity_filer.filing_processors.filing_components import aliases, business_info, shares
from entity_filer.filing_processors.filing_components.offices import update_offices
from entity_filer.filing_processors.filing_components.parties import update_parties


def create_affiliation(business: Business, filing: Filing):
    """Create an affiliation for the business."""
    try:
        rv = AccountService.create_affiliation(
            account=filing.payment_account,
            business_registration=business.identifier,
            business_name=business.legal_name,
            corp_type_code=business.legal_type
        )

        if rv not in (HTTPStatus.OK, HTTPStatus.CREATED):
            deaffiliation = AccountService.delete_affiliation(filing.payment_account, business.identifier)
            sentry_sdk.capture_message(
                f'Queue Error: Unable to affiliate business:{business.identifier} for filing:{filing.id}',
                level='error'
            )
        if rv not in (HTTPStatus.OK, HTTPStatus.CREATED) \
                or ('deaffiliation' in locals() and deaffiliation != HTTPStatus.OK):
            raise QueueException
    except Exception as err:  # pylint: disable=broad-except; note out any exception, but don't fail the call
        sentry_sdk.capture_message(
            f'Queue Error: Affiliation error for filing:{filing.id}, with err:{err}',
            level='error'
        )


def process(business: Business, filing: Dict, filing_rec: Filing):
    # pylint: disable=too-many-locals; 1 extra
    """Process the incoming transition filing."""
    # Extract the filing information for transition application
    transition_filing = filing.get('transition')

    if not transition_filing:
        raise QueueException(f'legal_filing:transition data missing from {filing_rec.id}')
    if business:
        raise QueueException(f'Business Already Exist: legal_filing:transitionApplication {filing_rec.id}')

    business_info_obj = filing_rec.filing_json['filing']['business']

    # Initial insert of the business record
    business = Business()
    corp_num = business_info_obj.get('identifier')
    business = business_info.update_business_info(corp_num, business, business_info_obj, filing_rec)
    business.founding_date = datetime.datetime.fromisoformat(business_info_obj.get('foundingDate'))
    business.restriction_ind = transition_filing.get('hasProvisions')

    if offices := transition_filing['offices']:
        update_offices(business, offices)

    if parties := transition_filing.get('parties'):
        update_parties(business, parties)

    if share_structure := transition_filing['shareStructure']:
        shares.update_share_structure(business, share_structure)

    if name_translations := transition_filing.get('nameTranslations'):
        aliases.update_aliases(business, name_translations)

    return business, filing_rec
