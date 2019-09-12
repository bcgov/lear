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
from typing import Dict

import pycountry
from flask_babel import _

from legal_api.errors import Error
from legal_api.models import Business

from ..utils import get_str


def validate(business: Business, cod: Dict) -> Error:
    """Validate the Change of Directors filing."""
    if not business or not cod:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': _('A valid business and filing are required.')}])
    msg = []

    directors = cod['filing']['changeOfDirectors']['directors']

    for idx, director in enumerate(directors):
        try:
            pycountry.countries.search_fuzzy(
                get_str(director, '/deliveryAddress/addressCountry')
            )[0].alpha_2
        except LookupError:
            msg.append({'error': _('Address Country must resolve to a valid ISO-2 country.'),
                        'path': f'/filing/changeOfDirectors/directors/{idx}/deliveryAddress/addressCountry'})

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None
