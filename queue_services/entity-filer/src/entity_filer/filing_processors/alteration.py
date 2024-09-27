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
from legal_api.models import Business, Filing

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors.filing_components import (
    aliases,
    business_info,
    filings,
    rules_and_memorandum,
    shares,
)


def process(
    business: Business,
    filing_submission: Filing,
    filing: Dict,
    filing_meta: FilingMeta,
    correction: bool = False
):  # pylint: disable=W0613, R0914
    """Render the Alteration onto the model objects."""
    filing_meta.alteration = {}
    to_legal_type = None

    # Alter the corp type, if any
    with suppress(IndexError, KeyError, TypeError):
        if business.legal_type == Business.LegalTypes.COOP.value:
            alteration_json = dpath.util.get(filing, '/alteration')
            coop_association_type = alteration_json.get('cooperativeAssociationType')
            filing_meta.alteration = {**filing_meta.alteration,
                                      'fromCooperativeAssociationType': business.association_type,
                                      'toCooperativeAssociationType': coop_association_type}
            business_info.set_association_type(business, coop_association_type)
        else:
            business_json = dpath.util.get(filing, '/alteration/business')
            to_legal_type = business_json.get('legalType')
            if to_legal_type and business.legal_type != to_legal_type:
                filing_meta.alteration = {**filing_meta.alteration,
                                          'fromLegalType': business.legal_type,
                                          'toLegalType': to_legal_type}
                business_info.set_corp_type(business, business_json)

    # Alter the business name, if any
    with suppress(IndexError, KeyError, TypeError):
        # if nameRequest is present then there could be a name change
        # from name -> numbered OR name -> name OR numbered to name
        business_json = dpath.util.get(filing, '/alteration/nameRequest')
        from_legal_name = business.legal_name
        business_info.set_legal_name(business.identifier, business, business_json, to_legal_type)
        if from_legal_name != business.legal_name:
            filing_meta.alteration = {**filing_meta.alteration,
                                      'fromLegalName': from_legal_name,
                                      'toLegalName': business.legal_name}

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

    # update provisionsRemoved, if any
    with suppress(IndexError, KeyError, TypeError):
        provisions_removed = dpath.util.get(filing, '/alteration/provisionsRemoved')
        if bool(provisions_removed):
            business.restriction_ind = False

    # update rules, if any
    with suppress(IndexError, KeyError, TypeError):
        rules_file_key = dpath.util.get(filing, '/alteration/rulesFileKey')
        rules_file_name = dpath.util.get(filing, '/alteration/rulesFileName')
        if rules_file_key:
            rules_and_memorandum.update_rules(business, filing_submission, rules_file_key, rules_file_name)
            filing_meta.alteration = {**filing_meta.alteration,
                                      'uploadNewRules': True}

    with suppress(IndexError, KeyError, TypeError):
        memorandum_file_key = dpath.util.get(filing, '/alteration/memorandumFileKey')
        rules_and_memorandum.update_memorandum(business, filing_submission, memorandum_file_key)
