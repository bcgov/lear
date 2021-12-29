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
"""File processing rules and actions for the Change of Name filing."""
from contextlib import suppress
from typing import Dict

import dpath
import sentry_sdk
from legal_api.models import Business, Filing

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors.filing_components import (
    aliases,
    business_info,
    business_profile,
    filings,
    name_request,
    shares,
)


def process(
    business: Business,
    filing_submission: Filing,
    filing: Dict,
    filing_meta: FilingMeta,
    correction: bool = False
):  # pylint: disable=W0613
    """Render the Alteration onto the model objects."""
    filing_meta.alteration = {}
    # Alter the corp type, if any
    with suppress(IndexError, KeyError, TypeError):
        business_json = dpath.util.get(filing, '/alteration/business')
        filing_meta.alteration = {**filing_meta.alteration,
                                  **{'fromLegalType': business.legal_type,
                                     'toLegalType': business_json.get('legalType')}}
        business_info.set_corp_type(business, business_json)

    # Alter the business name, if any
    with suppress(IndexError, KeyError, TypeError):
        # if nameRequest is present then there could be a name change
        # from name -> numbered OR name -> name OR numbered to name
        business_json = dpath.util.get(filing, '/alteration/nameRequest')
        from_legal_name = business.legal_name
        business_info.set_legal_name(business.identifier, business, business_json)
        if from_legal_name != business.legal_name:
            filing_meta.alteration = {**filing_meta.alteration,
                                      **{'fromLegalName': from_legal_name,
                                         'toLegalName': business.legal_name}}

    # update court order, if any is present
    with suppress(IndexError, KeyError, TypeError):
        court_order_json = dpath.util.get(filing, '/alteration/courtOrder')
        filings.update_filing_court_order(filing_submission, court_order_json)

    # update name translations, if any
    with suppress(IndexError, KeyError, TypeError):
        alias_json = dpath.util.get(filing, '/alteration/nameTranslations')
        aliases.update_aliases(business, alias_json)

    # update share structure and resolutions, if any
    with suppress(IndexError, KeyError, TypeError):
        share_structure = dpath.util.get(filing, '/alteration/shareStructure')
        shares.update_share_structure(business, share_structure)


def post_process(business: Business, filing: Filing, correction: bool = False):
    """Post processing activities for incorporations.

    THIS SHOULD NOT ALTER THE MODEL
    """
    if not correction and name_request.has_new_nr_for_alteration(business, filing.filing_json):
        name_request.consume_nr(business, filing, '/filing/alteration/nameRequest/nrNumber')

    with suppress(IndexError, KeyError, TypeError):
        if err := business_profile.update_business_profile(
            business,
            filing.json['filing']['alteration']['contactPoint']
        ):
            sentry_sdk.capture_message(
                f'Queue Error: Update Business for filing:{filing.id},error:{err}',
                level='error')
