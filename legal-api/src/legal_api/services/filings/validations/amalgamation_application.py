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
from datetime import UTC, datetime
from http import HTTPStatus
from typing import Final

from flask.globals import request_ctx
from flask_babel import _ as babel

from business_account import AccountService
from business_model.models import AmalgamatingBusiness, Amalgamation, Business, Filing, OfficeType, PartyRole
from legal_api.errors import Error
from legal_api.services import STAFF_ROLE, colin, flags
from legal_api.services.filings.validations.common_validations import (
    validate_court_order,
    validate_effective_date,
    validate_foreign_jurisdiction,
    validate_name_request,
    validate_offices_addresses,
    validate_parties_addresses,
    validate_parties_names,
    validate_permission_and_completing_party,
    validate_phone_number,
    validate_share_currency,
    validate_share_structure,
)
from legal_api.services.filings.validations.incorporation_application import (
    validate_offices,
    validate_parties_delivery_address,
)
from legal_api.services.permissions import ListActionsPermissionsAllowed, PermissionService
from legal_api.services.utils import get_str
from legal_api.utils.auth import jwt

# COLIN corps not loaded in LEAR that can amalgamate
COLIN_AMALGAMATION_LEGAL_TYPES: Final = [
    Business.LegalTypes.COMP.value,
    Business.LegalTypes.BC_ULC_COMPANY.value,
    Business.LegalTypes.BC_CCC.value,
    # extraprovincials get the foreign-corporation rule set, not the COLIN TING checks
    Business.LegalTypes.EXTRA_PRO_A.value,
]


def validate(amalgamation_json: dict, account_id) -> Error | None:
    """Validate the Amalgamation Application filing."""
    filing_type = "amalgamationApplication"
    if not amalgamation_json:
        return Error(HTTPStatus.BAD_REQUEST, [{"error": babel("A valid filing is required.")}])
    msg = []

    legal_type_path = f"/filing/{filing_type}/nameRequest/legalType"
    legal_type = get_str(amalgamation_json, legal_type_path)
    if not legal_type:
        msg.append({"error": babel("Legal type is required."), "path": legal_type_path})
        return msg  # Cannot continue validation without legal_type

    amalgamation_type = get_str(amalgamation_json, f"/filing/{filing_type}/type")

    msg.extend(_validate_name_request_section(amalgamation_json, amalgamation_type, legal_type, filing_type))

    if flags.is_on("enabled-deeper-permission-action"):
        err = validate_permission_and_completing_party(
            None,
            amalgamation_json,
            filing_type,
            msg,
            {"check_name":False,
            "check_email":True,
            "check_address":False,
            "check_document_email":True}
                            )
        if err:
            return err
    msg.extend(validate_party(amalgamation_json, amalgamation_type, filing_type))
    msg.extend(validate_parties_names(amalgamation_json, filing_type, legal_type))
    msg.extend(validate_parties_addresses(amalgamation_json, filing_type))

    structural_errors = _structural_validation_errors(amalgamation_json, legal_type, filing_type)
    if amalgamation_type == Amalgamation.AmalgamationTypes.regular.name:
        msg.extend(structural_errors)
    else:
        # short-form: the filing must mirror the primary/holding business's current data
        msg.extend(validate_primary_or_holding_match(amalgamation_json, filing_type, amalgamation_type))
        msg.extend(_augment_with_source_update_hint(structural_errors, amalgamation_type))

    msg.extend(validate_amalgamation_court_order(amalgamation_json, filing_type))
    msg.extend(validate_amalgamating_businesses(amalgamation_json,
                                                filing_type,
                                                legal_type,
                                                amalgamation_type,
                                                account_id))

    err = validate_phone_number(amalgamation_json, legal_type, filing_type)
    if err:
        msg.extend(err)

    msg.extend(validate_effective_date(amalgamation_json))

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def _validate_name_request_section(amalgamation_json, amalgamation_type, legal_type, filing_type) -> list:
    name_request = amalgamation_json.get("filing", {}).get(filing_type, {}).get("nameRequest", {})
    if not name_request.get("nrNumber"):
        return []

    if amalgamation_type in [Amalgamation.AmalgamationTypes.horizontal.name,
                             Amalgamation.AmalgamationTypes.vertical.name]:
        # Short-form amalgamations adopt the primary/holding business name; an NR is not allowed.
        return [{
            "error": "Short-form amalgamations cannot have a Name Request.",
            "path": f"/filing/{filing_type}/nameRequest/nrNumber"
        }]

    return validate_name_request(amalgamation_json, legal_type, filing_type)


