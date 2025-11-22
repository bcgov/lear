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
"""Validation for the Change of Directors filing."""
from http import HTTPStatus

import pycountry
from flask_babel import _ as babel  # noqa: N813, I004, I001; importing camelcase '_' as a name

from legal_api.errors import Error
from legal_api.models import Address, Business, Filing
from legal_api.services.filings.validations.common_validations import validate_parties_addresses
from legal_api.services.utils import get_str
from legal_api.utils.datetime import datetime
from legal_api.utils.legislation_datetime import LegislationDatetime

# noqa: I003; needed as the linter gets confused from the babel override above.


def validate(business: Business, cod: dict) -> Error:
    """Validate the Change of Directors filing."""
    if not business or not cod:
        return Error(HTTPStatus.BAD_REQUEST, [{"error": babel("A valid business and filing are required.")}])
    msg = []

    msg_directors_addresses = validate_directors_addresses(business, cod)
    if msg_directors_addresses:
        msg += msg_directors_addresses

    msg_effective_date = validate_effective_date(business, cod)
    if msg_effective_date:
        msg += msg_effective_date

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def validate_directors_addresses(business: Business, cod: dict) -> list:
    """Return an error message if the directors address are invalid.

    Address must contain a valid ISO-2 valid country.
    """
    msg = []

    filing_type = "changeOfDirectors"
    msg.extend(validate_parties_addresses(cod, filing_type, "directors"))

    directors = cod["filing"][filing_type]["directors"]

    for idx, director in enumerate(directors):  # pylint: disable=too-many-nested-blocks;
        for address_type in Address.JSON_ADDRESS_TYPES:
            if address_type in director:
                try:
                    country = get_str(director, f"/{address_type}/addressCountry")
                    _ = pycountry.countries.search_fuzzy(country)[0].alpha_2

                except LookupError:
                    msg.append({"error": babel("Address Country must resolve to a valid ISO-2 country."),
                                "path": f"/filing/changeOfDirectors/directors/{idx}/{address_type}/addressCountry"})
            elif business.legal_type in Business.CORPS:
                msg.append({
                    "error": f"missing {address_type}",
                    "path": f"/filing/changeOfDirectors/directors/{idx}/{address_type}"
                })
    return msg


def validate_effective_date(business: Business, cod: dict) -> list:
    """Return an error or warning message based on the effective date validation rules.

    Rules: (text from the BA rules document)
        - The effective date of change cannot be in the future.
        - The effective date cannot be a date prior to their Incorporation Date.
        - The effective date of change cannot be a date that is farther in the past
            than a previous COD filing (standalone or AR).
        - The effective date can be the same effective date as another COD filing
            (standalone or AR). If this is the case:
        - COD filing that was filed most recently is the most current director information.
    """
    msg = []

    # get effective datetime string from filing
    try:
        effective_datetime_str = cod["filing"]["header"]["effectiveDate"]
    except KeyError:
        return {"error": babel("No effective date provided.")}

    # convert string to datetime
    try:
        effective_datetime_utc = datetime.fromisoformat(effective_datetime_str)
    except ValueError:
        return {"error": babel("Invalid ISO format for effective date.")}

    # check if effective datetime is in the future
    if effective_datetime_utc > datetime.utcnow():
        msg.append({"error": babel("Filing cannot have a future effective date.")})

    # convert to legislation timezone and then get date only
    effective_date_leg = LegislationDatetime.as_legislation_timezone(effective_datetime_utc).date()

    # check if effective date is before their incorporation date
    founding_date_leg = LegislationDatetime.as_legislation_timezone(business.founding_date).date()
    if effective_date_leg < founding_date_leg:
        msg.append({"error": babel("Effective date cannot be before businesses founding date.")})

    # check if effective date is before their most recent COD or AR date
    last_cod_filing = Filing.get_most_recent_legal_filing(business.id,
                                                          Filing.FILINGS["changeOfDirectors"]["name"])
    if last_cod_filing:
        last_cod_date_leg = LegislationDatetime.as_legislation_timezone(last_cod_filing.effective_date).date()
        if effective_date_leg < last_cod_date_leg:
            msg.append({"error": babel("Effective date cannot be before another Change of Director filing.")})

    return msg
