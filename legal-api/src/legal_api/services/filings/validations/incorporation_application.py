# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Validation for the Incorporation filing."""
from flask_babel import _ as babel  # noqa: N813, I004, I001; importing camelcase '_' as a name
from http import HTTPStatus

from legal_api.errors import Error
from legal_api.models import Business  # noqa: F401 pylint: disable=unused-import


def validate(business, incorporation_json):
    """Validate the Change ofAddress filing."""
    if not business or not incorporation_json:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid business and filing are required.')}])
    msg = []
    # What are the rules for saving an incorporation
    temp_identifier = incorporation_json['filing']['incorporationApplication']['nameRequest']['nrNumber']

    if business.identifier != temp_identifier:
        msg.append({'error': babel('Business Identifier does not match the identifier in filing.')})

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None
