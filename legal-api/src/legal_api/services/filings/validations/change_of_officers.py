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
"""Validation for the Change of Directors filing."""

from http import HTTPStatus
from typing import Dict, List

import pycountry
from flask_babel import _ as babel  # noqa: N813, I004, I001; importing camelcase '_' as a name

from legal_api.errors import Error
from legal_api.models import Address, Business
from legal_api.services.filings.validations.common_validations import validate_parties_addresses
from legal_api.services.utils import get_str
# noqa: I003; needed as the linter gets confused from the babel override above.


def validate(business: Business, coo: Dict) -> Error:
    """Validate the Change of Officers filing."""
    if not business or not coo:
        return Error(HTTPStatus.BAD_REQUEST, [{"error": babel("A valid business and filing are required.")}])

    msg = []

    msg_officers_addresses = validate_relationship_addresses(coo)
    if msg_officers_addresses:
        msg += msg_officers_addresses

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def validate_relationship_addresses(coo: Dict) -> List:
    """Return an error message if the officers address are invalid.

    Address must contain a valid ISO-2 valid country.
    """
    msg = []

    filing_type = "changeOfOfficers"
    msg.extend(validate_parties_addresses(coo, filing_type, "relationships"))

    relationships = coo["filing"][filing_type]["relationships"]

    for idx, rel in enumerate(relationships):  # pylint: disable=too-many-nested-blocks;  # noqa: E501 review this when implementing corrections
        for address_type in Address.JSON_ADDRESS_TYPES:
            if address_type in rel:
                try:
                    country = get_str(rel, f"/{address_type}/addressCountry")
                    _ = pycountry.countries.search_fuzzy(country)[0].alpha_2

                except LookupError:
                    msg.append(
                        {
                            "error": babel("Address Country must resolve to a valid ISO-2 country."),
                            "path": f"/filing/changeOfOfficers/relationships/{idx}/{address_type}/addressCountry",
                        }
                    )
    return msg