def _structural_validation_errors(amalgamation_json, legal_type, filing_type) -> list:
    """Validate the office, share structure and party address data.

    Sections are gated on presence: short-form filings are not schema-required to carry
    them (a missing section gets its own required-section error from the match validation).
    """
    filing_section = amalgamation_json.get("filing", {}).get(filing_type, {})
    msg = []
    if "offices" in filing_section:
        msg.extend(validate_offices(amalgamation_json, legal_type, filing_type))
        msg.extend(validate_offices_addresses(amalgamation_json, filing_type))
    if "shareStructure" in filing_section:
        if err := validate_share_structure(amalgamation_json, filing_type, legal_type):
            msg.extend(err)
        if err := validate_share_currency(amalgamation_json, filing_type):
            msg.extend(err)
    if err := validate_parties_delivery_address(amalgamation_json, legal_type, filing_type):
        msg.extend(err)
    return msg


def _primary_or_holding_role(amalgamation_type: str) -> str:
    """Return the TED-defining role for a short-form amalgamation type."""
    return (AmalgamatingBusiness.Role.primary.name
            if amalgamation_type == Amalgamation.AmalgamationTypes.horizontal.name
            else AmalgamatingBusiness.Role.holding.name)


def _augment_with_source_update_hint(errors: list, amalgamation_type: str) -> list:
    """Point short-form structural problems at the source business - they cannot be fixed in this filing."""
    role = _primary_or_holding_role(amalgamation_type)
    for error in errors:
        error["error"] += (f" This data comes from the {role} business - its information must be "
                           "corrected outside of this filing before this amalgamation can be filed.")
    return errors


