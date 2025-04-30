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
"""File processing rules and actions for the change of registration filing."""
import datetime
from contextlib import suppress

import dpath
from business_model.models import Address, Business, Filing, Party, PartyRole

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import (
    business_info,
    create_address,
    create_party,
    create_role,
    filings,
    update_address,
)


def process(business: Business, change_filing_rec: Filing, change_filing: dict, filing_meta: FilingMeta):
    """Render the change of registration filing onto the business model objects."""
    filing_meta.change_of_registration = {}
    # Update business legalName if present
    with suppress(IndexError, KeyError, TypeError):
        name_request_json = dpath.get(change_filing, "/changeOfRegistration/nameRequest")
        if name_request_json.get("legalName"):
            from_legal_name = business.legal_name
            business_info.set_legal_name(business.identifier, business, name_request_json)
            if from_legal_name != business.legal_name:
                filing_meta.change_of_registration = {**filing_meta.change_of_registration,
                                                      "fromLegalName": from_legal_name,
                                                         "toLegalName": business.legal_name}
    # Update Nature of Business
    if (((naics := change_filing.get("changeOfRegistration", {}).get("business", {}).get("naics"))
          and
          (naics_code := naics.get("naicsCode")))
              and
              business.naics_code != naics_code):
            filing_meta.change_of_registration = {**filing_meta.change_of_registration,
                                                  "fromNaicsCode": business.naics_code,
                                                     "toNaicsCode": naics_code,
                                                     "naicsDescription": naics.get("naicsDescription")}
            business_info.update_naics_info(business, naics)

    # Update business office if present
    with suppress(IndexError, KeyError, TypeError):
        business_office_json = dpath.get(change_filing, "/changeOfRegistration/offices/businessOffice")
        for updated_address in business_office_json.values():
            if updated_address.get("id", None):
                address = Address.find_by_id(updated_address.get("id"))
                if address:
                    update_address(address, updated_address)

    # Update parties
    with suppress(IndexError, KeyError, TypeError):
        party_json = dpath.get(change_filing, "/changeOfRegistration/parties")
        update_parties(business, party_json, change_filing_rec)

    # update court order, if any is present
    with suppress(IndexError, KeyError, TypeError):
        court_order_json = dpath.get(change_filing, "/changeOfRegistration/courtOrder")
        filings.update_filing_court_order(change_filing_rec, court_order_json)


def update_parties(business: Business, parties: dict, change_filing_rec: Filing):
    """Create a new party or get them if they already exist."""
    # Cease the party roles not present in the edit request
    end_date_time = datetime.datetime.now(datetime.UTC)
    parties_to_update = [party.get("officer").get("id") for party in parties if
                         party.get("officer").get("id") is not None]
    existing_party_roles = PartyRole.get_party_roles(business.id, end_date_time.date())
    for party_role in existing_party_roles:
        if party_role.party_id not in parties_to_update:
            party_role.cessation_date = end_date_time

    # Create and Update
    for party_info in parties:
        # Create if id not present
        # If id is present and is a GUID then this is an id specific to the UI which is not relevant to the backend.
        # The backend will have an id of type int
        if not party_info.get("officer").get("id") or \
                (party_info.get("officer").get("id") and not isinstance(party_info.get("officer").get("id"), int)):
            _create_party_info(business, change_filing_rec, party_info)
        else:
            # Update if id is present
            _update_party(party_info)


def _update_party(party_info):
    party = Party.find_by_id(party_id=party_info.get("officer").get("id"))
    if party:
        party.first_name = party_info["officer"].get("firstName", "").upper()
        party.last_name = party_info["officer"].get("lastName", "").upper()
        party.middle_initial = party_info["officer"].get("middleName", "").upper()
        party.title = party_info.get("title", "").upper()
        party.organization_name = party_info["officer"].get("organizationName", "").upper()
        party.party_type = party_info["officer"].get("partyType")
        party.email = party_info["officer"].get("email", "").lower()
        party.identifier = party_info["officer"].get("identifier", "").upper()

        # add addresses to party
        if party_info.get("deliveryAddress", None):
            if party.delivery_address:
                update_address(party.delivery_address, party_info.get("deliveryAddress"))
            else:
                address = create_address(party_info["deliveryAddress"], Address.DELIVERY)
                party.delivery_address = address
        if party_info.get("mailingAddress", None):
            if party.mailing_address:
                update_address(party.mailing_address, party_info.get("mailingAddress"))
            else:
                mailing_address = create_address(party_info["mailingAddress"], Address.MAILING)
                party.mailing_address = mailing_address


def _create_party_info(business, change_filing_rec, party_info):
    party = create_party(business_id=business.id, party_info=party_info, create=False)
    for role_type in party_info.get("roles"):
        role_str = role_type.get("roleType", "").lower()
        role = {
            "roleType": role_str,
            "appointmentDate": role_type.get("appointmentDate", None),
            "cessationDate": role_type.get("cessationDate", None)
        }
        party_role = create_role(party=party, role_info=role)
        if party_role.role in [PartyRole.RoleTypes.COMPLETING_PARTY.value]:
            change_filing_rec.filing_party_roles.append(party_role)
        else:
            business.party_roles.append(party_role)
