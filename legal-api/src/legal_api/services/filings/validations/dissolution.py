# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Validation for the Voluntary Dissolution filing."""
from enum import Enum
from http import HTTPStatus
from typing import Final, Optional

import pycountry
from flask_babel import _

from legal_api.errors import Error
from legal_api.models import Address, Business, PartyRole
from legal_api.services import flags
from legal_api.services.filings.validations.common_validations import (
    validate_court_order,
    validate_effective_date,
    validate_parties_addresses,
    validate_pdf,
)
from legal_api.services.permissions import (
    ListActionsPermissionsAllowed,
    ListFilingsPermissionsAllowed,
    PermissionService,
)
from legal_api.services.utils import get_str  # noqa: I003; needed as the linter gets confused from the babel override.


class DissolutionTypes(str, Enum):
    """Dissolution types."""

    ADMINISTRATIVE = "administrative"
    COURT_ORDERED_LIQUIDATION = "courtOrderedLiquidation"
    DELAY = "delay"
    INVOLUNTARY = "involuntary"
    VOLUNTARY = "voluntary"
    VOLUNTARY_LIQUIDATION = "voluntaryLiquidation"


class DissolutionStatementTypes(str, Enum):
    """Dissolution statement types."""

    NO_ASSETS_NO_LIABILITIES_197 = "197NoAssetsNoLiabilities"
    NO_ASSETS_PROVISIONS_LIABILITIES_197 = "197NoAssetsProvisionsLiabilities"

    @classmethod
    def has_value(cls, value):
        """Check if enum contains specific value provided via input param."""
        return value in cls._value2member_map_  # pylint: disable=no-member


DISSOLUTION_MAPPING = {
    "COOP": [DissolutionTypes.VOLUNTARY, DissolutionTypes.VOLUNTARY_LIQUIDATION, DissolutionTypes.ADMINISTRATIVE, DissolutionTypes.DELAY],
    "CORP": [DissolutionTypes.VOLUNTARY, DissolutionTypes.ADMINISTRATIVE, DissolutionTypes.DELAY],
    "FIRMS": [DissolutionTypes.VOLUNTARY, DissolutionTypes.ADMINISTRATIVE]
}


def validate(business: Business, dissolution: dict) -> Optional[Error]:
    """Validate the dissolution filing."""
    if not business or not dissolution:
        return Error(HTTPStatus.BAD_REQUEST, [{"error": _("A valid business and filing are required.")}])

    filing_type = "dissolution"
    dissolution_type = get_str(dissolution, "/filing/dissolution/dissolutionType")
    msg = []

    if flags.is_on("enabled-deeper-permission-action"):
        if not business.good_standing:
            required_permission = ListActionsPermissionsAllowed.OVERRIDE_NIGS.value
            message = "Permission Denied - You do not have permissions send not in good standing business in this filing."
            error = PermissionService.check_user_permission(required_permission, message=message)
            return error
        
        err = _validate_dissolution_permission(business, dissolution_type, filing_type)
        if err:
            return err
        
    err = validate_dissolution_type(dissolution, business.legal_type)
    if err:
        msg.extend(err)

    err = validate_dissolution_details(dissolution)
    if err:
        msg.extend(err)

    err = validate_dissolution_statement_type(dissolution, business.legal_type, dissolution_type)
    if err:
        msg.extend(err)

    err = validate_dissolution_parties_roles(dissolution, business.legal_type, dissolution_type)
    if err:
        msg.extend(err)    

    # Specific validation for addresses in dissolution
    err = validate_dissolution_parties_address(dissolution, business.legal_type, dissolution_type)
    if err:
        msg.extend(err)

    if dissolution["filing"]["dissolution"].get("parties"):
        # Common validation for addresses
        msg.extend(validate_parties_addresses(dissolution, filing_type))

    err = validate_affidavit(dissolution, business.legal_type, dissolution_type)
    if err:
        msg.extend(err)


    msg.extend(_validate_court_order(dissolution))

    msg.extend(validate_effective_date(dissolution))

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def validate_dissolution_details(filing_json) -> Optional[list]:
    """Validate details for administrative dissolution."""
    msg = []
    dissolution_type_path = "/filing/dissolution/dissolutionType"
    dissolution_type = get_str(filing_json, dissolution_type_path)
    dissolution_details_path = "/filing/dissolution/details"
    dissolution_details = get_str(filing_json, dissolution_details_path)
    if dissolution_type and dissolution_type == DissolutionTypes.ADMINISTRATIVE.value and not dissolution_details:
        msg.append({"error": _("Administrative dissolution must have details"), "path": dissolution_details_path})
        return msg

    return None


