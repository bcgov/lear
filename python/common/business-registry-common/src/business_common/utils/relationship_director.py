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
"""Convert changeOfDirectors relationship items to the legacy director shape."""
from __future__ import annotations

DIRECTOR_ROLE_TYPE = "director"

# Uppercase relationship actions (business-ui ActionType) -> legacy director actions.
# CHANGED intentionally has no mapping: it is an unspecific edit, handled by derivation.
RELATIONSHIP_ACTION_CONVERTER = {
    "ADDED": "appointed",
    "REMOVED": "ceased",
    "NAME_CHANGED": "nameChanged",
    "ADDRESS_CHANGED": "addressChanged",
}

FREE_ACTIONS = {"nameChanged", "addressChanged"}


def _director_role(relationship: dict) -> dict:
    """Return the relationship's Director role, or an empty dict."""
    return next(
        (
            role
            for role in relationship.get("roles", [])
            if (role.get("roleType") or "").lower() == DIRECTOR_ROLE_TYPE
        ),
        {},
    )


def _officer_id(relationship: dict) -> int | str | None:
    """Return the entity identifier as an int party id where possible."""
    identifier = relationship.get("entity", {}).get("identifier")
    if identifier is None:
        return None
    try:
        return int(identifier)
    except (ValueError, TypeError):
        return identifier


def map_relationship_actions(relationship: dict) -> list[str]:
    """Return legacy director actions for a relationship item."""
    if mapped := [
        RELATIONSHIP_ACTION_CONVERTER[action]
        for action in relationship.get("actions") or []
        if action in RELATIONSHIP_ACTION_CONVERTER
    ]:
        return mapped

    if _director_role(relationship).get("cessationDate"):
        return ["ceased"]
    if not relationship.get("entity", {}).get("identifier"):
        return ["appointed"]
    return []


def relationship_to_director(relationship: dict) -> dict:
    """Convert a relationship item to a legacy director dict.

    prevFirstName/prevMiddleInitial/prevLastName are never populated
    — relationships have no previous-name concept
    - consumers needing them (COLIN sync) enrich from versioned party revisions
    """
    entity = relationship.get("entity", {})
    organization_name = entity.get("businessName")

    officer = {
        "firstName": entity.get("givenName", ""),
        "middleInitial": entity.get("middleInitial", ""),
        "lastName": entity.get("familyName", ""),
        "partyType": "organization" if organization_name else "person",
    }
    if organization_name:
        officer["organizationName"] = organization_name
    if email := entity.get("email"):
        officer["email"] = email
    if (officer_id := _officer_id(relationship)) is not None:
        officer["id"] = officer_id

    director_role = _director_role(relationship)
    director = {
        "officer": officer,
        "appointmentDate": director_role.get("appointmentDate"),
        "cessationDate": director_role.get("cessationDate"),
        "actions": map_relationship_actions(relationship),
    }
    if delivery_address := relationship.get("deliveryAddress"):
        director["deliveryAddress"] = delivery_address
    if mailing_address := relationship.get("mailingAddress"):
        director["mailingAddress"] = mailing_address

    return director


def cod_directors(change_of_directors: dict) -> list[dict]:
    """Return the filing's directors in the legacy shape regardless of submitted shape."""
    if directors := change_of_directors.get("directors"):
        return directors
    if relationships := change_of_directors.get("relationships"):
        return [relationship_to_director(relationship) for relationship in relationships]
    return []


def is_change_free(director: dict) -> bool:
    """Return True if the director's changes qualify for the free filing code.

    Name and address edits are free; appointments and cessations are not.
    An empty actions list is an unspecified edit and counts as free.
    """
    return all(action in FREE_ACTIONS for action in director.get("actions") or [])
