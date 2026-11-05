# Copyright © 2024 Province of British Columbia
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

"""Business checks for corps."""

import pycountry

from business_model.models import Address, Business, OfficeType, PartyRole
from legal_api.services import flags
from legal_api.services.request_context import get_request_context
from legal_api.services.utils import CANADIAN_POSTAL_CODE_REGEX
from legal_api.services.warnings.business.business_checks import (
    OFFICE_REFERERS,
    WARNING_MESSAGE_BASE,
    BusinessWarningCodes,
    BusinessWarningReferers,
    WarningType,
)
from legal_api.services.warnings.business.business_checks.firms import check_address

# office type -> (warning referer, missing office code, missing office message)
OFFICE_CHECKS = {
    OfficeType.REGISTERED: (BusinessWarningReferers.REGISTERED_OFFICE,
                            BusinessWarningCodes.NO_REGISTERED_OFFICE,
                            "A registered office is required."),
    OfficeType.RECORDS: (BusinessWarningReferers.RECORDS_OFFICE,
                         BusinessWarningCodes.NO_RECORDS_OFFICE,
                         "A records office is required.")
}


def check_business(business: Business, is_staff: bool = False) -> list:
    """Check business data."""
    result = []

    if is_review_imported_data_enabled():
        # missing address warnings are only actionable through the reviewImportedData filing (they block correction),
        # so emit them only while that filing is enabled
        result.extend(check_offices(business))
        result.extend(check_directors(business))
    result.extend(check_amalgamating_business(business, is_staff))
    result.extend(check_transition_application(business))

    return result


def is_review_imported_data_enabled() -> bool:
    """Return True when the reviewImportedData filing is enabled by the enable-new-feature flag."""
    request_context = get_request_context()
    enabled_features = flags.value("enable-new-feature", request_context.user, request_context.account_id) or []
    return "reviewImportedData" in enabled_features


def _with_data(warnings: list, data: dict) -> list:
    """Return copies of the warnings carrying ``data`` so the UI can identify the office/party to fix."""
    return [{**warning, "data": data} for warning in warnings]


def check_offices(business: Business) -> list:
    """Check for missing registered office and records office address data."""
    result = []

    for office_type, (referer, no_office_code, no_office_message) in OFFICE_CHECKS.items():
        data = {"officeType": office_type}
        office = business.offices \
            .filter_by(office_type=office_type, deactivated_date=None) \
            .first()

        if not office:
            result.append({
                **WARNING_MESSAGE_BASE,
                "code": no_office_code,
                "message": no_office_message,
                "data": data
            })
            continue

        addresses = office.addresses.all()
        mailing_address = next((x for x in addresses if x.address_type == Address.MAILING), None)
        result.extend(_with_data(check_address_data(mailing_address, Address.MAILING, referer), data))

        delivery_address = next((x for x in addresses if x.address_type == Address.DELIVERY), None)
        result.extend(_with_data(check_address_data(delivery_address, Address.DELIVERY, referer), data))

    return result


def check_directors(business: Business) -> list:
    """Check for missing address data on active directors."""
    result = []

    director_roles = business.party_roles \
        .filter(PartyRole.role == PartyRole.RoleTypes.DIRECTOR.value) \
        .filter(PartyRole.cessation_date.is_(None))

    for party_role in director_roles:
        party = party_role.party
        data = {"partyId": party.id}
        result.extend(_with_data(
            check_address_data(party.mailing_address, Address.MAILING, BusinessWarningReferers.DIRECTOR), data))
        result.extend(_with_data(
            check_address_data(party.delivery_address, Address.DELIVERY, BusinessWarningReferers.DIRECTOR), data))

    return result


def check_address_data(address: Address, address_type: str, referer: BusinessWarningReferers) -> list:
    """Check a corp office / director address for missing and invalid data."""
    return [
        *check_address(address, address_type, referer),
        *check_address_validity(address, address_type, referer),
    ]


