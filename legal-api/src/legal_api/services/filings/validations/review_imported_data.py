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
"""Validation for the Review Imported Data filing."""
from datetime import UTC, datetime
from http import HTTPStatus

from flask_babel import _ as babel

from business_model.models import Business, PartyRole
from legal_api.errors import Error
from legal_api.services.filings.validations.common_validations import (
    validate_offices,
    validate_parties_addresses,
    validate_parties_countries,
)


def validate(business: Business, imported_data: dict) -> Error:
    """Validate the Review Imported Data filing."""
    if not business or not imported_data:
        return Error(
            HTTPStatus.BAD_REQUEST,
            [{"error": babel("A valid business and filing are required.")}],
        )

    filing_type = "reviewImportedData"
    filing_data = imported_data["filing"][filing_type]
    msg = []

    if filing_data.get("offices"):
        msg.extend(
            validate_offices(
                imported_data,
                filing_type,
                allowed_types=["registeredOffice", "recordsOffice"],
                required_types=[],
                bc_req=False,
            )
        )

    if filing_data.get("relationships"):
        msg.extend(validate_relationship_addresses(imported_data))
        msg.extend(validate_active_directors(business, imported_data))

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)

    return None


def validate_relationship_addresses(imported_data: dict) -> list:
    """Validate director relationship addresses."""
    filing_type = "reviewImportedData"
    msg = []
    msg.extend(validate_parties_addresses(imported_data, filing_type, "relationships"))
    msg.extend(validate_parties_countries(imported_data, filing_type, "relationships"))
    return msg


def validate_active_directors(business: Business, imported_data: dict) -> list:
    """Ensure each relationship references an existing active director."""
    msg = []
    filing_type = "reviewImportedData"
    relationships = imported_data["filing"][filing_type]["relationships"]
    today = datetime.now(tz=UTC).date()

    party_roles = PartyRole.get_party_roles(
        business.id,
        today,
        PartyRole.RoleTypes.DIRECTOR.value,
    )
    active_party_ids = {str(party_role.party_id) for party_role in party_roles}

    for index, relationship in enumerate(relationships):
        identifier = relationship.get("entity", {}).get("identifier")
        if identifier and identifier not in active_party_ids:
            msg.append({
                "error": "Relationship with this identifier is not valid for this filing.",
                "path": (
                    f"/filing/{filing_type}/relationships/"
                    f"{index}/entity/identifier"
                ),
            })

    return msg