def validate_dissolution_type(filing_json, legal_type) -> Optional[list]:
    """Validate dissolution type of the filing."""
    msg = []
    dissolution_type_path = "/filing/dissolution/dissolutionType"
    dissolution_type = get_str(filing_json, dissolution_type_path)
    if dissolution_type:
        # pylint: disable=too-many-boolean-expressions
        if (legal_type == Business.LegalTypes.COOP.value and dissolution_type not in DISSOLUTION_MAPPING["COOP"]) \
                or (legal_type in Business.CORPS and dissolution_type not in DISSOLUTION_MAPPING["CORP"]) \
                or (legal_type in (
                Business.LegalTypes.SOLE_PROP.value, Business.LegalTypes.PARTNERSHIP.value) and dissolution_type not in
                    DISSOLUTION_MAPPING["FIRMS"]):
            msg.append({"error": _("Invalid Dissolution type."), "path": dissolution_type_path})
            return msg
    else:
        msg.append({"error": _("Dissolution type must be provided."),
                    "path": dissolution_type_path})
        return msg

    return None


def validate_dissolution_statement_type(filing_json, legal_type, dissolution_type) -> Optional[list]:
    """Validate dissolution statement type of the filing.

    This needs not to be validated for administrative dissolution
    """
    if dissolution_type in [DissolutionTypes.ADMINISTRATIVE, DissolutionTypes.DELAY]:
        return None

    msg = []
    dissolution_stmt_type_path = "/filing/dissolution/dissolutionStatementType"
    dissolution_stmt_type = get_str(filing_json, dissolution_stmt_type_path)

    if legal_type == Business.LegalTypes.COOP.value:
        if not dissolution_stmt_type:
            msg.append({"error": _("Dissolution statement type must be provided."),
                        "path": dissolution_stmt_type_path})
            return msg
        if not DissolutionStatementTypes.has_value(dissolution_stmt_type):
            msg.append({"error": _("Invalid Dissolution statement type."),
                        "path": dissolution_stmt_type_path})
            return msg

    return None

def validate_dissolution_parties_roles(filing_json, legal_type, dissolution_type) -> Optional[list]: # noqa: PLR0912
    """Validate that all party roles in the dissolution are valid.

    This needs not to be validated for administrative dissolution
    """
    if dissolution_type in [DissolutionTypes.ADMINISTRATIVE, DissolutionTypes.DELAY]:
        return None

    if "parties" not in filing_json["filing"]["dissolution"]:
        return [{"error": "Parties are required.", "path": "/filing/dissolution/parties"}]

    parties_json = filing_json["filing"]["dissolution"]["parties"]
    party_path = "/filing/dissolution/parties"

    if legal_type in Business.CORPS:
        allowed_roles = {PartyRole.RoleTypes.CUSTODIAN.value}
    elif legal_type == Business.LegalTypes.COOP.value:
        allowed_roles = {PartyRole.RoleTypes.CUSTODIAN.value,
                         PartyRole.RoleTypes.LIQUIDATOR.value}
    elif legal_type in {Business.LegalTypes.SOLE_PROP.value, Business.LegalTypes.PARTNERSHIP.value}:
        allowed_roles = {PartyRole.RoleTypes.COMPLETING_PARTY.value}
    else:
        allowed_roles = set()

    msg = []
    custodian_count = 0
    liquidator_count = 0
    completing_party_count = 0
    invalid_roles = set()
    for party in parties_json:
        for role in party.get("roles", []):
            role_type = role.get("roleType").lower().replace(" ", "_")
            if role_type not in allowed_roles:
                invalid_roles.add(role_type)
                continue

            if role_type == PartyRole.RoleTypes.CUSTODIAN.value:
                custodian_count += 1
            elif role_type == PartyRole.RoleTypes.LIQUIDATOR.value:
                liquidator_count += 1
            elif role_type == PartyRole.RoleTypes.COMPLETING_PARTY.value:
                completing_party_count += 1

    if invalid_roles:
        msg.append({
            "error": f'Invalid party role(s) provided: {", ".join(sorted(invalid_roles))}.',
            "path": f"{party_path}/roles"
        })
    
    if legal_type in Business.CORPS:
        if custodian_count == 0:
            msg.append({"error": "Must have a minimum of one custodian.", "path": party_path})
        elif custodian_count > 1:
            msg.append({"error": "Must have a maximum of one custodian.", "path": party_path})    
    elif legal_type == Business.LegalTypes.COOP.value:
        total = custodian_count + liquidator_count
        if total == 0:
            msg.append({"error": "Must have a minimum of one custodian or one liquidator.", "path": party_path})
        elif total > 1:
            msg.append({"error": "Must have a maximum of one custodian or one liquidator, not both.", "path": party_path})
    elif (
        legal_type in {Business.LegalTypes.SOLE_PROP.value, Business.LegalTypes.PARTNERSHIP.value} and
        completing_party_count == 0
    ):
        msg.append({"error": "Must have a completing party.", "path": party_path})

    return msg

