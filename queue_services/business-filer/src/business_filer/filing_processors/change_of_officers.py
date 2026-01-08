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
"""File processing rules and actions for the change of directors."""
import copy
from datetime import UTC, datetime

from business_model.models import Address, Business, Filing, Party, PartyRole, db
from business_model.models.types.party_class_type import PartyClassType

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components.relationships import (
    cease_relationships,
    create_relationsips,
    update_relationship_addresses,
    update_relationship_entity_info,
)


def process(business: Business, filing_rec: Filing, filing_meta: FilingMeta):  # noqa: PLR0912
    """Render the change_of_officers onto the business model objects."""
    filing_json = copy.deepcopy(filing_rec.filing_json)
    relationships = filing_json["filing"]["changeOfOfficers"].get("relationships")
    create_relationsips(relationships, business, filing_rec, PartyClassType.OFFICER)
    update_relationship_entity_info(relationships, business)
    update_relationship_addresses(relationships, business)

    valid_officer_roles = [
        PartyRole.RoleTypes.CEO.value,
        PartyRole.RoleTypes.CFO.value,
        PartyRole.RoleTypes.PRESIDENT.value,
        PartyRole.RoleTypes.VICE_PRESIDENT.value,
        PartyRole.RoleTypes.CHAIR.value,
        PartyRole.RoleTypes.TREASURER.value,
        PartyRole.RoleTypes.SECRETARY.value,
        PartyRole.RoleTypes.ASSISTANT_SECRETARY.value,
        PartyRole.RoleTypes.OTHER.value,
    ]
    cease_relationships(relationships, business, valid_officer_roles, filing_meta.application_date)

#     # get list of submitted officers
#     if not (submitted_officers := filing_json["filing"]["changeOfOfficers"].get("relationships")):
#         return

#     # get all active officers to compare when updating parties
#     existing_officers = _group_current_officers_by_id(business.id) # { party_id: [PartyRole, PartyRole, ...] }

#     # loop through submitted officers and create or update Party, Address and PartyRole's
#     for officer in submitted_officers:
#         entity = officer.get("entity", {})
#         party_id = _str_to_int(entity.get("identifier"))

#         # update existing party and roles
#         if party_id:
#             # ignore this party id if it doesn't exist for this business
#             if party_id not in existing_officers:
#                 continue

#             party = Party.find_by_id(party_id)
#             # skip party if submitted id can't be found
#             if not party:
#                 continue
            
#             # update party fields
#             _update_party_fields(party, entity)

#             # update or create party addresses
#             _update_or_create_party_addresses(party, officer)
            
#             # update or create roles for party
#             current_party_roles = existing_officers.get(party_id, [])
#             for role in officer.get("roles", []):
#                 # check if role already exists
#                 role_enum = _get_role_enum(role)
#                 existing_role = next((pr for pr in current_party_roles if pr.role == role_enum.value), None)

#                 has_cessation_date = role.get("cessationDate") is not None
#                 if existing_role:
#                     # cease role if submitted with cessation date, else do not update the role
#                     if has_cessation_date:
#                         existing_role.cessation_date = filing_rec.effective_date        
#                 # create new role for party, ignore new roles submitted with a cessation date
#                 elif not has_cessation_date:
#                     _create_party_role(
#                         party,
#                         business.id,
#                         role_enum,
#                         filing_rec.effective_date
#                     )
#         # create new party and roles
#         else:
#             new_party = Party(
#                 first_name=_str_to_upper(entity.get("givenName", "")),
#                 last_name=_str_to_upper(entity.get("familyName", "")),
#                 middle_initial=_str_to_upper(entity.get("middleInitial", "")),
#                 alternate_name=_str_to_upper(entity.get("alternateName", ""))
#             )
#             db.session.add(new_party)

#             # create addresses for new party
#             if new_delivery_address := officer.get("deliveryAddress"):
#                 new_address = create_address(new_delivery_address, Address.DELIVERY)
#                 new_party.delivery_address = new_address
#                 db.session.add(new_address)
#             if new_mailing_address := officer.get("mailingAddress"):
#                 new_address = create_address(new_mailing_address, Address.MAILING)
#                 new_party.mailing_address = new_address
#                 db.session.add(new_address)

#             # create roles for new party
#             for role in officer.get("roles", []):
#                 # ignore roles submitted with cessation date
#                 if not role.get("cessationDate"):
#                     role_enum = _get_role_enum(role)
#                     _create_party_role(
#                         new_party,
#                         business.id,
#                         role_enum,
#                         filing_rec.effective_date
#                     )

# def _str_to_upper(str: str | None) -> str:
#     if str:
#         return str.strip().upper()
#     return None

# def _str_to_int(str: str | None) -> str | None:
#     # submitted identifier is a string, convert to int to match party id
#     if str:
#         try:
#             return int(str)
#         except (ValueError, TypeError):
#             return None
#     return None

# def _get_role_enum(role: dict) -> PartyRole.RoleTypes:
#     role_str = role.get("roleType", "").strip().lower()
#     role_enum = OFFICER_ROLE_CONVERTER.get(role_str)

#     return role_enum

# def _group_current_officers_by_id(business_id: int) -> dict[int, list[PartyRole]]:
#     end_date = datetime.now(UTC).date()
#     active_roles = PartyRole.get_party_roles_by_class_type(business_id, PartyClassType.OFFICER, end_date)
#     existing_officers: dict[int, list[PartyRole]] = {} # { party_id: [PartyRole, PartyRole, ...] }

#     # group roles by party id
#     for pr in active_roles:
#         if pr.party_id not in existing_officers:
#             existing_officers[pr.party_id] = []
#         existing_officers[pr.party_id].append(pr)

#     return existing_officers
