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

from flask_babel import _ as babel  # noqa: N813, I004, I001; importing camelcase '_' as a name
# noqa: I003
from legal_api.errors import Error
from legal_api.models import Business
from legal_api.services import flags
from legal_api.services.utils import get_int
from legal_api.utils.legislation_datetime import LegislationDatetime
# noqa: I003


def validate(business: Business, filing: Dict) -> Optional[Error]:
    """Validate the Agm Location Change filing."""
    if not business or not filing:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid business and filing are required.')}])

    if flags.is_on('supported-agm-location-change-entities'):
        enabled_filings = flags.value('supported-agm-location-change-entities').split()
        if business.legal_type not in enabled_filings:
            return Error(HTTPStatus.BAD_REQUEST,
                         [{'error': babel(f'{business.legal_type} does not support agm location change filing.')}])

    msg = []

    agm_year_path: Final = '/filing/agmLocationChange/year'
    year = get_int(filing, agm_year_path)
    if year:
        expected_min = LegislationDatetime.now().year - 2
        expected_max = LegislationDatetime.now().year + 1
        if expected_min > year or year > expected_max:
            msg.append({'error': 'AGM year must be between -2 or +1 year from current year.', 'path': agm_year_path})
    else:
        msg.append({'error': 'Invalid AGM year.', 'path': agm_year_path})

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)

    return None
