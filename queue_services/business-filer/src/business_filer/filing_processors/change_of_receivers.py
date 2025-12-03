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

from business_model.models import Business, Filing, PartyRole

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components.relationships import cease_relationships, create_relationsips, update_entity_info, update_relationship_addresses


def process(business: Business, filing: dict, filing_rec: Filing, filing_meta: FilingMeta):
    """Render the changeOfReceivers onto the business model objects."""
    ammend_receiver_filing = filing.get("changeOfReceivers", {}).get("ammendReceiver", {})
    appoint_receiver_filing = filing.get("changeOfReceivers", {}).get("appointReceiver", {})
    cease_receiver_filing = filing.get("changeOfReceivers", {}).get("ceaseReceiver", {})
    change_address_receiver_filing = filing.get("changeOfReceivers", {}).get("changeAddressReceiver", {})

    # TODO: maybe need to db.session.add parties?
    if ammend_parties := ammend_receiver_filing.get("relationships"):
        appointed_parties = [party for party in ammend_parties if "ADDED" in party["actions"]]
        ceased_parties = [party for party in ammend_parties if "REMOVED" in party["actions"]]
        change_address_parties = [party for party in ammend_parties if "ADDRESS_CHANGED" in party["actions"]]
        info_changed_entities = [party["entity"] for party in ammend_parties
                                      if any(action in party["actions"] for action in ["EMAIL_CHANGED", "NAME_CHANGED"])]

        create_relationsips(appointed_parties, business, filing_rec)
        cease_relationships(ceased_parties, business, PartyRole.RoleTypes.RECEIVER, filing_meta.application_date)
        update_relationship_addresses(change_address_parties)
        update_entity_info(info_changed_entities)

    if appointed_parties := appoint_receiver_filing.get("relationships"):
        create_relationsips(appointed_parties, business, filing_rec)
    
    if ceased_parties := cease_receiver_filing.get("relationships"):
        cease_relationships(ceased_parties, business, PartyRole.RoleTypes.RECEIVER, filing_meta.application_date)
    
    if change_address_parties := change_address_receiver_filing.get("relationships"):
        update_relationship_addresses(change_address_parties)
