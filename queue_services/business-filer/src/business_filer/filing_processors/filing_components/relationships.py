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
"""Manages the parties and party role filing processing using the relationships schema."""
from __future__ import annotations

from datetime import datetime

from business_model.models import Address, Business, Filing, Party, PartyRole

from business_filer.filing_processors.filing_components import create_address, create_party, create_role, update_address



RELATIONSHIP_ROLE_CONVERTER = {
    "custodian": PartyRole.RoleTypes.CUSTODIAN.value,
    "completing party": PartyRole.RoleTypes.COMPLETING_PARTY.value,
    "director": PartyRole.RoleTypes.DIRECTOR.value,
    "incorporator": PartyRole.RoleTypes.INCORPORATOR.value,
    "proprietor": PartyRole.RoleTypes.PROPRIETOR.value,
    "partner": PartyRole.RoleTypes.PARTNER.value,
    "applicant": PartyRole.RoleTypes.APPLICANT.value,
    "receiver": PartyRole.RoleTypes.RECEIVER.value,
    # below is for role class officer
    "ceo": PartyRole.RoleTypes.CEO,
    "cfo": PartyRole.RoleTypes.CFO,
    "president": PartyRole.RoleTypes.PRESIDENT,
    "vice president": PartyRole.RoleTypes.VICE_PRESIDENT,
    "chair": PartyRole.RoleTypes.CHAIR,
    "treasurer": PartyRole.RoleTypes.TREASURER,
    "secretary": PartyRole.RoleTypes.SECRETARY,
    "assistant secretary": PartyRole.RoleTypes.ASSISTANT_SECRETARY,
    "other": PartyRole.RoleTypes.OTHER,
}


def _create_party(entity: dict):
    """Create a new party."""
    org_name = _str_to_upper(entity.get("businessName", ""))
    party_type = Party.PartyTypes.ORGANIZATION.value if org_name else Party.PartyTypes.PERSON.value
    party = Party(
        first_name=_str_to_upper(entity.get("givenName", "")),
        last_name=_str_to_upper(entity.get("familyName", "")),
        middle_initial=_str_to_upper(entity.get("middleInitial", "")),
        alternate_name=_str_to_upper(entity.get("alternateName", "")),
        organization_name=org_name,
        email=_str_to_upper(entity.get("email", "")),
        identifier=entity.get("businessIdentifier", ""),
        party_type=party_type
    )

    # add addresses to party
    if entity.get("deliveryAddress"):
        address = create_address(entity["deliveryAddress"], Address.DELIVERY)
        party.delivery_address = address
    if entity.get("mailingAddress"):
        mailing_address = create_address(entity["mailingAddress"], Address.MAILING)
        party.mailing_address = mailing_address

    return party


def _create_role(party: Party, role_info: dict) -> PartyRole:
    """Create a new party role and link to party."""
    party_role = PartyRole(
        role=RELATIONSHIP_ROLE_CONVERTER.get(role_info.get("roleType").lower(), ""),
        appointment_date=role_info["appointmentDate"],
        cessation_date=role_info["cessationDate"],
        party=party
    )
    return party_role


def _str_to_int(str: str | None) -> str | None:
    if str:
        try:
            return int(str)
        except (ValueError, TypeError):
            return None
    return None


def _str_to_upper(str: str | None) -> str:
    if str:
        return str.strip().upper()
    return None


def create_relationsips(relationships: list[dict], business: Business, filing: Filing) -> list | None:
    """Create new the party and party roles for a business.

    Assumption: The structure has already been validated, upon submission.

    Other errors are recorded and will be managed out of band.
    """
    err = []

    if relationships:
        try:
            for relationship_info in relationships:
                party = _create_party(entity=relationship_info.get("entity"))
                for role_type in relationship_info.get("roles"):
                    role_str = role_type.get("roleType", "").lower()
                    role = {
                        "roleType": role_str,
                        "appointmentDate": role_type.get("appointmentDate", None) or filing.effective_date,
                        "cessationDate": role_type.get("cessationDate", None)
                    }
                    party_role = _create_role(party=party, role_info=role)
                    if party_role.role in [PartyRole.RoleTypes.COMPLETING_PARTY.value,
                                           PartyRole.RoleTypes.INCORPORATOR.value,
                                           PartyRole.RoleTypes.APPLICANT.value]:
                        filing.filing_party_roles.append(party_role)
                    else:
                        business.party_roles.append(party_role)
        except KeyError:
            err.append(
                {"error_code": "FILER_UNABLE_TO_SAVE_PARTIES",
                 "error_message": f"Filer: unable to save new parties for :'{business.identifier}'"}
            )
    return err


def cease_relationships(
    relationships: dict,
    business: Business,
    role: PartyRole.RoleTypes,
    date_time = datetime.datetime.now(datetime.UTC)):
    """Cease the party role types for the given parties for a business.
    
    Assumption: The structure has already been validated, upon submission.
    """
    cease_party_ids = [
        _str_to_int(relationship["entity"]["identifier"])
        for relationship in relationships
        if relationship.get("entity", {}).get("identifier") is not None
    ]
    party_roles = PartyRole.get_party_roles(business.id, date_time.date(), role.value)
    for party_role in party_roles:
        if party_role.party_id in cease_party_ids:
            party_role.cessation_date = date_time


def update_relationship_addresses(relationships: list[dict]) -> None:
    """Update the relationship addresses for existing party relationships.
    
    Assumption: The structure has already been validated, upon submission.
    """
    for relationship in relationships:
        if (
            (existing_party_id := _str_to_int(party.get("entity", {}).get("identifier"))) and
            (party := Party.find_by_id(existing_party_id))
        ):
            if new_delivery_address := relationship.get("deliveryAddress"):
                if party.delivery_address:
                    party.delivery_address = update_address(party.delivery_address, new_delivery_address)
                else:
                    new_address = create_address(new_delivery_address, Address.DELIVERY)
                    party.delivery_address = new_address

            if new_mailing_address := relationship.get("mailingAddress"):
                if party.mailing_address:
                    party.mailing_address = update_address(party.mailing_address, new_mailing_address)
                else:
                    new_address = create_address(new_mailing_address, Address.MAILING)
                    party.mailing_address = new_address


def update_entity_info(entities: list[dict]) -> None:
    """Update the party info for existing parties.
    
    Assumption: The structure has already been validated, upon submission.
    """
    for entity in entities:
        if (
            (existing_party_id := _str_to_int(entity.get("identifier"))) and
            (party := Party.find_by_id(existing_party_id))
        ):
            party.first_name=_str_to_upper(entity.get("givenName", "")),
            party.last_name=_str_to_upper(entity.get("familyName", "")),
            party.middle_initial=_str_to_upper(entity.get("middleInitial", "")),
            party.alternate_name=_str_to_upper(entity.get("alternateName", "")),
            party.organization_name=_str_to_upper(entity.get("businessName", "")),
            party.identifier=_str_to_upper(entity.get("businessIdentifier", "")),
            party.email=_str_to_upper(entity.get("email", "")),
            