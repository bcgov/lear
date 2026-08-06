# Copyright © 2023 Province of British Columbia
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
"""Validation for the Continuation Out filing."""
from http import HTTPStatus
from typing import Final

from flask_babel import _ as babel

from business_common.utils.legislation_datetime import LegislationDatetime
from business_model.models import Business
from legal_api.errors import Error
from legal_api.services import flags
from legal_api.services.filings.validations.common_validations import (
    validate_court_order,
    validate_foreign_jurisdiction,
)
from legal_api.services.utils import get_date


def validate(business: Business, filing: dict) -> Error | None:
    """Validate the Continuation Out filing."""
    if not business or not filing:
        return Error(HTTPStatus.BAD_REQUEST, [{"error": babel("A valid business and filing are required.")}])

    enabled_filings = flags.value("supported-continuation-out-entities").split()
    if business.legal_type not in enabled_filings:
        return Error(HTTPStatus.FORBIDDEN,
                     [{"error": babel(f"{business.legal_type} does not support continuation out filing.")}])

    msg = []
    filing_type = "continuationOut"


    if err := validate_continuation_out_date(filing, filing_type):
        msg.extend(err)

    if err := validate_foreign_jurisdiction(filing["filing"][filing_type]["foreignJurisdiction"],
                                            f"/filing/{filing_type}/foreignJurisdiction"):
        msg.extend(err)

    if court_order := filing.get("filing", {}).get(filing_type, {}).get("courtOrder", None):
        court_order_path: Final = f"/filing/{filing_type}/courtOrder"
        err = validate_court_order(court_order_path, court_order)
        if err:
            msg.extend(err)

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def validate_continuation_out_date(filing: dict, filing_type: str) -> list:
    """Validate continuation out date."""
    msg = []
    continuation_out_date_path = f"/filing/{filing_type}/continuationOutDate"
    continuation_out_date = get_date(filing, continuation_out_date_path)

    now = LegislationDatetime.now().date()
    if continuation_out_date > now:
        msg.append({"error": "Continuation out date must be today or past.",
                    "path": continuation_out_date_path})

    return msg
