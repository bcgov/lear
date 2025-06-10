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
from datetime import datetime
from http import HTTPStatus
from typing import Dict, Optional

import pycountry
from flask_babel import _ as babel  # noqa: N813, I004, I001, I003

from legal_api.errors import Error
from legal_api.models import Business
from legal_api.services.utils import get_date

from .common_validations import validate_court_order


def validate(business: Business, filing_json: Dict) -> Optional[Error]:
    """Validate the Intent to Liquidate filing."""
    if not business or not filing_json:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid business and filing are required.')}])

    if business.state != Business.State.ACTIVE or not business.good_standing:
        return Error(HTTPStatus.BAD_REQUEST, [{
            'error': babel('Business should be Active and in Good Standing to file Intent to Liquidate.')
        }])

    if business.in_liquidation:
        return Error(HTTPStatus.BAD_REQUEST, [{
            'error': babel('Business already in liquidation.')
        }])

    if business.in_dissolution:
        return Error(HTTPStatus.BAD_REQUEST, [{
            'error': babel('Business already in dissolution.')
        }])

    msg = []

    err = validate_liquidation_date(filing_json)
    if err:
        msg.extend(err)

    err = validate_parties(filing_json)
    if err:
        msg.extend(err)

    err = validate_offices(filing_json)
    if err:
        msg.extend(err)

    err = validate_intent_court_order(filing_json)
    if err:
        msg.extend(err)

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def validate_liquidation_date(filing_json: Dict) -> Optional[list]:
    """Validate the date of commencement of liquidation."""
    msg = []
    liquidation_date_path = '/filing/intentToLiquidate/dateOfCommencementOfLiquidation'

    liquidation_date = get_date(filing_json, liquidation_date_path)
    if not liquidation_date:
        msg.append({'error': babel('Date of commencement of liquidation must be a valid date.'),
                    'path': liquidation_date_path})

    return msg if msg else None


def validate_parties(filing_json: Dict) -> Optional[list]:
    """Validate the parties in the intent to liquidate filing."""
    msg = []
    parties_path = '/filing/intentToLiquidate/parties'

    parties = filing_json.get('filing', {}).get('intentToLiquidate', {}).get('parties', [])

    if not parties:
        msg.append({'error': babel('At least one party is required.'), 'path': parties_path})
        return msg

    liquidator_count = 0
    for party in parties:
        roles = party.get('roles', [])

        # Check for liquidator role
        has_liquidator_role = any(role.get('roleType') == 'Liquidator' for role in roles)
        if has_liquidator_role:
            liquidator_count += 1

    if liquidator_count == 0:
        msg.append({'error': babel('At least one liquidator is required.'), 'path': parties_path})

    return msg if msg else None


def validate_offices(filing_json: Dict) -> Optional[list]:
    """Validate the liquidation office."""
    msg = []
    offices_path = '/filing/intentToLiquidate/offices'

    offices = filing_json.get('filing', {}).get('intentToLiquidate', {}).get('offices', {})
    liquidation_office = offices.get('liquidationOffice')

    if not liquidation_office:
        msg.append({'error': babel('Liquidation office is required.'), 'path': f'{offices_path}/liquidationOffice'})
        return msg

    # Validate liquidation office addresses
    for address_type in ['mailingAddress', 'deliveryAddress']:
        address = liquidation_office.get(address_type)
        if address:
            address_path = f'{offices_path}/liquidationOffice/{address_type}'

            region = address.get('addressRegion')
            if region != 'BC':
                msg.append({'error': babel("Address Region must be 'BC'."),
                            'path': f'{address_path}/addressRegion'})

            country = address.get('addressCountry')
            if country:
                try:
                    country_code = pycountry.countries.search_fuzzy(country)[0].alpha_2
                    if country_code != 'CA':
                        raise LookupError
                except LookupError:
                    msg.append({'error': babel("Address Country must be 'CA'."),
                                'path': f'{address_path}/addressCountry'})

    return msg if msg else None


def validate_intent_court_order(filing_json: Dict) -> Optional[list]:
    """Validate the court order if present."""
    msg = []
    court_order = filing_json.get('filing', {}).get('intentToLiquidate', {}).get('courtOrder')

    if court_order:
        court_order_path = '/filing/intentToLiquidate/courtOrder'
        err = validate_court_order(court_order_path, court_order)
        if err:
            msg.extend(err)

    return msg if msg else None
