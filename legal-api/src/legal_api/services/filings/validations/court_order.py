# Copyright © 2021 Province of British Columbia
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
"""Validation for the Court Order filing."""
from http import HTTPStatus
from typing import Dict, Optional

from flask_babel import _ as babel  # noqa: N813, I004, I001; importing camelcase '_' as a name
# noqa: I004
from legal_api.errors import Error
from legal_api.models import Business

from ...utils import get_str
# noqa: I003; needed as the linter gets confused from the babel override above.


def validate(business: Business, court_order: Dict) -> Optional[Error]:
    """Validate the Court Order filing."""
    if not business or not court_order:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid business and filing are required.')}])
    msg = []

    if not get_str(court_order, '/filing/courtOrder/orderDetails'):
        msg.append({'error': babel('Court Order is required.'), 'path': '/filing/courtOrder/orderDetails'})

    effect_of_order = get_str(court_order, '/filing/courtOrder/effectOfOrder')
    if effect_of_order and effect_of_order != 'planOfArrangement':
        msg.append({'error': babel('Invalid effectOfOrder.'), 'path': '/filing/courtOrder/effectOfOrder'})

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None
