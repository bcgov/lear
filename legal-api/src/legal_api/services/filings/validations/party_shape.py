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
"""Normalize relationships-shaped party filings so the legacy parties validators run unchanged.

Filings in PARTY_SHAPE_FILING_TYPES may submit ``parties`` or ``relationships``. The validation
entry point converts relationships into a ``parties`` copy for the existing validators, runs the
relationship-only checks on the submitted shape, and rewrites error paths back to the
relationships shape so the caller sees paths that match what it sent.
"""
import copy
from http import HTTPStatus

from business_common.utils.relationship_party import (
    PARTIES_KEY,
    RELATIONSHIPS_KEY,
    get_parties,
    has_both_party_shapes,
    party_key,
)
from legal_api.errors import Error
from legal_api.services.filings.validations.common_validations import validate_relationship_entity_name

# Ordered: specific officer fields first, then the generic officer -> entity prefix.
OFFICER_PATH_REWRITES = (
    ("/officer/firstName", "/entity/givenName"),
    ("/officer/lastName", "/entity/familyName"),
    ("/officer/organizationName", "/entity/businessName"),
    ("/officer/identifier", "/entity/businessIdentifier"),
    ("/officer/middleName", "/entity/additionalName"),
    ("/officer/", "/entity/"),
)


def submitted_party_key(filing_json: dict, filing_type: str) -> str | None:
    """Return the party array key the filing submitted, or None."""
    return party_key(filing_json["filing"].get(filing_type) or {})


def normalize_party_shape(filing_json: dict, filing_type: str) -> tuple[dict, Error | None]:
    """Return the filing with relationships converted into parties, or a 400 when both shapes are present."""
    section = filing_json["filing"].get(filing_type) or {}
    if has_both_party_shapes(section):
        return filing_json, Error(HTTPStatus.BAD_REQUEST, [{
            "error": "Provide either parties or relationships, not both.",
            "path": f"/filing/{filing_type}/{RELATIONSHIPS_KEY}"
        }])
    if party_key(section) != RELATIONSHIPS_KEY:
        return filing_json, None

    normalized = copy.deepcopy(filing_json)
    normalized["filing"][filing_type][PARTIES_KEY] = get_parties(section)
    return normalized, None


def validate_relationship_items(filing_json: dict, filing_type: str) -> list:
    """Validate the relationship-only rules on the submitted shape.

    Every role needs an appointmentDate (the legacy party role schema required it and the filer
    reads it by key), and the entity name fields must match the entity type.
    """
    msg = []
    relationships_path = f"/filing/{filing_type}/{RELATIONSHIPS_KEY}"
    relationships = filing_json["filing"].get(filing_type, {}).get(RELATIONSHIPS_KEY) or []
    for index, relationship in enumerate(relationships):
        path = f"{relationships_path}/{index}"
        for role_index, role in enumerate(relationship.get("roles") or []):
            if not role.get("appointmentDate"):
                msg.append({"error": "appointmentDate is required.",
                            "path": f"{path}/roles/{role_index}/appointmentDate"})
        msg.extend(validate_relationship_entity_name(relationship, path))
    return msg


def rewrite_party_error_paths(msg: list, filing_type: str) -> list:
    """Rewrite legacy parties error paths in place to the relationships shape."""
    parties_path = f"/filing/{filing_type}/{PARTIES_KEY}"
    relationships_path = f"/filing/{filing_type}/{RELATIONSHIPS_KEY}"
    for err in msg:
        path = err.get("path")
        if not isinstance(path, str) or not path.startswith(parties_path):
            continue
        remainder = path[len(parties_path):]
        if remainder and not remainder.startswith("/"):
            continue
        path = relationships_path + remainder
        for legacy, relationship in OFFICER_PATH_REWRITES:
            path = path.replace(legacy, relationship)
        err["path"] = path
    return msg
