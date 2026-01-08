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

import datetime

from business_model.models import Address, Business, Filing, Party, PartyRole, db
from business_model.models.types.party_class_type import PartyClassType

from business_filer.filing_processors.filing_components import create_address, update_address
from business_filer.common.legislation_datetime import LegislationDatetime

RELATIONSHIP_ROLE_CONVERTER = {
    "custodian": PartyRole.RoleTypes.CUSTODIAN.value,
    "completing party": PartyRole.RoleTypes.COMPLETING_PARTY.value,
    "director": PartyRole.RoleTypes.DIRECTOR.value,
    "incorporator": PartyRole.RoleTypes.INCORPORATOR.value,
    "liquidator": PartyRole.RoleTypes.LIQUIDATOR.value,
    "proprietor": PartyRole.RoleTypes.PROPRIETOR.value,
    "partner": PartyRole.RoleTypes.PARTNER.value,
    "applicant": PartyRole.RoleTypes.APPLICANT.value,
    "receiver": PartyRole.RoleTypes.RECEIVER.value,
    # below is for role class officer
    "ceo": PartyRole.RoleTypes.CEO.value,
    "cfo": PartyRole.RoleTypes.CFO.value,
    "president": PartyRole.RoleTypes.PRESIDENT.value,
    "vice president": PartyRole.RoleTypes.VICE_PRESIDENT.value,
    "chair": PartyRole.RoleTypes.CHAIR.value,
    "treasurer": PartyRole.RoleTypes.TREASURER.value,
    "secretary": PartyRole.RoleTypes.SECRETARY.value,
    "assistant secretary": PartyRole.RoleTypes.ASSISTANT_SECRETARY.value,
    "other": PartyRole.RoleTypes.OTHER.value,
}


def _create_party(relationship: dict):
    """Create a new party."""
    entity = relationship.get("entity", {})
    org_name = _str_to_upper(entity.get("businessName", ""))
    party_type = Party.PartyTypes.ORGANIZATION.value if org_name else Party.PartyTypes.PERSON.value
    party = party = Party(
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
    if relationship.get("deliveryAddress"):
        address = create_address(relationship["deliveryAddress"], Address.DELIVERY)
        party.delivery_address = address
    if relationship.get("mailingAddress"):
        mailing_address = create_address(relationship["mailingAddress"], Address.MAILING)
        party.mailing_address = mailing_address

    db.session.add(party)
    return party


def _create_role(party: Party,
                 role_info: dict,
                 default_appointment: datetime.datetime,
                 role_class: PartyClassType | None) -> PartyRole:
    """Create a new party role and link to party."""
    # FUTURE: use appointmentDate instead of default when given (api validation needs to be updated first for officers, receivers, liquidators)
    appointment_date = default_appointment or (
        LegislationDatetime.as_utc_timezone_from_legislation_date_str(role_info.get["appointmentDate"])
        if role_info.get("appointmentDate")
        else None
    )
    cessation_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(role_info.get["cessationDate"]) if role_info.get("cessationDate") else None
    party_role = PartyRole(
        role=RELATIONSHIP_ROLE_CONVERTER.get(role_info.get("roleType").lower(), ""),
        appointment_date=appointment_date,
        cessation_date=cessation_date,
        party=party
    )
    if role_class:
        party_role.party_class_type = role_class

    return party_role


def _str_to_int(str: str | None) -> int | None:
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


def create_relationsips(relationships: list[dict],
                        business: Business,
                        filing: Filing,
                        role_class: PartyClassType | None = None) -> list | None:
    """Create new party and party roles for a business.

    Assumption: The structure has already been validated, upon submission.

    Other errors are recorded and will be managed out of band.
    Relationships with existing records will be ignored.
    """
    err = []

    # Only create new records for relationships without an existing id
    if relationships:
        try:
            for relationship_info in relationships:
                party_id = _str_to_int(relationship_info.get("entity", {}).get("identifier"))
                party = Party.find_by_id(party_id) if party_id else None
                if not party:
                    party = _create_party(relationship_info)

                party_roles: list[PartyRole] = PartyRole.get_party_roles_by_party_id(business.id, party.id)
                # FUTURE: rely on api validation to check existing party is allowed to be updated instead of ignoring the update here
                if not party_roles and party_id:
                    # ignore updates
                    continue

                active_party_role_types = [party_role.role for party_role in party_roles if party_role.cessation_date is None]
                for role_info in relationship_info.get("roles", []):
                    role_type = RELATIONSHIP_ROLE_CONVERTER.get(role_info.get("roleType", "").lower(), "")
                    if role_type not in active_party_role_types and not role_info.get("cessationDate"):
                        party_role = _create_role(party=party,
                                                  role_info=role_info,
                                                  default_appointment=filing.effective_date,
                                                  role_class=role_class)
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
    allowed_roles: list[str],
    date_time: datetime.datetime | None = None):
    """Cease the party role types for the given parties for a business.
    
    Assumption: The structure has already been validated, upon submission.
    """
    date_time = date_time or datetime.datetime.now(datetime.UTC)

    def has_ceased_role(roles: list[dict], role: str):
        return any(
            ceased_role for ceased_role in roles
            if RELATIONSHIP_ROLE_CONVERTER.get(ceased_role.get("roleType", "").lower(), "") == role and
            ceased_role.get("cessationDate")
        )
    
    existing_relationships = [
        relationship
        for relationship in relationships
        if relationship.get("entity", {}).get("identifier") is not None
    ]
    for relationship in existing_relationships:
        party_id = _str_to_int(_str_to_int(relationship["entity"]["identifier"]))
        party_roles: list[PartyRole] = PartyRole.get_party_roles_by_party_id(business.id, party_id)

        for party_role in party_roles:
            if (party_role.role in allowed_roles
                and has_ceased_role(relationship.get("roles", []), party_role.role)
                and not party_role.cessation_date
            ):
                party_role.cessation_date = date_time


