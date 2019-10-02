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
"""Validation for the Change of Address filing."""
from http import HTTPStatus
from typing import Dict

import pycountry
from flask_babel import _

from legal_api.errors import Error
from legal_api.models import Business

from ..utils import get_str


def validate(business: Business, cod: Dict) -> Error:
    """Validate the Change ofAddress filing."""
    if not business or not cod:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': _('A valid business and filing are required.')}])
    msg = []

    # Check Delivery Address
    da_region_path = '/filing/changeOfAddress/deliveryAddress/addressRegion'
    if get_str(cod, da_region_path) != 'BC':
        msg.append({'error': _("Address Region must be 'BC'."),
                    'path': da_region_path})

    da_country_path = '/filing/changeOfAddress/deliveryAddress/addressCountry'
    raw_da_country = get_str(cod, da_country_path)
    try:
        da_country = pycountry.countries.search_fuzzy(raw_da_country)[0].alpha_2
        if da_country != 'CA':
            raise LookupError
    except LookupError:
        msg.append({'error': _("Address Country must be 'CA'."),
                    'path': da_country_path})

    ma_region_path = '/filing/changeOfAddress/mailingAddress/addressRegion'
    if get_str(cod, ma_region_path) != 'BC':
        msg.append({'error': _("Address Region must be 'BC'."),
                    'path': ma_region_path})

    ma_country_path = '/filing/changeOfAddress/mailingAddress/addressCountry'
    raw_ma_country = get_str(cod, ma_country_path)
    try:
        ma_country = pycountry.countries.search_fuzzy(raw_ma_country)[0].alpha_2
        if ma_country != 'CA':
            raise LookupError
    except LookupError:
        msg.append({'error': _("Address Country must be 'CA'."),
                    'path': ma_country_path})
    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None