def validate_dissolution_parties_address(filing_json, legal_type, dissolution_type) -> Optional[list]:
    """Validate the person data of the dissolution filing.

    Address must be in Canada for COOP and BC for CORP.
    Both mailing and delivery address are mandatory.
    This needs not to be validated for SP and GP
    This needs not to be validated for administrative dissolution
    """
    if dissolution_type in [DissolutionTypes.ADMINISTRATIVE, DissolutionTypes.DELAY]:
        return None

    if legal_type in [Business.LegalTypes.SOLE_PROP.value, Business.LegalTypes.PARTNERSHIP.value]:
        return None
    
    if "parties" not in filing_json["filing"]["dissolution"]:
        return None

    parties_json = filing_json["filing"]["dissolution"]["parties"]
    parties = list(filter(lambda x: _is_dissolution_party_role(x.get("roles", [])), parties_json))
    msg = []
    address_in_bc = 0
    address_in_ca = 0
    party_path = "/filing/dissolution/parties"

    if len(parties) > 0:
        msg.extend(_validate_custodian_email(parties, dissolution_type, legal_type))
        msg.extend(validate_custodian_org_name(parties, dissolution_type, legal_type))

        err, address_in_bc, address_in_ca = _validate_address_location(parties)
        if err:
            msg.extend(err)
    else:
        msg.append({"error": "Dissolution party is required.", "path": party_path})

    if legal_type == Business.LegalTypes.COOP.value and address_in_ca == 0:
        msg.append({"error": "Address must be in Canada.", "path": party_path})
    elif legal_type in Business.CORPS and address_in_bc == 0:
        msg.append({"error": "Address must be in BC.", "path": party_path})

    if msg:
        return msg

    return None


def _is_dissolution_party_role(roles: list) -> bool:
    return any(role.get("roleType", "").lower() in
               [PartyRole.RoleTypes.CUSTODIAN.value,
                PartyRole.RoleTypes.LIQUIDATOR.value] for role in roles)


def _validate_address_location(parties):
    msg = []
    address_in_bc = 0
    address_in_ca = 0
    for idx, party in enumerate(parties):  # pylint: disable=too-many-nested-blocks;
        for address_type in Address.JSON_ADDRESS_TYPES:
            if address_type in party:
                try:
                    region = get_str(party, f"/{address_type}/addressRegion")
                    if region == "BC":
                        address_in_bc += 1

                    country = get_str(party, f"/{address_type}/addressCountry")
                    country_code = pycountry.countries.search_fuzzy(country)[0].alpha_2
                    if country_code == "CA":
                        address_in_ca += 1

                except LookupError:
                    msg.append({"error": _("Address Country must resolve to a valid ISO-2 country."),
                                "path": f"/filing/dissolution/parties/{idx}/{address_type}/addressCountry"})
            else:
                msg.append({"error": _(f"{address_type} is required."),
                            "path": f"/filing/dissolution/parties/{idx}"})

    if msg:
        return msg, address_in_bc, address_in_ca

    return None, address_in_bc, address_in_ca


def validate_affidavit(filing_json, legal_type, dissolution_type) -> Optional[list]:
    """Validate affidavit document of the filing.

    This needs not to be validated for administrative dissolution
    """
    if dissolution_type in [DissolutionTypes.ADMINISTRATIVE, DissolutionTypes.DELAY]:
        return None

    if legal_type == Business.LegalTypes.COOP.value:
        affidavit_file_key_path = "/filing/dissolution/affidavitFileKey"
        affidavit_file_key = get_str(filing_json, affidavit_file_key_path)

        # Validate key values exist
        if not affidavit_file_key:
            return [{"error": _("A valid affidavit key is required."),
                     "path": affidavit_file_key_path}]

        return validate_pdf(affidavit_file_key, affidavit_file_key_path)

    return None


