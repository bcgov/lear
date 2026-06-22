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
"""Validation for the Agm Location Change filing."""
from http import HTTPStatus
from typing import Final

from flask_babel import _ as babel

from business_common.utils.legislation_datetime import LegislationDatetime
from business_model.models import Business
from legal_api.errors import Error
from legal_api.services import flags
from legal_api.services.utils import get_int


def validate(business: Business, filing: dict) -> Error | None:
    """Validate the Agm Location Change filing."""
    if not business or not filing:
        return Error(HTTPStatus.BAD_REQUEST, [{"error": babel("A valid business and filing are required.")}])

    enabled_filings = flags.value("supported-agm-location-change-entities").split()
    if business.legal_type not in enabled_filings:
        return Error(HTTPStatus.FORBIDDEN,
                     [{"error": babel(f"{business.legal_type} does not support agm location change filing.")}])

    msg = []

    # A four-digit year is enforced by the schema (agm_location_change year pattern ^\d{4}$);
    # only the business-rule year range is checked here.
    agm_year_path: Final = "/filing/agmLocationChange/year"
    year = get_int(filing, agm_year_path)
    if year:
        expected_min = LegislationDatetime.now().year - 2
        expected_max = LegislationDatetime.now().year + 1
        if expected_min > year or year > expected_max:
            msg.append({"error": "AGM year must be between -2 or +1 year from current year.", "path": agm_year_path})

    # A non-empty reason (at least one non-whitespace character) is enforced by the schema
    # (business-schemas agm_location_change reason pattern).

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)

    return None