def validate_amalgamating_businesses(  # noqa: PLR0912, PLR0915
        amalgamation_json,
        filing_type,
        legal_type,
        amalgamation_type,
        account_id) -> list:
    """Validate amalgamating businesses."""
    is_staff = jwt.validate_roles(request_ctx.current_user, [STAFF_ROLE])
    enabled_filings = flags.value("supported-amalgamation-entities").split()
    if legal_type not in enabled_filings:
        return Error(HTTPStatus.FORBIDDEN,
                     [{"error": babel(f"{legal_type} is not enabled for amalgamation entities.")}])
    msg = []
    amalgamating_businesses_json = amalgamation_json.get("filing", {}) \
                                                    .get(filing_type, {})\
                                                    .get("amalgamatingBusinesses", [])
    amalgamating_businesses_path = f"/filing/{filing_type}/amalgamatingBusinesses"
    is_any_business = {
        Business.LegalTypes.BCOMP.value: False,
        Business.LegalTypes.COMP.value: False,
        Business.LegalTypes.BC_CCC.value: False,
        Business.LegalTypes.BC_ULC_COMPANY.value: False
    }
    is_any_expro_a = False
    is_any_foreign = False
    business_identifiers = []
    duplicate_businesses = []
    adoptable_names = []
    primary_or_holding_legal_type = None
    amalgamating_business_roles = {
        AmalgamatingBusiness.Role.amalgamating.name: 0,
        AmalgamatingBusiness.Role.holding.name: 0,
        AmalgamatingBusiness.Role.primary.name: 0
    }
    amalgamating_businesses = {}
    colin_businesses = {}
    expro_businesses = {}
    colin_fetch_failures = []

    # collect data for validation
    for amalgamating_business_json in amalgamating_businesses_json:
        amalgamating_business_roles[amalgamating_business_json["role"]] += 1
        identifier = amalgamating_business_json.get("identifier")
        if identifier in business_identifiers:
            duplicate_businesses.append(identifier)
            continue

        business_identifiers.append(identifier)

        # Check if its a foreign business
        if amalgamating_business_json.get("foreignJurisdiction"):
            is_any_foreign = True
            continue

        if business := Business.find_by_identifier(identifier):
            amalgamating_businesses[identifier] = business
            ting_legal_type, ting_legal_name = business.legal_type, business.legal_name
        else:
            # not foreign and not in LEAR - maybe a COLIN corp that can amalgamate
            colin_business, colin_fetch_failed = _find_colin_business(identifier)
            if not colin_business:
                if colin_fetch_failed:
                    colin_fetch_failures.append(identifier)
                continue
            if colin_business["legalType"] == Business.LegalTypes.EXTRA_PRO_A.value:
                is_any_expro_a = True
                expro_businesses[identifier] = colin_business
                continue
            colin_businesses[identifier] = colin_business
            ting_legal_type, ting_legal_name = colin_business["legalType"], colin_business["legalName"]

        # aggregate bookkeeping (CC/ULC mixes, name adoption, type match) shared by LEAR and COLIN TINGs
        is_any_business[ting_legal_type] = True
        if legal_type == ting_legal_type:
            adoptable_names.append(ting_legal_name)
        if amalgamating_business_json["role"] in [AmalgamatingBusiness.Role.primary.name,
                                                  AmalgamatingBusiness.Role.holding.name]:
            primary_or_holding_legal_type = ting_legal_type

    is_any_bc_company = (is_any_business[Business.LegalTypes.BCOMP.value] or
                         is_any_business[Business.LegalTypes.COMP.value] or
                         is_any_business[Business.LegalTypes.BC_CCC.value] or
                         is_any_business[Business.LegalTypes.BC_ULC_COMPANY.value])

    # validate each TING business
    for index, amalgamating_business_json in enumerate(amalgamating_businesses_json):
        # foreignJurisdiction and legalName are dependent in the schema. one cannot be present without the other
        if foreign_legal_name := amalgamating_business_json.get("legalName"):
            msg.extend(_validate_foreign_businesses(is_staff,
                                                    is_any_bc_company,
                                                    is_any_business[Business.LegalTypes.BC_ULC_COMPANY.value],
                                                    legal_type,
                                                    foreign_legal_name,
                                                    amalgamating_business_json,
                                                    f"{amalgamating_businesses_path}/{index}"))
        else:
            identifier = amalgamating_business_json.get("identifier")
            amalgamating_business_path = f"{amalgamating_businesses_path}/{index}"
            if amalgamating_business := amalgamating_businesses.get(identifier):
                business_info = _business_info_from_lear(amalgamating_business, is_staff)
            elif colin_business := colin_businesses.get(identifier):
                business_info = colin_business
            elif expro_business := expro_businesses.get(identifier):
                # extraprovincial: the foreign-corporation rule set, with the name from COLIN;
                # skips the affiliation/state/good-standing checks exactly as a foreign entry does
                msg.extend(_validate_foreign_rules(is_staff,
                                                   is_any_bc_company,
                                                   is_any_business[Business.LegalTypes.BC_ULC_COMPANY.value],
                                                   legal_type,
                                                   expro_business["legalName"],
                                                   amalgamating_business_json["role"],
                                                   amalgamating_business_path))
                continue
            elif identifier in colin_fetch_failures:
                # COLIN could not be reached - a clear retryable error, not "not found"
                msg.append({
                    "error": f"Unable to verify {identifier} - COLIN is unavailable, try again.",
                    "path": amalgamating_business_path
                })
                continue
            else:
                msg.append({
                    "error": f"A business with identifier:{identifier} not found.",
                    "path": amalgamating_business_path
                })
                continue

            msg.extend(_validate_amalgamating_business(identifier,
                                                       business_info,
                                                       account_id,
                                                       is_staff,
                                                       amalgamating_business_path))

    if duplicate_businesses:
        msg.append({
            "error": f'Duplicate amalgamating business entry found in list: {", ".join(duplicate_businesses)}.',
            "path": amalgamating_businesses_path
        })

    name_request = amalgamation_json.get("filing", {}).get(filing_type, {}).get("nameRequest", {})
    if (
        amalgamation_type == Amalgamation.AmalgamationTypes.regular.name and
        (
            not name_request.get("nrNumber") and
            (adopted_name := name_request.get("legalName")) and
            adopted_name not in adoptable_names
        )
    ):
        msg.append({
            "error": "Adopt a name that have the same business type as the resulting business.",
            "path": f"/filing/{filing_type}/nameRequest/legalName"
        })

    if primary_or_holding_legal_type:
        continued_types_map = {
            Business.LegalTypes.CONTINUE_IN.value: Business.LegalTypes.COMP.value,
            Business.LegalTypes.BCOMP_CONTINUE_IN.value: Business.LegalTypes.BCOMP.value,
            Business.LegalTypes.ULC_CONTINUE_IN.value: Business.LegalTypes.BC_ULC_COMPANY.value,
            Business.LegalTypes.CCC_CONTINUE_IN.value: Business.LegalTypes.BC_CCC.value
        }
        legal_type_to_compare = continued_types_map.get(primary_or_holding_legal_type,
                                                        primary_or_holding_legal_type)
        if legal_type_to_compare != legal_type:
            msg.append({
                "error": "Legal type should be same as the legal type in primary or holding business.",
                "path": f"/filing/{filing_type}/nameRequest/legalType"
            })

    msg.extend(_validate_amalgamation_type(amalgamation_type,
                                           amalgamating_business_roles,
                                           is_any_foreign,
                                           is_any_expro_a,
                                           amalgamating_businesses_path))

    if legal_type == Business.LegalTypes.BC_CCC.value and not is_any_business[Business.LegalTypes.BC_CCC.value]:
        msg.append({
            "error": ("A BC Community Contribution Company must amalgamate to form "
                      "a new BC Community Contribution Company."),
            "path": amalgamating_businesses_path
        })
    elif (legal_type in [Business.LegalTypes.BC_CCC.value, Business.LegalTypes.BC_ULC_COMPANY.value] and
          is_any_expro_a and is_any_bc_company):
        msg.append({
            "error": ("An extra-Pro cannot amalgamate with anything to become "
                      "a BC Unlimited Liability Company or a BC Community Contribution Company."),
            "path": amalgamating_businesses_path
        })

    return msg


