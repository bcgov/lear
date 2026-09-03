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
"""Validation for the Correction filing."""
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from typing import Final

from dateutil.relativedelta import relativedelta
from flask.globals import request_ctx
from flask_babel import _

from business_model.models import Business, CourtOrder, Filing, Jurisdiction, PartyRole
from business_model.models.types.filings import FilingTypes
from legal_api.core.filing_helper import is_special_resolution_correction_by_filing_json
from legal_api.errors import Error
from legal_api.services import STAFF_ROLE, SYSTEM_ROLE, NaicsService
from legal_api.services.filings.validations.alteration import validate_type_change
from legal_api.services.filings.validations.common_validations import (
    is_same_str,
    validate_court_order,
    validate_foreign_jurisdiction,
    validate_name_request,
    validate_offices_addresses,
    validate_out_date,
    validate_parties_addresses,
    validate_parties_names,
    validate_pdf,
    validate_relationships,
    validate_resolution_date_in_share_structure,
    validate_share_currency,
    validate_share_structure,
)
from legal_api.services.filings.validations.continuation_in import (
    validate_continuation_in_expro_business_in_colin,
    validate_continuation_in_foreign_jurisdiction,
)
from legal_api.services.filings.validations.dissolution import validate_custodian_email
from legal_api.services.filings.validations.incorporation_application import (
    validate_coop_parties_mailing_address,
    validate_roles,
)
from legal_api.services.filings.validations.incorporation_application import validate_offices as validate_corp_offices
from legal_api.services.filings.validations.registration import validate_offices
from legal_api.services.filings.validations.special_resolution import (
    validate_resolution_content,
    validate_signatory_name,
    validate_signing_date,
)
from legal_api.services.utils import get_bool, get_date, get_str
from legal_api.utils.auth import jwt


def validate(business: Business, filing: dict) -> Error:
    """Validate the Correction filing."""
    if not business or not filing:
        return Error(HTTPStatus.BAD_REQUEST, [{"error": _("A valid business and filing are required.")}])
    msg = []
    filing_type = "correction"

    is_comment_only_correction = get_bool(filing, "/filing/correction/commentOnly")
    is_staff_or_system_role = (jwt.validate_roles(request_ctx.current_user, [STAFF_ROLE])
                               or jwt.validate_roles(request_ctx.current_user, [SYSTEM_ROLE]))

    # check if comment only correction filed by staff or system
    if is_comment_only_correction and not is_staff_or_system_role:
        path = "/filing/correction/commentOnly"
        msg.append({"error": _("Only staff can file comment only Corrections."), "path": path})

    # confirm corrected filing ID is a valid complete filing
    corrected_filing = Filing.find_by_id(filing["filing"]["correction"]["correctedFilingId"])
    if not corrected_filing or corrected_filing.status not in [Filing.Status.COMPLETED.value,
                                                               Filing.Status.CORRECTED.value]:
        path = "/filing/correction/correctedFilingId"
        msg.append({"error": _("Corrected filing is not a valid filing."), "path": path})

    # confirm that this business owns the corrected filing
    elif business.id != corrected_filing.business_id:
        path = "/filing/correction/correctedFilingId"
        msg.append({"error": _("Corrected filing is not a valid filing for this business."), "path": path})

    elif corrected_filing.filing_type != filing["filing"]["correction"]["correctedFilingType"]:
        path = "/filing/correction/correctedFilingType"
        msg.append({"error": _("The corrected filing type does not match filing type of corrected filing."),
                    "path": path})

    # skip all the other validation checks if comment only correction
    if not is_comment_only_correction:
        if filing.get("filing", {}).get("correction", {}).get("parties", None):
            msg.extend(validate_parties_addresses(filing, filing_type))
        if filing.get("filing", {}).get("correction", {}).get("offices", None):
            msg.extend(validate_offices_addresses(filing, filing_type))

        _validate_type_specific_props(business, filing, msg)

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)

    return None

def _validate_type_specific_props(business: Business, filing: dict, msg: list):
    if business.legal_type in [Business.LegalTypes.SOLE_PROP.value, Business.LegalTypes.PARTNERSHIP.value]:
        _validate_firms_correction(business, filing, business.legal_type, msg)
    elif business.legal_type in Business.CORPS:
        _validate_corps_correction(business, filing, business.legal_type, msg)
    elif business.legal_type == Business.LegalTypes.COOP.value:
        _validate_special_resolution_correction(filing, business.legal_type, msg)


