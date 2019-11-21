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
"""Validation for the Special Resolution filing."""
from http import HTTPStatus
from typing import Dict

from flask_babel import _

from legal_api.errors import Error
from legal_api.models import Business

from ..utils import get_str


def validate(business: Business, con: Dict) -> Error:
    """Validate the Special Resolution filing."""
    if not business or not con:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': _('A valid business and filing are required.')}])
    msg = []

    resolution_path = '/filing/specialResolution/resolution'
    resolution_name = get_str(con, resolution_path)
    if not resolution_name:
        msg.append({'error': _('Resolution must be provided.'),
                    'path': resolution_path})

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None
