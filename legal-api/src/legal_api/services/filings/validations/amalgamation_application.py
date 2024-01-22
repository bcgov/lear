# Copyright © 2023 Province of British Columbia
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
"""Validation for the Amalgamation Application filing."""
from http import HTTPStatus
from typing import Dict, Final, Optional

from flask_babel import _ as babel  # noqa: N813, I004, I001; importing camelcase '_' as a name

from legal_api.errors import Error
from legal_api.models import BusinessCommon, EntityRole, Filing
from legal_api.services import STAFF_ROLE
from legal_api.services.bootstrap import AccountService
from legal_api.services.business_service import BusinessService
from legal_api.services.filings.validations.common_validations import (
    validate_court_order,
    validate_name_request,
    validate_share_structure,
)
from legal_api.services.filings.validations.incorporation_application import validate_offices
from legal_api.services.utils import get_str
from legal_api.utils.auth import jwt

# noqa: I003


def validate(business: any, amalgamation_json: Dict, account_id) -> Optional[Error]:
    """Validate the Amalgamation Application filing."""
    filing_type = "amalgamationApplication"
    if not amalgamation_json:
        return Error(HTTPStatus.BAD_REQUEST, [{"error": babel("A valid filing is required.")}])
    msg = []

    entity_type_path = f"/filing/{filing_type}/nameRequest/legalType"
    entity_type = get_str(amalgamation_json, entity_type_path)
    if not entity_type:
        msg.append({"error": babel("Legal type is required."), "path": entity_type_path})
        return msg  # Cannot continue validation without entity_type

    amalgamation_type = get_str(amalgamation_json, f"/filing/{filing_type}/type")

    if amalgamation_json.get("filing", {}).get(filing_type, {}).get("nameRequest", {}).get("nrNumber", None):
        # Adopt from one of the amalgamating businesses contains name not nrNumber
        msg.extend(validate_name_request(amalgamation_json, entity_type, filing_type))

    msg.extend(validate_party(amalgamation_json, amalgamation_type, filing_type))
    if amalgamation_type == "regular":
        msg.extend(validate_offices(amalgamation_json, filing_type))
        err = validate_share_structure(amalgamation_json, filing_type)
        if err:
            msg.extend(err)

    msg.extend(validate_amalgamation_court_order(amalgamation_json, filing_type))
    msg.extend(validate_amalgamating_businesses(amalgamation_json, filing_type, entity_type, account_id))

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def validate_amalgamating_businesses(  # pylint: disable=too-many-branches,too-many-statements,too-many-locals
    amalgamation_json, filing_type, entity_type, account_id
) -> list:
    """Validate amalgamating businesses."""
    is_staff = jwt.validate_roles([STAFF_ROLE])
    msg = []
    amalgamating_businesses_json = (
        amalgamation_json.get("filing", {}).get(filing_type, {}).get("amalgamatingBusinesses", [])
    )
    amalgamating_businesses_path = f"/filing/{filing_type}/amalgamatingBusinesses"
    is_any_limited = False
    is_any_ccc = False
    is_any_ben = False
    is_any_ulc = False
    is_any_expro_a = False
    amalgamating_businesses = {}
    duplicate_businesses = []
    for amalgamating_business_json in amalgamating_businesses_json:
        if identifier := amalgamating_business_json.get("identifier"):
            if (
                identifier.startswith("A")
                and (foreign_jurisdiction := amalgamating_business_json.get("foreignJurisdiction"))
                and foreign_jurisdiction.get("country") == "CA"
                and foreign_jurisdiction.get("region") == "BC"
            ):
                is_any_expro_a = True

            if not (business := BusinessService.fetch_business(identifier)):
                continue

            if identifier in amalgamating_businesses:
                duplicate_businesses.append(identifier)
            amalgamating_businesses[identifier] = business

            if business.entity_type == BusinessCommon.EntityTypes.BCOMP.value:
                is_any_ben = True
            elif business.entity_type == BusinessCommon.EntityTypes.COMP.value:
                is_any_limited = True
            elif business.entity_type == BusinessCommon.EntityTypes.BC_CCC.value:
                is_any_ccc = True
            elif business.entity_type == BusinessCommon.EntityTypes.BC_ULC_COMPANY.value:
                is_any_ulc = True
        elif corp_number := amalgamating_business_json.get("corpNumber"):
            if corp_number in amalgamating_businesses:
                duplicate_businesses.append(corp_number)
            amalgamating_businesses[corp_number] = amalgamating_business_json

            if (corp_number.startswith("A") and
                    (foreign_jurisdiction := amalgamating_business_json.get("foreignJurisdiction")) and
                    foreign_jurisdiction.get("country") == "CA" and
                    foreign_jurisdiction.get("region") == "BC"):
                is_any_expro_a = True
    is_any_bc_company = is_any_ben or is_any_limited or is_any_ccc or is_any_ulc

    for amalgamating_business_json in amalgamating_businesses_json:
        identifier = amalgamating_business_json.get("identifier")
        foreign_legal_name = amalgamating_business_json.get("legalName")
        is_foreign_business = bool(foreign_legal_name)
        amalgamating_business = amalgamating_businesses.get(identifier)

        if amalgamating_business:
            if amalgamating_business.state == BusinessCommon.State.HISTORICAL:
                msg.append(
                    {
                        "error": f"Cannot amalgamate with {identifier} which is in historical state.",
                        "path": amalgamating_businesses_path,
                    }
                )
            elif _has_pending_filing(amalgamating_business):
                msg.append(
                    {"error": f"{identifier} has a draft, pending or future effective filing.", "path": amalgamating_businesses_path}
                )

        if not is_staff:
            if amalgamating_business:
                if not _is_business_affliated(identifier, account_id):
                    msg.append(
                        {
                            "error": f"{identifier} is not affiliated with the currently selected BC Registries account.",  # noqa: E501
                            "path": amalgamating_businesses_path,
                        }
                    )

                if not amalgamating_business.good_standing:
                    msg.append(
                        {"error": f"{identifier} is not in good standing.", "path": amalgamating_businesses_path}
                    )
            elif identifier:
                msg.append(
                    {
                        "error": f"A business with identifier:{identifier} not found.",
                        "path": amalgamating_businesses_path,
                    }
                )

            if is_foreign_business:
                msg.append(
                    {
                        "error": (
                            f"{foreign_legal_name} foreign corporation cannot "
                            "be amalgamated except by Registries staff."
                        ),
                        "path": amalgamating_businesses_path,
                    }
                )
        else:
            if is_foreign_business:
                if entity_type == BusinessCommon.EntityTypes.BC_ULC_COMPANY.value and is_any_bc_company:
                    msg.append(
                        {
                            "error": (
                                f"{foreign_legal_name} foreign corporation must not amalgamate with "
                                "a BC company to form a BC Unlimited Liability Company."
                            ),
                            "path": amalgamating_businesses_path,
                        }
                    )

                if is_any_ulc:
                    msg.append(
                        {
                            "error": (
                                "A BC Unlimited Liability Company cannot amalgamate with "
                                f"a foreign company {foreign_legal_name}."
                            ),
                        "path": amalgamating_businesses_path
                    })

    if duplicate_businesses:
        error_msg = "Duplicate amalgamating business entry found in list: " + \
            ", ".join(duplicate_businesses) + "."
        msg.append({
            "error": error_msg,
            "path": amalgamating_businesses_path
        })

    if len(amalgamating_businesses) < 2:
        msg.append({
            "error": "Two or more amalgamating businesses required.",
            "path": amalgamating_businesses_path,
        })

    if entity_type == BusinessCommon.EntityTypes.BC_CCC.value and not is_any_ccc:
        msg.append(
            {
                "error": (
                    "A BC Community Contribution Company must amalgamate to form "
                    "a new BC Community Contribution Company."
                ),
                "path": amalgamating_businesses_path,
            }
        )
    elif (
        entity_type in [BusinessCommon.EntityTypes.BC_CCC.value, BusinessCommon.EntityTypes.BC_ULC_COMPANY.value]
        and is_any_expro_a
        and is_any_bc_company
    ):
        msg.append(
            {
                "error": (
                    "An extra-Pro cannot amalgamate with anything to become "
                    "a BC Unlimited Liability Company or a BC Community Contribution Company."
                ),
                "path": amalgamating_businesses_path,
            }
        )

    return msg