def _validate_firms_correction(business: Business, filing, legal_type, msg):
    filing_type = "correction"
    if filing.get("filing", {}).get("correction", {}).get("nameRequest", {}).get("nrNumber", None):
        msg.extend(validate_name_request(filing, legal_type, filing_type))
    if filing.get("filing", {}).get("correction", {}).get("parties", None):
        msg.extend(validate_party(filing, legal_type))
    if filing.get("filing", {}).get("correction", {}).get("offices", None):
        msg.extend(validate_offices(filing, filing_type))
    if filing.get("filing", {}).get("correction", {}).get("startDate", None):
        msg.extend(validate_start_date(business, filing))
    msg.extend(validate_naics(business, filing, filing_type))


def _validate_corps_correction(business: Business, filing_dict, legal_type, msg):
    if filing_dict.get("filing", {}).get("correction", {}).get("courtOrder", None):
        msg.extend(court_order_validation(filing_dict))
    msg.extend(_validate_court_orders_correction(filing_dict, business))

    if relationships := filing_dict.get("filing", {}).get("correction", {}).get("relationships", None):
        relationships_path = "/filing/correction/relationships"
        completing_parties = [
            x for x in relationships
            if any(
                role for role in x.get("roles", [])
                if role["roleType"].lower().replace(" ", "_") == PartyRole.RoleTypes.COMPLETING_PARTY.value
            )
        ]
        correction_type = filing_dict.get("filing").get("correction").get("type", "STAFF")
        if correction_type == "STAFF":
            if len(completing_parties) != 0:
                msg.append({
                    "error": "Should not provide completing party when correction type is STAFF",
                    "path": relationships_path
                })
        elif len(completing_parties) == 0:
            msg.append({"error": "Completing party is required.", "path": relationships_path})
        elif len(completing_parties) > 1:
            msg.append({"error": "Only one completing party is allowed.", "path": relationships_path})

    if business.state == Business.State.HISTORICAL.value:
        _validate_corps_correction_historical(business, filing_dict, msg)
    else:
        _validate_corps_correction_active(business, filing_dict, legal_type, msg)


def _validate_corps_correction_historical(business: Business, filing_dict, msg):
    filing_type = "correction"
    msg.extend(_validate_out_correction(filing_dict, filing_type, business))
    if relationships := filing_dict.get("filing", {}).get("correction", {}).get("relationships", None):
        custodian_parties = [
            x for x in relationships
            if any(
                role for role in x.get("roles", [])
                if role["roleType"].lower() == PartyRole.RoleTypes.CUSTODIAN.value
            )
        ]
        relationships_path = "/filing/correction/relationships"
        if len(custodian_parties) > 1:
            msg.append({"error": "Only one custodian is allowed.", "path": relationships_path})
        elif len(custodian_parties) == 1:
            today = datetime.now(tz=UTC).date()
            existing_custodian = PartyRole.get_party_roles(business.id, today, PartyRole.RoleTypes.CUSTODIAN.value)
            if not custodian_parties[0].get("entity", {}).get("identifier") and len(existing_custodian) > 0:
                msg.append({
                    "error": "Custodian already exists for this business, cannot create another custodian.",
                    "path": relationships_path
                })
            msg.extend(
                validate_custodian_email(
                    custodian_parties[0].get("entity", {}).get("email"),
                    f"{relationships_path}/entity/email"
                )
            )

        msg.extend(validate_relationships(
            business,
            filing_dict,
            filing_type,
            [
                PartyRole.RoleTypes.CUSTODIAN,
                PartyRole.RoleTypes.COMPLETING_PARTY
            ],
            True,
            True,
            [PartyRole.RoleTypes.CUSTODIAN, PartyRole.RoleTypes.COMPLETING_PARTY]
        ))


