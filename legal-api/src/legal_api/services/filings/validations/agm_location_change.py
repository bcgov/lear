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
"""Validation for the Agm Location Change filing."""
from http import HTTPStatus
from typing import Dict, Final, Optional

import pycountry
from flask_babel import _ as babel  # noqa: N813, I004, I001; importing camelcase '_' as a name
# noqa: I003
from legal_api.errors import Error
from legal_api.models import Business
from legal_api.services.utils import get_int
from legal_api.utils.legislation_datetime import LegislationDatetime


def validate(business: Business, filing: Dict) -> Optional[Error]:
    """Validate the Agm Location Change filing."""
    if not business or not filing:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid business and filing are required.')}])

    msg = []

    agm_year_path: Final = '/filing/agmLocationChange/year'
    year = get_int(filing, agm_year_path)
    if year:
        expected_min = LegislationDatetime.now().year - 1
        expected_max = LegislationDatetime.now().year + 1
        if not (expected_min <= year and year <= expected_max):
            msg.append({'error': 'AGM year must be between -1 or +1 year from current year.', 'path': agm_year_path})
    else:
        msg.append({'error': 'Invalid AGM year.', 'path': agm_year_path})

    address = filing['filing']['agmLocationChange']['newAgmLocation']
    country_code = address.get('addressCountry').upper()  # country is a required field in schema
    region = (address.get('addressRegion') or '').upper()

    agm_location_path: Final = '/filing/agmLocationChange/newAgmLocation'
    country = pycountry.countries.get(alpha_2=country_code)
    if not country:
        msg.append({'error': 'Invalid country.', 'path': f'{agm_location_path}/addressCountry'})
    elif country_code == 'CA':
        if region == 'BC':
            msg.append({'error': 'Region should not be BC.', 'path': f'{agm_location_path}/addressRegion'})
        elif not (pycountry.subdivisions.get(code=f'{country_code}-{region}')):
            msg.append({'error': 'Invalid region.', 'path': f'{agm_location_path}/addressRegion'})
    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)

    return None