def _is_business_affliated(identifier, account_id):
    if (
        (account_response := AccountService.get_account_by_affiliated_identifier(identifier))
        and (orgs := account_response.get("orgs"))
        and any(str(org.get("id")) == account_id for org in orgs)
    ):
        return True
    return False


def _has_pending_filing(amalgamating_business: any):
    if Filing.get_filings_by_status(amalgamating_business.id, [
            Filing.Status.DRAFT.value,
            Filing.Status.PENDING.value,
            Filing.Status.PAID.value]):
        return True
    return False


def validate_party(filing: Dict, amalgamation_type, filing_type) -> list:
    """Validate party."""
    msg = []
    completing_parties = 0
    director_parties = 0
    parties = filing["filing"][filing_type]["parties"]
    for party in parties:  # pylint: disable=too-many-nested-blocks;  # noqa: E501
        for role in party.get("roles", []):
            role_type = role.get("roleType").lower().replace(" ", "_")
            if role_type == EntityRole.RoleTypes.completing_party.name:
                completing_parties += 1
            elif role_type == EntityRole.RoleTypes.director.name:
                director_parties += 1

    party_path = f"/filing/{filing_type}/parties"
    if amalgamation_type == "regular" and (completing_parties < 1 or director_parties < 1):
        msg.append({"error": "At least one Director and a Completing Party is required.", "path": party_path})
    elif amalgamation_type in ["vertical", "horizontal"] and completing_parties == 0:
        msg.append({"error": "A Completing Party is required.", "path": party_path})

    return msg


def validate_amalgamation_court_order(filing: Dict, filing_type) -> list:
    """Validate court order."""
    if court_order := filing.get("filing", {}).get(filing_type, {}).get("courtOrder", None):
        court_order_path: Final = f"/filing/{filing_type}/courtOrder"
        err = validate_court_order(court_order_path, court_order)
        if err:
            return err
    return []