def _validate_corps_correction_active(business: Business, filing_dict, legal_type, msg):
    filing_type = "correction"
    if new_legal_type := filing_dict.get("filing", {}).get("correction", {}).get("newLegalType"):
        if business.legal_type == new_legal_type:
            # This is not a valid type change
            path = "/filing/correction/newLegalType"
            msg.append({"error": _("New legal type must be different from current legal type."), "path": path})
        else:
            msg.extend(validate_type_change(filing_dict, business, "/filing/correction/newLegalType"))
    if filing_dict.get("filing", {}).get("correction", {}).get("nameRequest", {}).get("nrNumber", None):
        msg.extend(validate_name_request(filing_dict, legal_type, filing_type))
    if filing_dict.get("filing", {}).get("correction", {}).get("offices", None):
        msg.extend(validate_corp_offices(filing_dict, legal_type, filing_type))
    if filing_dict.get("filing", {}).get("correction", {}).get("parties", None):
        err = validate_roles(filing_dict, legal_type, filing_type)
        if err:
            msg.extend(err)
        # FUTURE: this should be removed when COLIN sync back is no longer required.
        msg.extend(validate_parties_names(filing_dict, filing_type, legal_type))

    if filing_dict.get("filing", {}).get("correction", {}).get("relationships", None):
        msg.extend(validate_relationships(
            business,
            filing_dict,
            filing_type,
            [
                PartyRole.RoleTypes.DIRECTOR,
                PartyRole.RoleTypes.LIQUIDATOR,
                PartyRole.RoleTypes.RECEIVER,
                PartyRole.RoleTypes.COMPLETING_PARTY
            ],
            True,
            True,
            [PartyRole.RoleTypes.DIRECTOR, PartyRole.RoleTypes.COMPLETING_PARTY]
        ))

    if filing_dict.get("filing", {}).get("correction", {}).get("shareStructure", None):
        err = validate_share_structure(filing_dict, filing_type, legal_type)
        if err:
            msg.extend(err)

        msg.extend(validate_share_currency(filing_dict, filing_type, business))
        msg.extend(validate_resolution_date_in_share_structure(filing_dict, filing_type, business))

    msg.extend(_validate_continuation_in_correction(filing_dict, filing_type, legal_type, business))
    msg.extend(_validate_amalgamation_correction(filing_dict, filing_type, business))


def _validate_court_orders_correction(filing_dict, business: Business):
    """Validate court orders for a correction filing.

    - If the court order has an Id, verifies it exists in the database for the business.
    - If the court order does not have an Id, verifies its filingId matches the corrected filing Id.
    - Verifies that only one court order is associated with the corrected filing in the database.
    - Verifies that no more than one new court order is being added in the correction.
    - Performs common validation on court order details.
    """
    msg = []
    if not (orders := filing_dict["filing"]["correction"].get("courtOrders")):
        return msg

    corrected_filing_id = filing_dict["filing"]["correction"]["correctedFilingId"]
    new_court_orders = []
    court_orders_db = CourtOrder.get_json_with_filing_type(business.id)
    for idx, order in enumerate(orders):
        path = f"/filing/correction/courtOrders/{idx}"
        is_file_or_details_required = False
        if order_id := order.get("id"):
            court_order_db = next((o for o in court_orders_db if o["id"] == order_id), None)
            if not court_order_db:
                msg.append({"error": _("Court order not found."), "path": path})
            else:
                is_file_or_details_required = (court_order_db["filingType"] == "courtOrder")
        elif order.get("filingId") == corrected_filing_id:
            if next((o for o in court_orders_db if o["filingId"] == corrected_filing_id), None):
                msg.append({"error": _("Only one court order can be added per filing."), "path": path})

            is_file_or_details_required = (
                filing_dict["filing"]["correction"]["correctedFilingType"] == FilingTypes.COURTORDER
            )
            new_court_orders.append(order)
        else:
            msg.append({"error": _("Filing Id does not match corrected filing Id."), "path": path})


        msg.extend(validate_court_order(path, order, is_file_or_details_required))

    if len(new_court_orders) > 1:
        msg.append({"error": _("Only one court order can be added."), "path": "/filing/correction/courtOrders"})

    return msg


def _validate_amalgamation_correction(filing_dict, filing_type, business: Business):
    msg = []
    if not (
        amalgamating_businesses_json := filing_dict["filing"][filing_type].get("amalgamation", {})
            .get("amalgamatingBusinesses", [])
    ):
        return msg
    
    amalgamation = business.amalgamation.first()
    amalgamating_businesses = amalgamation.amalgamating_businesses.all()
    for idx, ting_json in enumerate(amalgamating_businesses_json):
        path = f"/filing/{filing_type}/amalgamation/amalgamatingBusinesses/{idx}"
        ting_id = ting_json["id"]
        ting = next((ting for ting in amalgamating_businesses if ting.id == ting_id), None)
        if not ting:
            msg.append({"error": _("Amalgamating business not found."), "path": path})
            continue

        if ting.business_id or ting.colin_identifier:
            # LEAR and COLIN (incl. extraprovincial) entries carry no correctable filing data
            msg.append({"error": _("Can only correct foreign businesses."), "path": path})
            continue

        # Skip to allow unmodified invalid migrated data
        if (
            not is_same_str(ting.foreign_jurisdiction, ting_json["foreignJurisdiction"]["country"]) or
            not is_same_str(ting.foreign_jurisdiction_region, ting_json["foreignJurisdiction"].get("region"))
        ):
            msg.extend(
                validate_foreign_jurisdiction(
                    ting_json["foreignJurisdiction"],
                    f"{path}/foreignJurisdiction",
                    is_region_for_us_required=False
                )
            )
    return msg


