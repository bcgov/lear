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
from typing import Dict, List

import pycountry
from flask_babel import _ as babel  # noqa: N813, I004, I001; importing camelcase '_' as a name

from legal_api.errors import Error
from legal_api.models import Address, Business, Filing
from legal_api.services.filings.utils import get_str
from legal_api.utils.datetime import datetime
# noqa: I003; needed as the linter gets confused from the babel override above.


def validate(business: Business, cod: Dict) -> Error:
    """Validate the Change of Directors filing."""
    if not business or not cod:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid business and filing are required.')}])
    msg = []

    msg_directors_addresses = validate_directors_addresses(cod)
    if msg_directors_addresses:
        msg += msg_directors_addresses

    msg_effective_date = validate_effective_date(business, cod)
    if msg_effective_date:
        msg += msg_effective_date

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def validate_directors_addresses(cod: Dict) -> List:
    """Return an error message if the directors address are invalid.

    Address must contain a valid ISO-2 valid country.
    """
    msg = []

    directors = cod['filing']['changeOfDirectors']['directors']

    for idx, director in enumerate(directors):  # pylint: disable=too-many-nested-blocks;  # noqa: E501 review this when implementing corrections
        for address_type in Address.JSON_ADDRESS_TYPES:
            if address_type in director:
                try:
                    country = get_str(director, f'/{address_type}/addressCountry')
                    _ = pycountry.countries.search_fuzzy(country)[0].alpha_2

                except LookupError:
                    msg.append({'error': babel('Address Country must resolve to a valid ISO-2 country.'),
                                'path': f'/filing/changeOfDirectors/directors/{idx}/{address_type}/addressCountry'})
    return msg


def validate_effective_date(business: Business, cod: Dict) -> List:
    """Return an error or warning message based on the effective date validation rules.

    Rules:
        - The effective date of change cannot be in the future.
        - The effective date cannot be a date prior to their Incorporation Date
        - The effective date of change cannot be a date that is farther in the past
            as a previous COD filing (Standalone or AR).
        - The effective date can be the same effective date as another COD filing
            (standalone OR AR). If this is the case:
        - COD filing that was filed most recently as the most current director information.
    """
    try:
        filing_effective_date = cod['filing']['header']['effectiveDate']
    except KeyError:
        try:
            # we'll assume the filing is at 0 hours UTC
            filing_effective_date = cod['filing']['header']['date'] + 'T00:00:00+00:00'
        except KeyError:
            return {'error': babel('No effective_date or filing date provided.')}

    try:
        effective_date = datetime.fromisoformat(filing_effective_date)
    except ValueError:
        return {'error': babel('Invalid ISO format for effective_date or filing date.')}

    msg = []

    # The effective date of change cannot be in the future
    if effective_date > datetime.utcnow():
        msg.append({'error': babel('Filing cannot have a future effective date.')})

    # The effective date cannot be a date prior to their Incorporation Date
    if effective_date < business.founding_date:
        msg.append({'error': babel('Filing cannot be before a businesses founding date.')})

    last_cod_filing = Filing.get_most_recent_legal_filing(business.id,
                                                          Filing.FILINGS['changeOfDirectors']['name'])
    if last_cod_filing:
        if effective_date < last_cod_filing.effective_date:
            msg.append({'error': babel("Filing's effective date cannot be before another Change of Director filing.")})

    return msg
