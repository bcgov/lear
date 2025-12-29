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
"""File processing rules and actions for change of receivers filings."""
import copy

from business_model.models import Business, Filing, PartyRole

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components.filings import update_filing_court_order
from business_filer.filing_processors.filing_components.relationships import (
    cease_relationships,
    create_relationsips,
    update_relationship_addresses,
    update_relationship_entity_info,
)


def process(business: Business, filing_rec: Filing, filing_meta: FilingMeta):
    """Render the changeOfReceivers onto the business model objects."""
    filing_json = copy.deepcopy(filing_rec.filing_json)
    relationships = filing_json["filing"]["changeOfReceivers"].get("relationships")
    if filing_rec.filing_sub_type == "amendReceiver":
        create_relationsips(relationships, business, filing_rec)
        cease_relationships(relationships, business, PartyRole.RoleTypes.RECEIVER, filing_meta.application_date)
        update_relationship_addresses(relationships)
        update_relationship_entity_info(relationships)

    elif filing_rec.filing_sub_type == "appointReceiver":
        create_relationsips(relationships, business, filing_rec)
    
    elif filing_rec.filing_sub_type == "ceaseReceiver":
        cease_relationships(relationships, business, PartyRole.RoleTypes.RECEIVER, filing_meta.application_date)
    
    elif filing_rec.filing_sub_type == "changeAddressReceiver":
        update_relationship_addresses(relationships)

    # update court order, if any is present
    if court_order := filing_json["filing"]["changeOfReceivers"].get("courtOrder"):
        update_filing_court_order(filing_rec, court_order)
    
    # FUTURE: DRS integration with document id