def _validate_continuation_in_correction(filing_dict, filing_type, legal_type, business: Business):
    msg = []
    if continuation_in := filing_dict["filing"][filing_type].get("continuationIn"):
        jurisdiction = Jurisdiction.get_continuation_in_jurisdiction(business.id)
        skip_jurisdiction = (  # Skip to allow unmodified invalid migrated data
            is_same_str(jurisdiction.country, continuation_in.get("country")) and
            is_same_str(jurisdiction.region, continuation_in.get("region"))
        )
        msg.extend(validate_continuation_in_foreign_jurisdiction(
            legal_type,
            continuation_in,
            f"/filing/{filing_type}/continuationIn",
            skip_affidavit=True,
            skip_jurisdiction=skip_jurisdiction
        ))
        msg.extend(validate_continuation_in_expro_business_in_colin(
            continuation_in.get("expro"),
            f"/filing/{filing_type}/continuationIn/expro",
            skip_founding_date=True
        ))
    return msg


def _validate_out_correction(filing_dict, filing_type, business):
    msg = []
    corrected_filing_type = filing_dict["filing"]["correction"]["correctedFilingType"]
    if (
        corrected_filing_type in [FilingTypes.CONTINUATIONOUT, FilingTypes.AMALGAMATIONOUT]
        and (out := filing_dict["filing"][filing_type].get(corrected_filing_type))
    ):
        if (  # Skip to allow unmodified invalid migrated data
            not is_same_str(business.jurisdiction, out.get("country")) or
            not is_same_str(business.foreign_jurisdiction_region, out.get("region"))
        ):
            msg.extend(validate_foreign_jurisdiction(out, f"/filing/{filing_type}/{corrected_filing_type}"))

        msg.extend(validate_out_date(filing_dict, f"/filing/{filing_type}/{corrected_filing_type}/date"))

    return msg


def _validate_special_resolution_correction(filing_dict, legal_type, msg):
    filing_type = "correction"
    if filing_dict.get("filing", {}).get(filing_type, {}).get("nameRequest", {}).get("nrNumber", None):
        msg.extend(validate_name_request(filing_dict, legal_type, filing_type))
    if filing_dict.get("filing", {}).get(filing_type, {}).get("resolution", None):
        msg.extend(validate_resolution_content(filing_dict, filing_type))
    if filing_dict.get("filing", {}).get(filing_type, {}).get("signingDate", None):
        msg.extend(validate_signing_date(filing_dict, filing_type))
    if filing_dict.get("filing", {}).get(filing_type, {}).get("signatory", None):
        msg.extend(validate_signatory_name(filing_dict, filing_type))
    if filing_dict.get("filing", {}).get(filing_type, {}).get("courtOrder", None):
        msg.extend(court_order_validation(filing_dict))
    if filing_dict.get("filing", {}).get(filing_type, {}).get("rulesFileKey", None):
        msg.extend(rules_change_validation(filing_dict))
    if filing_dict.get("filing", {}).get(filing_type, {}).get("memorandumFileKey", None):
        msg.extend(memorandum_change_validation(filing_dict))
    if is_special_resolution_correction_by_filing_json(filing_dict.get("filing", {})):
        _validate_roles_parties_correction(filing_dict, legal_type, filing_type, msg)


def _validate_roles_parties_correction(filing_dict, legal_type, filing_type, msg):
    if filing_dict.get("filing", {}).get("correction", {}).get("parties", None):
        err = validate_roles(filing_dict, legal_type, filing_type)
        if err:
            msg.extend(err)

        msg.extend(validate_parties_names(filing_dict, filing_type, legal_type))
        msg.extend(validate_coop_parties_mailing_address(filing_dict, filing_type))
    else:
        err_path = f"/filing/{filing_type}/parties/roles"
        msg.append({"error": "Parties list cannot be empty or null", "path": err_path})


