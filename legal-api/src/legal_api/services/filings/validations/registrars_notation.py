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
"""Validation for the Registrars Notation filing."""
from http import HTTPStatus
from typing import Dict, Optional

from flask_babel import _ as babel  # noqa: N813, I004, I001; importing camelcase '_' as a name
# noqa: I004
from legal_api.errors import Error
from legal_api.models import Business
from legal_api.services.utils import get_str
# noqa: I003; needed as the linter gets confused from the babel override above.


def validate(business: Business, registrars_notation: Dict) -> Optional[Error]:
    """Validate the Registrars Notation filing."""
    if not business or not registrars_notation:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid business and filing are required.')}])
    msg = []

    effect_of_order = get_str(registrars_notation, '/filing/registrarsNotation/effectOfOrder')
    if effect_of_order:
        if effect_of_order == 'planOfArrangement':
            file_number = get_str(registrars_notation, '/filing/registrarsNotation/fileNumber')
            if not file_number:
                msg.append({'error': babel(
                    'Court Order Number is required when this filing is pursuant to a Plan of Arrangement.'),
                    'path': '/filing/registrarsNotation/fileNumber'})
        else:
            msg.append({'error': babel('Invalid effectOfOrder.'), 'path': '/filing/registrarsNotation/effectOfOrder'})

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None
