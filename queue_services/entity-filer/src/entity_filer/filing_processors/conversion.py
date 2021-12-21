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
"""File processing rules and actions for historic conversion filing.

A conversion filing is for a business that was created before COLIN,
the original system to manage business corporations.

As the business exists, no new registration identifiers, names, or structures are
altered.

There are no corrections for a conversion filing.
"""
# pylint: disable=superfluous-parens; as pylance requires it
from contextlib import suppress
from typing import Dict

import sentry_sdk
from entity_queue_common.service_utils import QueueException
from legal_api.models import Business, Filing

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors.filing_components import aliases, business_info, business_profile, shares
from entity_filer.filing_processors.filing_components.offices import update_offices
from entity_filer.filing_processors.filing_components.parties import update_parties


def process(business: Business,  # pylint: disable=too-many-branches
            filing: Dict,
            filing_rec: Filing,
            filing_meta: FilingMeta):  # pylint: disable=too-many-branches
    """Process the incoming historic conversion filing."""
    # Extract the filing information for incorporation
    if not (conversion_filing := filing.get('filing', {}).get('conversion')):
        raise QueueException(f'CONVL legal_filing:conversion missing from {filing_rec.id}')

    if business:
        raise QueueException(f'Business Already Exist: CONVL legal_filing:conversion {filing_rec.id}')

    if not (corp_num := filing.get('filing', {}).get('business', {}).get('identifier')):
        raise QueueException(f'conversion {filing_rec.id} missing the business idnetifier.')

    # Initial insert of the business record
    business_info_obj = conversion_filing.get('nameRequest')
    if not (business := business_info.update_business_info(corp_num, Business(), business_info_obj, filing_rec)):
        raise QueueException(f'CONVL conversion {filing_rec.id}, Unable to create business.')

    if offices := conversion_filing.get('offices'):
        update_offices(business, offices)

    if parties := conversion_filing.get('parties'):
        update_parties(business, parties, filing_rec)

    if share_structure := conversion_filing.get('shareStructure'):
        shares.update_share_structure(business, share_structure)

    if name_translations := conversion_filing.get('nameTranslations'):
        aliases.update_aliases(business, name_translations)

    return business, filing_rec


def post_process(business: Business, filing: Filing):
    """Post processing activities for conversion ledger.

    THIS SHOULD NOT ALTER THE MODEL
    """
    with suppress(IndexError, KeyError, TypeError):
        if err := business_profile.update_business_profile(
            business,
            filing.json['filing']['conversion']['contactPoint']
        ):
            sentry_sdk.capture_message(
                f'Queue Error: Update Business for filing:{filing.id}, error:{err}',
                level='error')