def _validate_court_order(filing):
    """Validate court order."""
    if court_order := filing.get("filing", {}).get("dissolution", {}).get("courtOrder", None):
        court_order_path: Final = "/filing/dissolution/courtOrder"
        err = validate_court_order(court_order_path, court_order)
        if err:
            return err
    return []


def _validate_custodian_email(parties, dissolution_type, legal_type) -> list:
    """Validate custodian email for voluntary dissolution."""
    # Only validate for CORP voluntary dissolution
    if not (legal_type in Business.CORPS and dissolution_type == DissolutionTypes.VOLUNTARY.value):
        return []

    msg = []
    for idx, party in enumerate(parties):
        email = get_str(party, "/officer/email")
        if not email:
            msg.append({"error": "Custodian email is required for voluntary dissolution.",
                        "path": f"/filing/dissolution/parties/{idx}/officer/email"})
        elif any(char.isspace() for char in email):
            msg.append({
                "error": "Custodian email cannot contain any whitespaces.",
                "path": f"/filing/dissolution/parties/{idx}/officer/email"
            })    
    return msg

def validate_custodian_org_name(parties, dissolution_type, legal_type) -> list:
    """Validate custodian organization name of the dissolution filing and trim it."""
    # Only validate for CORP voluntary dissolution
    if not (legal_type in Business.CORPS and dissolution_type == DissolutionTypes.VOLUNTARY.value):
        return []

    msg = []
    for idx, party in enumerate(parties):
        party_type = get_str(party, "/officer/partyType")
        # Only validate if partyType is organization
        if party_type == "organization":

            org_name = get_str(party, "/officer/organizationName")
            stripped_org_name = org_name.strip()

            if not stripped_org_name:
                msg.append({
                    "error": "Organization name is required.",
                    "path": f"/filing/dissolution/parties/{idx}/officer/organizationName"
                })
            elif org_name != stripped_org_name:
                msg.append({
                    "error": "Organization name cannot have leading or trailing spaces.",
                    "path": f"/filing/dissolution/parties/{idx}/officer/organizationName"
                })    

    return msg

def _check_dissolution_permission(required_permission: str, dissolution_type: str, filing_type: str) -> Optional[Error]:
    """Check if the user has the required permission for the dissolution filing."""
    message = "Permission Denied - You do not have permissions file {dissolution_type} {filing_type} filing."
    return PermissionService.check_user_permission(required_permission, message=message)

def _validate_dissolution_permission(business: Business, dissolution_type: str, filing_type: str) -> Optional[Error]:
    """Validate dissolution permission based on business and dissolution type."""

    if dissolution_type == DissolutionTypes.ADMINISTRATIVE.value:
            error = _check_dissolution_permission(
                ListFilingsPermissionsAllowed.DISSOLUTION_ADMIN_FILING.value,
                dissolution_type,
                filing_type
            )
            if error:
                return error
    if dissolution_type == DissolutionTypes.INVOLUNTARY.value:
        error = _check_dissolution_permission(
            ListFilingsPermissionsAllowed.DISSOLUTION_INVOLUNTARY_FILING.value,
            dissolution_type,
            filing_type
        )
        if error:
            return error
    if business.legal_type in (Business.LegalTypes.SOLE_PROP.value, Business.LegalTypes.PARTNERSHIP.value):
        error = _check_dissolution_permission(
            ListFilingsPermissionsAllowed.DISSOLUTION_FIRM_FILING.value,
            dissolution_type,
            filing_type
        )
        if error:
            return error
    if dissolution_type == DissolutionTypes.VOLUNTARY.value:
        error = _check_dissolution_permission(
            ListFilingsPermissionsAllowed.DISSOLUTION_VOLUNTARY_FILING.value,
            dissolution_type,
            filing_type
        )
        if error:
            return error
    
    if dissolution_type == DissolutionTypes.DELAY.value:
        error = _check_dissolution_permission(
            ListFilingsPermissionsAllowed.DISSOLUTION_DELAY_FILING.value,
            dissolution_type,
            filing_type
        )
        if error:
            return error
