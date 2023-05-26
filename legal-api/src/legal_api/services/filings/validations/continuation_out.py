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
"""Validation for the Continuation Out filing."""
from http import HTTPStatus
from typing import Dict, Final, Optional

import pycountry
from flask_babel import _ as babel  # noqa: N813, I004, I001; importing camelcase '_' as a name
# noqa: I003
from legal_api.errors import Error
from legal_api.models import Business
from legal_api.services.filings.validations.common_validations import validate_court_order
from legal_api.services.utils import get_date
from legal_api.utils.legislation_datetime import LegislationDatetime
# noqa: I003;


def validate(business: Business, filing: Dict) -> Optional[Error]:
    """Validate the Continuation Out filing."""
    if not business or not filing:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid business and filing are required.')}])

    msg = []
    filing_type = 'continuationOut'

    msg.extend(validate_continuation_out_date(business, filing, filing_type))
    msg.extend(validate_foreign_jurisdiction(filing, filing_type))

    if court_order := filing.get('filing', {}).get(filing_type, {}).get('courtOrder', None):
        court_order_path: Final = f'/filing/{filing_type}/courtOrder'
        err = validate_court_order(court_order_path, court_order)
        if err:
            msg.extend(err)

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def validate_continuation_out_date(business: Business, filing: Dict, filing_type: str) -> list:
    """Validate continuation out date."""
    msg = []
    continuation_out_date_path = f'/filing/{filing_type}/continuationOutDate'
    continuation_out_date = get_date(filing, continuation_out_date_path)

    now = LegislationDatetime.now().date()
    if continuation_out_date > now:
        msg.append({'error': 'Continuation out date must be today or past.',
                    'path': continuation_out_date_path})

    if business.cco_expiry_date:
        cco_expiry_date = LegislationDatetime.as_legislation_timezone(business.cco_expiry_date).date()
        if continuation_out_date > cco_expiry_date:
            msg.append({'error': 'Consent continuation of interest has expired.',
                        'path': continuation_out_date_path})
    else:
        msg.append({'error': 'Did not find an active Consent continuation out for this business.',
                    'path': continuation_out_date_path})

    return msg


def validate_foreign_jurisdiction(filing: Dict, filing_type: str) -> list:
    """Validate foreign jurisdiction."""
    msg = []
    foreign_jurisdiction_path = f'/filing/{filing_type}/foreignJurisdiction'

    foreign_jurisdiction = filing['filing'][filing_type]['foreignJurisdiction']
    country_code = foreign_jurisdiction.get('country').upper() # country is a required field in schema
    region = foreign_jurisdiction.get('region', '').upper()
    
    country = pycountry.countries.get(alpha_2=country_code)
    if not country:
            msg.append({'error': 'Invalid country.', 'path': f'{foreign_jurisdiction_path}/country'})
    elif country_code == 'CA':
        if region == 'BC':
            msg.append({'error': 'Region should not be BC.', 'path': f'{foreign_jurisdiction_path}/region'})
        elif not (region == 'FEDERAL' or pycountry.subdivisions.get(code=f'{country_code}-{region}')):
            msg.append({'error': 'Invalid region.', 'path': f'{foreign_jurisdiction_path}/region'})
    elif country_code == 'US' and not pycountry.subdivisions.get(code=f'{country_code}-{region}'):
        msg.append({'error': 'Invalid region.', 'path': f'{foreign_jurisdiction_path}/region'})

    return msg