def _validate_foreign_businesses(  # noqa: PLR0913
        is_staff,
        is_any_bc_company,
        is_any_ulc,
        legal_type,
        foreign_legal_name,
        amalgamating_business,
        amalgamating_business_path) -> list:
    msg = []

    if is_staff:
        msg.extend(validate_foreign_jurisdiction(amalgamating_business["foreignJurisdiction"],
                                                 f"{amalgamating_business_path}/foreignJurisdiction",
                                                 is_region_bc_valid=False,
                                                 is_region_for_us_required=False))

    msg.extend(_validate_foreign_rules(is_staff,
                                       is_any_bc_company,
                                       is_any_ulc,
                                       legal_type,
                                       foreign_legal_name,
                                       amalgamating_business["role"],
                                       amalgamating_business_path))

    return msg


def _validate_foreign_rules(  # noqa: PLR0913
        is_staff,
        is_any_bc_company,
        is_any_ulc,
        legal_type,
        legal_name,
        role,
        amalgamating_business_path) -> list:
    """Validate the rules shared by foreign corporations and extraprovincial (A) corps."""
    msg = []

    if is_staff:
        if legal_type == Business.LegalTypes.BC_ULC_COMPANY.value and is_any_bc_company:
            msg.append({
                "error": (f"{legal_name} foreign corporation must not amalgamate with "
                          "a BC company to form a BC Unlimited Liability Company."),
                "path": amalgamating_business_path
            })

        if is_any_ulc:
            msg.append({
                "error": ("A BC Unlimited Liability Company cannot amalgamate with "
                          f"a foreign company {legal_name}."),
                "path": amalgamating_business_path
            })

        if role in [AmalgamatingBusiness.Role.primary.name,
                    AmalgamatingBusiness.Role.holding.name]:
            msg.append({
                "error": f"A {legal_name} foreign corporation cannot be marked as Primary or Holding.",
                "path": amalgamating_business_path
            })
    elif flags.is_on("enabled-deeper-permission-action"):
        permission_error = PermissionService.check_user_permission(
            ListActionsPermissionsAllowed.AML_OVERRIDES.value,
            message="Permission Denied - You do not have permissions to amalgamate a foreign corporation."
        )
        if permission_error:
            msg.append({
                "error": permission_error.msg[0].get("message"),
                "path": amalgamating_business_path
            })
            return msg
    else:
        msg.append({
            "error": (f"{legal_name} foreign corporation cannot "
                    "be amalgamated except by Registries staff."),
            "path": amalgamating_business_path
        })

    return msg


