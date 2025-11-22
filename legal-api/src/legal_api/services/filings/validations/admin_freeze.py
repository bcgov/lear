# Copyright © 2022 Province of British Columbia
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
"""Validation for the Admin Freeze filing."""
from http import HTTPStatus
from typing import Optional

from flask_babel import _ as babel  # noqa: N813, I004, I001; importing camelcase '_' as a name

from legal_api.errors import Error
from legal_api.models import Business
from legal_api.services.utils import (
    get_bool,  # noqa: I003; needed as the linter gets confused from the babel override above.
)


def validate(business: Business, admin_freeze: dict) -> Optional[Error]:
    """Validate the Court Order filing."""
    if not business or not admin_freeze:
        return Error(HTTPStatus.BAD_REQUEST, [{"error": babel("A valid business and filing are required.")}])
    msg = []

    current_state = business.admin_freeze or False

    if current_state == get_bool(admin_freeze, "/filing/adminFreeze/freeze"):
        msg.append({"error": babel("Admin Freeze flag cannot be same as current state."),
                    "path": "/filing/adminFreeze/freeze"})

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)

    return None
