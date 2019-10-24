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
"""Validation for the Voluntary Dissolution filing."""
from http import HTTPStatus
from typing import Dict

from flask_babel import _

from legal_api.errors import Error
from legal_api.models import Business

from ..utils import get_bool, get_date


def validate(business: Business, con: Dict) -> Error:
    """Validate the Voluntary dissolution filing."""
    if not business or not con:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': _('A valid business and filing are required.')}])
    msg = []

    dissolution_date_path = '/filing/voluntaryDissolution/dissolutionDate'
    dissolution_date = get_date(con, dissolution_date_path)
    if not dissolution_date:
        msg.append({'error': _('Dissolution date must be provided.'),
                    'path': dissolution_date_path})

    has_liabilities_path = '/filing/voluntaryDissolution/hasLiabilities'
    has_liabilities = get_bool(con, has_liabilities_path)
    if has_liabilities is None:
        msg.append({'error': _('Liabilities flag must be provided.'),
                    'path': has_liabilities_path})
    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None