def _check_aml_permission_or_default_error(msg: list, message: str, default_error: dict) -> bool:
        if flags.is_on("enabled-deeper-permission-action"):
            permission_error = PermissionService.check_user_permission(
                ListActionsPermissionsAllowed.AML_OVERRIDES.value,
                message=message
            )
            if permission_error:
                msg.append({
                    "error": permission_error.msg[0].get("message"),
                    "path": default_error.get("path")
                })
                return True
        else:
            msg.append(default_error)
            return True
        return False

def _business_info_from_lear(business: Business, is_staff: bool) -> dict:
    """Normalize a LEAR business row to the snapshot shape shared by TING validation."""
    return {
        "state": business.state.name if business.state else None,
        "hasFutureEffectiveFiling": _has_pending_filing(business),
        "adminFreeze": business.admin_freeze,
        # good_standing costs a filing-history query and only the non-staff checks read it
        "goodStanding": True if is_staff else business.good_standing,
    }


def _validate_amalgamating_business(  # pylint: disable=too-many-arguments
        identifier,
        business_info,
        account_id,
        is_staff,
        amalgamating_business_path) -> list:
    """Validate a TING business from its normalized info (LEAR row or COLIN snapshot)."""
    msg = []
    if business_info.get("state") == Business.State.HISTORICAL.name:
        msg.append({
            "error": f"Cannot amalgamate with {identifier} which is in historical state.",
            "path": amalgamating_business_path
        })
    elif business_info.get("hasFutureEffectiveFiling"):
        msg.append({
            "error": f"{identifier} has a draft, pending or future effective filing.",
            "path": amalgamating_business_path
        })
    elif Business.is_pending_amalgamating_business(identifier):
        msg.append({
            "error": f"{identifier} is part of a future effective amalgamation filing.",
            "path": amalgamating_business_path
        })

    if business_info.get("adminFreeze"):
        msg.append({
            "error": f"{identifier} is frozen.",
            "path": amalgamating_business_path
        })

    if not is_staff:
        if not _is_business_affliated(identifier, account_id):
            error = _check_aml_permission_or_default_error(
                msg,
                "Permission Denied - You do not have permissions to amalgamate an unaffiliated business.",
                {
                    "error": (f"{identifier} is not affiliated with the currently "
                              "selected BC Registries account."),
                    "path": amalgamating_business_path
                }
            )
            if error:
                return msg

        if not business_info.get("goodStanding"):
            error = _check_aml_permission_or_default_error(
                msg,
                "Permission Denied - You do not have permissions to amalgamate a business not in good standing.",
                {
                    "error": f"{identifier} is not in good standing.",
                    "path": amalgamating_business_path
                }
            )
            if error:
                return msg

    return msg


def _find_colin_business(identifier: str) -> tuple:
    """Return (colin business dict | None, fetch_failed) for a business not found in LEAR."""
    snapshot_json, status_code = colin.get_snapshot(identifier)
    if status_code is None or status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
        return None, True
    if status_code != HTTPStatus.OK:
        return None, False
    if snapshot_json is None:
        # a 200 with a non-JSON body is an infrastructure failure - retryable, not "not found"
        return None, True

    business_json = snapshot_json.get("business") or {}
    if not business_json.get("legalName") or business_json.get("legalType") not in COLIN_AMALGAMATION_LEGAL_TYPES:
        return None, False
    return business_json, False


