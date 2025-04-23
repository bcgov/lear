# Copyright © 2025 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""File processing rules and actions for the Change of Name filing."""
from contextlib import suppress
from typing import Dict

import dpath
from business_model.models import Business, Filing

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import (
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
            alteration_json = dpath.get(filing, '/alteration')
            coop_association_type = alteration_json.get('cooperativeAssociationType')
            filing_meta.alteration = {**filing_meta.alteration,
                                      'fromCooperativeAssociationType': business.association_type,
                                      'toCooperativeAssociationType': coop_association_type}
            business_info.set_association_type(business, coop_association_type)
        else:
            business_json = dpath.get(filing, '/alteration/business')
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
        business_json = dpath.get(filing, '/alteration/nameRequest')
        from_legal_name = business.legal_name
        business_info.set_legal_name(business.identifier, business, business_json, to_legal_type)
        if from_legal_name != business.legal_name:
            filing_meta.alteration = {**filing_meta.alteration,
                                      'fromLegalName': from_legal_name,
                                      'toLegalName': business.legal_name}

    # update court order, if any is present
    with suppress(IndexError, KeyError, TypeError):
        court_order_json = dpath.get(filing, '/alteration/courtOrder')
        filings.update_filing_court_order(filing_submission, court_order_json)

    # update name translations, if any
    with suppress(IndexError, KeyError, TypeError):
        alias_json = dpath.get(filing, '/alteration/nameTranslations')
        aliases.update_aliases(business, alias_json)

    # update share structure and resolutions, if any
    with suppress(IndexError, KeyError, TypeError):
        share_structure = dpath.get(filing, '/alteration/shareStructure')
        shares.update_share_structure(business, share_structure)

    # update provisionsRemoved, if any
    with suppress(IndexError, KeyError, TypeError):
        provisions_removed = dpath.get(filing, '/alteration/provisionsRemoved')
        if bool(provisions_removed):
            business.restriction_ind = False

    # update rules, if any
    with suppress(IndexError, KeyError, TypeError):
        rules_file_key = dpath.get(filing, '/alteration/rulesFileKey')
        rules_file_name = dpath.get(filing, '/alteration/rulesFileName')
        if rules_file_key:
            rules_and_memorandum.update_rules(business, filing_submission, rules_file_key, rules_file_name)
            filing_meta.alteration = {**filing_meta.alteration,
                                      'uploadNewRules': True}

    with suppress(IndexError, KeyError, TypeError):
        memorandum_file_key = dpath.get(filing, '/alteration/memorandumFileKey')
        rules_and_memorandum.update_memorandum(business, filing_submission, memorandum_file_key)