def check_address_validity(address: Address, address_type: str, referer: BusinessWarningReferers) -> list:
    """Check for address data that is present but would be rejected by the reviewImportedData filing.

    Mirrors that filing's validation (validate_offices with bc_req, validate_parties_countries and
    _validate_postal_code) so a field that cannot pass it is flagged, and so unlocked for editing.
    """
    if not address:
        return []

    is_office_delivery = referer in OFFICE_REFERERS and address_type == Address.DELIVERY
    country_code = _get_country_code(address.country)
    invalid_fields = []

    # an office mailing address may be anywhere and its country is not checked by the filing
    if address.country and (
            (is_office_delivery and country_code != "CA")
            or (referer == BusinessWarningReferers.DIRECTOR and not country_code)):
        invalid_fields.append(("COUNTRY", "Country"))

    if _is_invalid_postal_code(address.postal_code, country_code):
        invalid_fields.append(("POSTAL_CODE", "Postal code"))

    if is_office_delivery and address.region and address.region != "BC":
        invalid_fields.append(("REGION", "Region"))

    label = referer.value.replace("_", " ").lower()
    return [{
        **WARNING_MESSAGE_BASE,
        "code": BusinessWarningCodes(f"INVALID_{referer.value}_{address_type.upper()}_ADDRESS_{field}"),
        "message": f"{field_label} is invalid for {label} {address_type} address.",
    } for field, field_label in invalid_fields]


def _get_country_code(country: str | None) -> str | None:
    """Return the ISO-2 code for a country, or None when it is missing or cannot be resolved."""
    if not country:
        return None
    try:
        return pycountry.countries.search_fuzzy(country)[0].alpha_2
    except LookupError:
        return None


def _is_invalid_postal_code(postal_code: str | None, country_code: str | None) -> bool:
    """Return True for a postal code the filing would reject: stray whitespace or not Canadian format in CA."""
    if not postal_code:
        return False
    return postal_code != postal_code.strip() or (
        country_code == "CA" and not CANADIAN_POSTAL_CODE_REGEX.match(postal_code))


def check_transition_application(business: Business) -> list:
    """Check if a business is currently pending a post restoration transition application."""
    result = []

    is_transition_needed_but_not_filed = business.transition_needed_but_not_filed()
    if is_transition_needed_but_not_filed:
        result.append({
            "code": BusinessWarningCodes.TRANSITION_NOT_FILED.value,
            "message": "This Business requires a post restoration transition application to be filed.",
            "warningType": WarningType.NOT_IN_GOOD_STANDING
        })

    return result


def check_amalgamating_business(business: Business, is_staff: bool = False) -> list:
    """Check if business is currently pending amalgamation."""
    result = []

    filing = Business.is_pending_amalgamating_business(business.identifier)

    # Check if a matching filing was found and if its effective date is greater than payment completion date
    if filing and filing.effective_date > filing.payment_completion_date:
        amalgamation_application = filing.filing_json["filing"]["amalgamationApplication"]
        name_request = amalgamation_application.get("nameRequest", {})
        # legalName is only present when the resulting business will be named
        resulting_business_name = name_request.get("legalName")

        warning = {
            "code": "AMALGAMATING_BUSINESS",
            "message": "This business is part of a future effective amalgamation.",
            "warningType": WarningType.FUTURE_EFFECTIVE_AMALGAMATION,
            "data": {
                "amalgamationDate": filing.effective_date,
                "amalgamatingBusinesses": amalgamation_application["amalgamatingBusinesses"]
            }
        }
        if resulting_business_name:
            warning["data"]["resultingBusinessName"] = resulting_business_name
        if is_staff:
            warning["data"]["filingId"] = filing.id
            warning["data"]["resultingBusinessIdentifier"] = filing.filing_json["filing"]["business"]["identifier"]
        result.append(warning)

    return result
