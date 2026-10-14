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

from business_model.models import Address, Business, OfficeType, PartyRole
from legal_api.services.warnings.business.business_checks import (
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

    result.extend(check_offices(business))
    result.extend(check_directors(business))
    result.extend(check_amalgamating_business(business, is_staff))
    result.extend(check_transition_application(business))

    return result


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
        result.extend(_with_data(check_address(mailing_address, Address.MAILING, referer), data))

        delivery_address = next((x for x in addresses if x.address_type == Address.DELIVERY), None)
        result.extend(_with_data(check_address(delivery_address, Address.DELIVERY, referer), data))

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
            check_address(party.mailing_address, Address.MAILING, BusinessWarningReferers.DIRECTOR), data))
        result.extend(_with_data(
            check_address(party.delivery_address, Address.DELIVERY, BusinessWarningReferers.DIRECTOR), data))

    return result


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