def update_relationship_addresses(relationships: list[dict], business: Business) -> None:
    """Update the relationship addresses for existing party relationships.
    
    Assumption: The structure has already been validated, upon submission.
    """
    for relationship in relationships:
        if (
            (existing_party_id := _str_to_int(relationship.get("entity", {}).get("identifier"))) and
            (party := Party.find_by_id(existing_party_id)) and
            # FUTURE: rely on api validation to check party is allowed to be updated instead of ignoring the update here
            PartyRole.get_party_roles_by_party_id(business.id, party.id)
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


def update_relationship_entity_info(relationships: list[dict], business: Business) -> None:
    """Update the party info for existing relationships.
    
    Assumption: The structure has already been validated, upon submission.
    """
    for relationship in relationships:
        if (
            (existing_party_id := _str_to_int(relationship.get("entity", {}).get("identifier"))) and
            (party := Party.find_by_id(existing_party_id)) and
            # FUTURE: rely on api validation to check party is allowed to be updated instead of ignoring the update here
            PartyRole.get_party_roles_by_party_id(business.id, party.id)
        ):
            org_name = _str_to_upper(relationship["entity"].get("businessName", ""))
            party_type = Party.PartyTypes.ORGANIZATION.value if org_name else Party.PartyTypes.PERSON.value
            party.first_name=_str_to_upper(relationship["entity"].get("givenName", ""))
            party.last_name=_str_to_upper(relationship["entity"].get("familyName", ""))
            party.middle_initial=_str_to_upper(relationship["entity"].get("middleInitial", ""))
            party.alternate_name=_str_to_upper(relationship["entity"].get("alternateName", ""))
            party.organization_name=org_name
            party.identifier=_str_to_upper(relationship["entity"].get("businessIdentifier", ""))
            party.email=_str_to_upper(relationship["entity"].get("email", ""))
            party.party_type=party_type
            