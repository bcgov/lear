# Copyright © 2024 Province of British Columbia
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
"""Validation for the Put Back Off filing."""
from http import HTTPStatus
from typing import Dict, Final, Optional

from flask_babel import _ as babel  # noqa: N813, I004, I001; importing camelcase '_' as a name

from legal_api.errors import Error
from legal_api.models import Business
from legal_api.services.filings.validations.common_validations import validate_court_order
from legal_api.services.utils import get_str  # noqa: I003; needed as the linter gets confused from the babel override.


def validate(business: Business, put_back_off: Dict) -> Optional[Error]:
    """Validate the Court Order filing."""
    if not business or not put_back_off:
        return Error(HTTPStatus.BAD_REQUEST, [{"error": babel("A valid business and filing are required.")}])
    msg = []

    if not get_str(put_back_off, "/filing/putBackOff/details"):
        msg.append({"error": babel("Put Back Off details are required."), "path": "/filing/putBackOff/details"})

    msg.extend(_validate_court_order(put_back_off))

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def _validate_court_order(filing):
    """Validate court order."""
    if court_order := filing.get("filing", {}).get("putBackOff", {}).get("courtOrder", None):
        court_order_path: Final = "/filing/putBackOff/courtOrder"
        err = validate_court_order(court_order_path, court_order)
        if err:
            return err
    return []