def validate_primary_or_holding_match(amalgamation_json, filing_type, amalgamation_type) -> list:
    """Ensure the filing has the primary/holding business's current data.

    A short-form amalgamation adopts the primary/holding business's legal name, directors,
    offices and share structure. The filing must record exactly what will be applied, so the
    submitted sections are compared against that business's current data (LEAR row or COLIN
    snapshot). A mismatch means the draft is stale and must be refreshed.
    """
    filing_section = amalgamation_json.get("filing", {}).get(filing_type, {})
    role = _primary_or_holding_role(amalgamation_type)
    source = _find_primary_or_holding_data(filing_section, role)
    if source is None:
        # a missing or unresolvable primary/holding business is reported by the TING validations
        return []

    msg = []
    section_path = f"/filing/{filing_type}"
    refresh_hint = "Refresh the draft with the business's current data."

    if legal_name := filing_section.get("nameRequest", {}).get("legalName"):
        if legal_name.strip() != ((source.get("business") or {}).get("legalName") or "").strip():
            msg.append({
                "error": f"Legal name does not match the {role} business. {refresh_hint}",
                "path": f"{section_path}/nameRequest/legalName"
            })
    else:
        msg.append({
            "error": f"Legal name of the {role} business is required for a short-form amalgamation.",
            "path": f"{section_path}/nameRequest/legalName"
        })

    if offices := filing_section.get("offices"):
        if _norm_offices(offices) != _norm_offices(source.get("offices")):
            msg.append({
                "error": f"Offices do not match the {role} business's current offices. {refresh_hint}",
                "path": f"{section_path}/offices"
            })
    else:
        msg.append({
            "error": f"Offices of the {role} business are required for a short-form amalgamation.",
            "path": f"{section_path}/offices"
        })

    if share_structure := filing_section.get("shareStructure"):
        if _norm_share_classes(share_structure.get("shareClasses")) != _norm_share_classes(source.get("shareClasses")):
            msg.append({
                "error": f"Share structure does not match the {role} business's current share structure. "
                         f"{refresh_hint}",
                "path": f"{section_path}/shareStructure"
            })
        source_dates = [resolution.get("date") for resolution in source.get("resolutions") or []]
        if _norm_resolution_dates(share_structure.get("resolutionDates")) != _norm_resolution_dates(source_dates):
            msg.append({
                "error": f"Resolution dates do not match the {role} business's current resolution dates. "
                         f"{refresh_hint}",
                "path": f"{section_path}/shareStructure/resolutionDates"
            })
    else:
        msg.append({
            "error": f"Share structure of the {role} business is required for a short-form amalgamation.",
            "path": f"{section_path}/shareStructure"
        })

    if _norm_directors(filing_section.get("parties")) != _norm_directors(source.get("parties")):
        msg.append({
            "error": f"Directors do not match the {role} business's current directors. {refresh_hint}",
            "path": f"{section_path}/parties"
        })

    return msg


def _find_primary_or_holding_data(filing_section: dict, role: str) -> dict | None:
    """Return the primary/holding business's current data in the same shape as COLIN snapshot."""
    entry = next((business_json for business_json in filing_section.get("amalgamatingBusinesses") or []
                  if business_json.get("role") == role and not business_json.get("foreignJurisdiction")), None)
    if not (entry and (identifier := entry.get("identifier"))):
        return None

    if business := Business.find_by_identifier(identifier):
        return _full_business_data_from_lear(business)

    snapshot_json, status_code = colin.get_snapshot(identifier)
    if status_code == HTTPStatus.OK:
        return snapshot_json or None
    return None


