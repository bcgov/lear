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
"""Validation for alteration filing."""
from http import HTTPStatus  # pylint: disable=wrong-import-order
from typing import Dict
from flask_babel import _ as babel  # noqa: N813, I004, I001, I003

from legal_api.errors import Error
from legal_api.core.filing import Filing  # noqa: I001

from .common_validations import validate_share_structure


def validate(alteration_json: Dict):
    """Validate the alteration filing."""
    if not alteration_json:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid alteration is required.')}])
    msg = []

    err = validate_share_structure(alteration_json, Filing.FilingTypes.ALTERATION.value)
    if err:
        msg.extend(err)

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None
