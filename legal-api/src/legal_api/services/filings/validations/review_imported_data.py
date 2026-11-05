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
import re
from datetime import UTC, datetime
from http import HTTPStatus

from flask_babel import _ as babel

from business_model.models import Address, Business, Party, PartyRole
from legal_api.errors import Error
from legal_api.services.filings.validations.common_validations import (
    validate_offices,
    validate_parties_addresses,
    validate_parties_countries,
)
from legal_api.services.warnings.business.business_checks import BusinessWarningReferers
from legal_api.services.warnings.business.business_checks.corps import check_address_data

# filing address json field -> Address model attribute
ADDRESS_JSON_FIELDS = {
    "streetAddress": "street",
    "streetAddressAdditional": "street_additional",
    "addressCity": "city",
    "addressRegion": "region",
    "addressCountry": "country",
    "postalCode": "postal_code",
    "deliveryInstructions": "delivery_instructions",
}


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
                bc_req=True,
            )
        )
        msg.extend(validate_office_address_changes(business, imported_data))

    if filing_data.get("relationships"):
        msg.extend(validate_relationship_addresses(imported_data))
        msg.extend(validate_active_directors(business, imported_data))
        msg.extend(validate_relationship_address_changes(business, imported_data))

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


def validate_office_address_changes(business: Business, imported_data: dict) -> list:
    """Only the office address fields the business warnings flag as missing or invalid may change."""
    referers = {
        "registeredOffice": BusinessWarningReferers.REGISTERED_OFFICE,
        "recordsOffice": BusinessWarningReferers.RECORDS_OFFICE,
    }
    filing_type = "reviewImportedData"
    msg = []
    offices = imported_data["filing"][filing_type]["offices"]

    for office_type, referer in referers.items():
        if not (submitted := offices.get(office_type)):
            continue
        # an office with no record at all is entered from scratch, so every field may be set
        office = business.offices.filter_by(office_type=office_type, deactivated_date=None).first()
        addresses = office.addresses.all() if office else []
        for json_type, address_type in ((Address.JSON_MAILING, Address.MAILING),
                                        (Address.JSON_DELIVERY, Address.DELIVERY)):
            if json_type not in submitted:
                continue
            existing = next((x for x in addresses if x.address_type == address_type), None)
            msg.extend(_validate_address_changes(
                submitted[json_type], existing, address_type, referer,
                f"/filing/{filing_type}/offices/{office_type}/{json_type}"))

    return msg


def validate_relationship_address_changes(business: Business, imported_data: dict) -> list:
    """Only the director address fields the business warnings flag as missing or invalid may change."""
    filing_type = "reviewImportedData"
    msg = []
    relationships = imported_data["filing"][filing_type]["relationships"]

    for index, relationship in enumerate(relationships):
        identifier = str(relationship.get("entity", {}).get("identifier") or "")
        # unknown identifiers are rejected by validate_active_directors
        party = Party.find_by_id(int(identifier)) if identifier.isdigit() else None
        if not party or party.id not in {
            role.party_id for role in business.party_roles.filter(PartyRole.cessation_date.is_(None))
        }:
            continue
        for json_type, address_type, existing in (
            (Address.JSON_MAILING, Address.MAILING, party.mailing_address),
            (Address.JSON_DELIVERY, Address.DELIVERY, party.delivery_address),
        ):
            if json_type not in relationship:
                continue
            msg.extend(_validate_address_changes(
                relationship[json_type], existing, address_type, BusinessWarningReferers.DIRECTOR,
                f"/filing/{filing_type}/relationships/{index}/{json_type}"))

    return msg


def _validate_address_changes(submitted: dict, existing: Address, address_type: str,
                              referer: BusinessWarningReferers, path: str) -> list:
    """Mirror the UI's locked address form: only flagged fields may change, an editable delivery street is no PO Box."""
    po_box = re.compile(r"\b(?:p\.?\s*o\.?|post\s+office)\s*box\b", re.IGNORECASE)
    editable = _get_editable_address_fields(existing, address_type, referer)
    msg = []

    if (address_type == Address.DELIVERY and "streetAddress" in editable
            and po_box.search(submitted.get("streetAddress") or "")):
        msg.append({"error": "Address cannot be a PO Box.", "path": f"{path}/streetAddress"})

    for json_field, attribute in ADDRESS_JSON_FIELDS.items():
        if json_field in editable:
            continue
        if _normalize(json_field, submitted.get(json_field)) != _normalize(json_field, getattr(existing, attribute)):
            msg.append({"error": "Only fields flagged as missing or invalid can be changed.",
                        "path": f"{path}/{json_field}"})

    return msg


def _get_editable_address_fields(existing: Address, address_type: str, referer: BusinessWarningReferers) -> set:
    """Return the json fields of an address the filing may change: the ones flagged as missing or invalid."""
    flagged_fields = {
        "_STREET": "streetAddress",
        "_CITY": "addressCity",
        "_COUNTRY": "addressCountry",
        "_POSTAL_CODE": "postalCode",
        "_REGION": "addressRegion",
    }
    # an address with no record at all is entered from scratch, so every field may be set
    if not existing:
        return set(ADDRESS_JSON_FIELDS)

    editable = set()
    for warning in check_address_data(existing, address_type, referer):
        code = str(getattr(warning["code"], "value", warning["code"]))
        editable.update(field for suffix, field in flagged_fields.items() if code.endswith(suffix))
    # what is valid for the region and postal code depends on the country entered
    if "addressCountry" in editable:
        editable.update(("addressRegion", "postalCode"))
    return editable


def _normalize(json_field: str, value: str | None) -> str:
    """Return a value for comparison; the UI reformats an untouched postal code (v1q2w4 -> V1Q 2W4, a 9 digit zip)."""
    value = value or ""
    if json_field == "postalCode":
        return re.sub(r"[\s-]", "", value).upper()
    return value