def _full_business_data_from_lear(business: Business) -> dict:
    """Return the business's current snapshot data (what the filer applies for amalgamation)."""
    offices = {}
    for office in business.offices.all():
        if office.office_type in [OfficeType.REGISTERED, OfficeType.RECORDS]:
            offices[office.office_type] = {
                f"{address.address_type}Address": address.json for address in office.addresses
            }
    directors = []
    for party_role in PartyRole.get_active_directors(business.id, datetime.now(UTC).date()):
        # party_role.json carries a singular 'role' - reshape to the snapshot's roles list
        director = party_role.json
        director["roles"] = [{"roleType": "Director"}]
        directors.append(director)
    return {
        "business": {"legalName": business.legal_name},
        "parties": directors,
        "offices": offices,
        "shareClasses": [share_class.json for share_class in business.share_classes.all()],
        "resolutions": [{"date": resolution.resolution_date.isoformat()} for resolution in business.resolutions],
    }


_ADDRESS_MATCH_FIELDS: Final = ("streetAddress", "streetAddressAdditional", "addressCity", "addressRegion",
                                "addressCountry", "postalCode", "deliveryInstructions")


def _norm_value(value):
    """Strip strings and collapse empties so '' and a missing key compare equal."""
    if isinstance(value, str):
        value = value.strip()
    return value if value not in ("", None) else None


def _norm_number(value):
    """Coerce numbers so 1, 1.0 and '1' compare equal."""
    try:
        return float(value) if value not in ("", None) else None
    except (TypeError, ValueError):
        return _norm_value(value)


def _norm_address(address: dict | None) -> tuple | None:
    if not address:
        return None
    return tuple(_norm_value(address.get(field)) for field in _ADDRESS_MATCH_FIELDS)


def _norm_offices(offices: dict | None) -> dict:
    return {
        office_type: (_norm_address(office.get("deliveryAddress")), _norm_address(office.get("mailingAddress")))
        for office_type, office in (offices or {}).items()
        if office_type in [OfficeType.REGISTERED, OfficeType.RECORDS]
    }


def _norm_directors(parties: list | None) -> set:
    directors = set()
    for party in parties or []:
        if not any((party_role.get("roleType") or "").lower() == PartyRole.RoleTypes.DIRECTOR.value
                   for party_role in party.get("roles") or []):
            continue
        officer = party.get("officer") or {}
        directors.add((
            _norm_value(officer.get("firstName")),
            _norm_value(officer.get("middleInitial")),
            _norm_value(officer.get("lastName")),
            _norm_value(officer.get("organizationName")),
            _norm_address(party.get("deliveryAddress")),
        ))
    return directors


def _norm_share_classes(share_classes: list | None) -> set:
    # Can skip:
    # - ids (DB artifact)
    # - priority (is synthesized from the COLIN class id)
    # - currencyAdditional (is only set with currency OTHER)
    return {
        (
            _norm_value(share_class.get("name")),
            bool(share_class.get("hasMaximumShares")),
            _norm_number(share_class.get("maxNumberOfShares")),
            bool(share_class.get("hasParValue")),
            _norm_number(share_class.get("parValue")),
            _norm_value(share_class.get("currency")),
            bool(share_class.get("hasRightsOrRestrictions")),
            tuple(sorted((_norm_share_series(series) for series in share_class.get("series") or []), key=repr)),
        )
        for share_class in share_classes or []
    }


def _norm_share_series(series: dict) -> tuple:
    return (
        _norm_value(series.get("name")),
        bool(series.get("hasMaximumShares")),
        _norm_number(series.get("maxNumberOfShares")),
        bool(series.get("hasRightsOrRestrictions")),
    )


def _norm_resolution_dates(dates: list | None) -> set:
    """Return the dates as YYYY-MM-DD strings (tolerates datetimes and date objects)."""
    return {str(date)[:10] for date in dates or [] if date}


