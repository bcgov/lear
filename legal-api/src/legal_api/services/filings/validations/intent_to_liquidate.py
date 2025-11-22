# Copyright © 2025 Province of British Columbia
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
"""Validation for the Intent to Liquidate filing."""
from http import HTTPStatus
from typing import Optional

from flask_babel import _ as babel

from legal_api.errors import Error
from legal_api.models import Business
from legal_api.services.filings.validations.common_validations import (
    validate_court_order,
    validate_offices_addresses,
    validate_parties_addresses,
)
from legal_api.services.utils import get_date
from legal_api.utils.legislation_datetime import LegislationDatetime


def validate(business: Business, filing_json: dict) -> Optional[Error]:
    """Validate the Intent to Liquidate filing."""
    if not business or not filing_json:
        return Error(HTTPStatus.BAD_REQUEST, [{"error": babel("A valid business and filing are required.")}])

    msg = []
    filing_type = "intentToLiquidate"

    err = validate_liquidation_date(filing_json, business)
    if err:
        msg.extend(err)

    err = validate_parties(filing_json)
    if err:
        msg.extend(err)
    msg.extend(validate_parties_addresses(filing_json, filing_type))

    err = validate_offices(filing_json)
    if err:
        msg.extend(err)
    msg.extend(validate_offices_addresses(filing_json, filing_type))

    err = validate_intent_court_order(filing_json)
    if err:
        msg.extend(err)

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def validate_liquidation_date(filing_json: dict, business: Business = None) -> Optional[list]:
    """Validate the date of commencement of liquidation."""
    msg = []
    liquidation_date_path = "/filing/intentToLiquidate/dateOfCommencementOfLiquidation"

    liquidation_date = get_date(filing_json, liquidation_date_path)
    # Validate that liquidation date is later than founding date
    if business and business.founding_date:
        founding_date_leg = LegislationDatetime.as_legislation_timezone(business.founding_date).date()
        if liquidation_date <= founding_date_leg:
            msg.append({
                "error": babel("Date of commencement of liquidation must be later than the business founding date."),
                "path": liquidation_date_path
            })

    return msg if msg else None


def validate_parties(filing_json: dict) -> Optional[list]:
    """Validate the parties in the intent to liquidate filing."""
    msg = []
    parties_path = "/filing/intentToLiquidate/parties"

    parties = filing_json.get("filing", {}).get("intentToLiquidate", {}).get("parties", [])

    liquidator_count = 0
    invalid_roles = set()

    for party in parties:
        roles = party.get("roles", [])

        for role in roles:
            role_type = role.get("roleType")
            # Check for liquidator role
            if role_type == "Liquidator":
                liquidator_count += 1
            else:
                invalid_roles.add(role_type)

    if invalid_roles:
        msg.append({
            "error": f'Invalid party role(s) provided: {", ".join(sorted(invalid_roles))}.',
            "path": f"{parties_path}/roles"
        })

    if liquidator_count == 0:
        msg.append({"error": babel("At least one liquidator is required."), "path": parties_path})

    return msg if msg else None


def validate_offices(filing_json: dict) -> Optional[list]:
    """Validate the liquidation office."""
    msg = []
    offices_path = "/filing/intentToLiquidate/offices"

    offices = filing_json.get("filing", {}).get("intentToLiquidate", {}).get("offices", {})
    liquidation_office = offices.get("liquidationOffice")

    # Validate liquidation office addresses
    for address_type in ["mailingAddress", "deliveryAddress"]:
        address = liquidation_office.get(address_type)
        if address:
            address_path = f"{offices_path}/liquidationOffice/{address_type}"

            region = address.get("addressRegion")
            if region and region != "BC":
                msg.append({"error": babel("Address Region must be 'BC'."),
                            "path": f"{address_path}/addressRegion"})

            country = address.get("addressCountry")
            if country and country != "CA":
                msg.append({"error": babel("Address Country must be 'CA'."),
                            "path": f"{address_path}/addressCountry"})

    return msg if msg else None


def validate_intent_court_order(filing_json: dict) -> Optional[list]:
    """Validate the court order if present."""
    msg = []
    court_order = filing_json.get("filing", {}).get("intentToLiquidate", {}).get("courtOrder")

    if court_order:
        court_order_path = "/filing/intentToLiquidate/courtOrder"
        err = validate_court_order(court_order_path, court_order)
        if err:
            msg.extend(err)

    return msg if msg else None