def validate_party(filing: dict, legal_type: str) -> list: # noqa: PLR0912
    """Validate party."""
    msg = []
    completing_parties = 0
    proprietor_parties = 0
    partner_parties = 0
    invalid_roles = set()
    parties = filing["filing"]["correction"]["parties"]
    for party in parties:  # pylint: disable=too-many-nested-blocks;
        for role in party.get("roles", []):
            role_type = role.get("roleType").lower().replace(" ", "_")
            if role_type == PartyRole.RoleTypes.COMPLETING_PARTY.value:
                completing_parties += 1
            elif role_type == PartyRole.RoleTypes.PROPRIETOR.value:
                proprietor_parties += 1
            elif role_type == PartyRole.RoleTypes.PARTNER.value:
                partner_parties += 1
            else:
                invalid_roles.add(role_type)

    if invalid_roles:
        err_path = "/filing/correction/parties/roles"
        msg.append({
            "error": f'Invalid party role(s) provided: {", ".join(sorted(invalid_roles))}.',
            "path": err_path
        })

    party_path = "/filing/correction/parties"

    if legal_type == Business.LegalTypes.SOLE_PROP.value and partner_parties > 0:
        msg.append({"error": "Partner is not valid for a Sole Proprietorship.", "path": party_path})
    elif legal_type == Business.LegalTypes.PARTNERSHIP.value and proprietor_parties > 0:
        msg.append({"error": "Proprietor is not valid for a General Partnership.", "path": party_path})

    min_partners: Final = 2
    min_proprietors: Final = 1
    min_completing_parties: Final = 1

    correction_type = filing.get("filing").get("correction").get("type", "STAFF")
    if correction_type == "STAFF":
        if legal_type == Business.LegalTypes.PARTNERSHIP.value and proprietor_parties > 0:
                msg.append({"error": "1 Proprietor is required.", "path": party_path})
        elif legal_type == Business.LegalTypes.PARTNERSHIP.value and partner_parties < min_partners:
                msg.append({"error": "2 Partners are required.", "path": party_path})
    elif (
        legal_type == Business.LegalTypes.SOLE_PROP.value and
        (completing_parties < min_completing_parties or proprietor_parties < min_proprietors)
    ):
        msg.append({"error": "1 Proprietor and a Completing Party are required.", "path": party_path})
    elif (
        legal_type == Business.LegalTypes.PARTNERSHIP.value and
        (completing_parties < min_completing_parties or partner_parties < min_partners)
    ):
        msg.append({"error": "2 Partners and a Completing Party are required.", "path": party_path})

    return msg


def validate_naics(business: Business, filing: dict, filing_type: str) -> list:
    """Validate naics."""
    msg = []
    naics_code_path = f"/filing/{filing_type}/business/naics/naicsCode"
    naics_code = get_str(filing, naics_code_path)
    naics_desc = get_str(filing, f"/filing/{filing_type}/business/naics/naicsDescription")

    # Note: if existing naics code and description has not changed, no NAICS validation is required
    if naics_code and (business.naics_code != naics_code or business.naics_description != naics_desc):
        naics = NaicsService.find_by_code(naics_code)
        if not naics or naics["classTitle"] != naics_desc:
            msg.append({"error": "Invalid naics code or description.", "path": naics_code_path})

    return msg


def validate_start_date(business: Business, filing: dict) -> list:
    """Validate start date."""
    # Staff can go back with an unlimited period of time, the maximum start date is 90 days after the registration date
    msg = []
    start_date_path = "/filing/correction/startDate"
    start_date = get_date(filing, start_date_path)
    registration_date = business.founding_date.date()
    greater = registration_date + timedelta(days=90)
    lesser = registration_date + relativedelta(years=-10)

    if not jwt.validate_roles(request_ctx.current_user, [STAFF_ROLE]) and start_date < lesser:
        msg.append({"error": "Start date must be less than or equal to 10 years.",
                    "path": start_date_path})
    if start_date > greater:
        msg.append({"error": "Start Date must be less than or equal to 90 days in the future.",
                    "path": start_date_path})

    return msg


def court_order_validation(filing):
    """Validate court order."""
    court_order_path: Final = "/filing/correction/courtOrder"
    if get_str(filing, court_order_path):
        return validate_court_order(court_order_path, filing["filing"]["correction"]["courtOrder"])
    return []


def rules_change_validation(filing):
    """Validate rules change."""
    msg = []
    rules_file_key_path: Final = "/filing/correction/rulesFileKey"
    rules_file_key: Final = get_str(filing, rules_file_key_path)

    if rules_file_key:
        msg.extend(validate_pdf(rules_file_key, rules_file_key_path))

    return msg


def memorandum_change_validation(filing):
    """Validate memorandum change."""
    msg = []
    memorandum_file_key_path: Final = "/filing/correction/memorandumFileKey"
    memorandum_file_key: Final = get_str(filing, memorandum_file_key_path)

    if memorandum_file_key:
        msg.extend(validate_pdf(memorandum_file_key, memorandum_file_key_path))

    return msg