def _validate_amalgamation_type(  # pylint: disable=too-many-arguments
        amalgamation_type,
        amalgamating_business_roles,
        is_any_foreign,
        is_any_expro_a,
        amalgamating_businesses_path) -> list:
    msg = []
    regular_amalgamation_minimum: Final = 2
    if (amalgamation_type == Amalgamation.AmalgamationTypes.regular.name and
        not (amalgamating_business_roles[AmalgamatingBusiness.Role.amalgamating.name] >=
             regular_amalgamation_minimum and
             amalgamating_business_roles[AmalgamatingBusiness.Role.holding.name] == 0 and
             amalgamating_business_roles[AmalgamatingBusiness.Role.primary.name] == 0)):
        msg.append({
            "error": "Regular amalgamation must have 2 or more amalgamating businesses.",
            "path": amalgamating_businesses_path
        })
    elif amalgamation_type == Amalgamation.AmalgamationTypes.horizontal.name:
        if (is_any_foreign or is_any_expro_a):
            msg.append({
                "error": "A foreign corporation or extra-Pro cannot be part of a Horizontal amalgamation.",
                "path": amalgamating_businesses_path
            })

        if not (amalgamating_business_roles[AmalgamatingBusiness.Role.primary.name] == 1 and
                amalgamating_business_roles[AmalgamatingBusiness.Role.amalgamating.name] >= 1 and
                amalgamating_business_roles[AmalgamatingBusiness.Role.holding.name] == 0):
            msg.append({
                "error": "Horizontal amalgamation must have a primary and 1 or more amalgamating businesses.",
                "path": amalgamating_businesses_path
            })
    elif (amalgamation_type == Amalgamation.AmalgamationTypes.vertical.name and
          not (amalgamating_business_roles[AmalgamatingBusiness.Role.holding.name] == 1 and
               amalgamating_business_roles[AmalgamatingBusiness.Role.amalgamating.name] >= 1 and
               amalgamating_business_roles[AmalgamatingBusiness.Role.primary.name] == 0)):
        msg.append({
            "error": "Vertical amalgamation must have a holding and 1 or more amalgamating businesses.",
            "path": amalgamating_businesses_path
        })

    return msg


def _is_business_affliated(identifier, account_id):
    return bool(
        (account_response := AccountService.get_account_by_affiliated_identifier(identifier, flags)) and
        (orgs := account_response.get("orgs")) and
        any(str(org.get("id")) == account_id for org in orgs)
    )


def _has_pending_filing(amalgamating_business: Business):
    return bool(Filing.get_filings_by_status(amalgamating_business.id,
                                             [Filing.Status.DRAFT.value,
                                              Filing.Status.PENDING.value,
                                              Filing.Status.PAID.value]))


def validate_party(filing: dict, amalgamation_type, filing_type) -> list:
    """Validate party."""
    msg = []
    completing_parties = 0
    director_parties = 0
    invalid_roles = set()
    parties = filing["filing"][filing_type]["parties"]
    for party in parties:  # pylint: disable=too-many-nested-blocks;
        for role in party.get("roles", []):
            role_type = role.get("roleType").lower().replace(" ", "_")
            if role_type == PartyRole.RoleTypes.COMPLETING_PARTY.value:
                completing_parties += 1
            elif role_type == PartyRole.RoleTypes.DIRECTOR.value:
                director_parties += 1
            else:
                invalid_roles.add(role_type)

    if invalid_roles:
        err_path = f"/filing/{filing_type}/parties/roles"
        msg.append({
            "error": f'Invalid party role(s) provided: {", ".join(sorted(invalid_roles))}.',
            "path": err_path
        })

    party_path = f"/filing/{filing_type}/parties"
    if (amalgamation_type == Amalgamation.AmalgamationTypes.regular.name and
            (completing_parties < 1 or director_parties < 1)):
        msg.append({"error": "At least one Director and a Completing Party is required.", "path": party_path})
    elif (amalgamation_type in [Amalgamation.AmalgamationTypes.vertical.name,
                                Amalgamation.AmalgamationTypes.horizontal.name] and
          completing_parties == 0):
        msg.append({"error": "A Completing Party is required.", "path": party_path})

    return msg


def validate_amalgamation_court_order(filing: dict, filing_type) -> list:
    """Validate court order."""
    if court_order := filing.get("filing", {}).get(filing_type, {}).get("courtOrder", None):
        court_order_path: Final = f"/filing/{filing_type}/courtOrder"
        return validate_court_order(court_order_path, court_order)
    return []
