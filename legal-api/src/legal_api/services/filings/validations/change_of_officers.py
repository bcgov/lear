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

from flask_babel import _ as babel

from business_model.models import Business
from legal_api.errors import Error
from legal_api.services.filings.validations.common_validations import (
    validate_parties_addresses,
    validate_parties_countries,
)


def validate(business: Business, coo: dict) -> Error:
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


def validate_relationship_addresses(coo: dict) -> list:
    """Return an error message if the officers address are invalid.

    Address must contain a valid ISO-2 valid country.
    """
    msg = []

    filing_type = "changeOfOfficers"
    msg.extend(validate_parties_addresses(coo, filing_type, "relationships"))
    msg.extend(validate_parties_countries(coo, filing_type, "relationships"))

    return msg
