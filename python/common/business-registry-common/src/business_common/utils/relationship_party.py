# Copyright © 2026 Province of British Columbia
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
"""Convert relationship items to the legacy party shape for filings that accept both.

Filings in PARTY_SHAPE_FILING_TYPES may submit either a legacy ``parties`` array or a
``relationships`` array. The stored filing keeps the submitted shape; each legacy consumer
(validators, reports, COLIN sync, filer, emailer) calls ``get_parties`` at its read boundary
so its existing party code path is reused unchanged.
"""

from __future__ import annotations

import copy

# Filings whose party consumers normalize relationships -> parties. Widen one filing at a time.
PARTY_SHAPE_FILING_TYPES = frozenset({"continuationIn"})
# Subset of the above that is synced to COLIN (colin-api only reads the legacy parties shape).
COLIN_PARTY_SHAPE_FILING_TYPES = frozenset({"continuationIn"})

RELATIONSHIPS_KEY = "relationships"
PARTIES_KEY = "parties"


def party_key(filing_section: dict) -> str | None:
    """Return which party array key the filing section carries."""
    if PARTIES_KEY in filing_section:
        return PARTIES_KEY
    if RELATIONSHIPS_KEY in filing_section:
        return RELATIONSHIPS_KEY
    return None


def has_both_party_shapes(filing_section: dict) -> bool:
    """Return True if the filing section carries both parties and relationships."""
    return PARTIES_KEY in filing_section and RELATIONSHIPS_KEY in filing_section


def _officer_id(entity: dict) -> int | str | None:
    """Return the entity identifier as an int party id where possible; empty means absent."""
    identifier = entity.get("identifier")
    if identifier in (None, ""):
        return None
    try:
        return int(identifier)
    except (ValueError, TypeError):
        return identifier


def entity_to_officer(entity: dict) -> dict:
    """Map a relationship entity to a legacy officer dict."""
    organization_name = entity.get("businessName")
    officer = {
        "firstName": entity.get("givenName") or "",
        "middleInitial": entity.get("middleInitial") or "",
        "lastName": entity.get("familyName") or "",
        "partyType": "organization" if organization_name else "person",
    }
    if organization_name:
        officer["organizationName"] = organization_name
    if (officer_id := _officer_id(entity)) is not None:
        officer["id"] = officer_id
    # legacy officer.identifier is the business number; entity.identifier is the party id
    for entity_field, officer_field in (
        ("additionalName", "middleName"),
        ("alternateName", "alternateName"),
        ("email", "email"),
        ("businessIdentifier", "identifier"),
    ):
        if value := entity.get(entity_field):
            officer[officer_field] = value
    return officer


def relationship_to_party(relationship: dict) -> dict:
    """Convert a relationship item to a legacy party dict."""
    party = {
        "officer": entity_to_officer(relationship.get("entity", {})),
        "roles": [
            {
                "roleType": role.get("roleType"),
                "appointmentDate": role.get("appointmentDate"),
                "cessationDate": role.get("cessationDate"),
            }
            for role in relationship.get("roles", [])
        ],
    }
    for address_key in ("deliveryAddress", "mailingAddress"):
        if address := relationship.get(address_key):
            party[address_key] = copy.deepcopy(address)
    return party


def get_parties(filing_section: dict) -> list[dict]:
    """Return the section's parties in the legacy shape regardless of submitted shape."""
    if PARTIES_KEY in filing_section:
        return filing_section.get(PARTIES_KEY) or []
    return [relationship_to_party(relationship) for relationship in filing_section.get(RELATIONSHIPS_KEY) or []]
