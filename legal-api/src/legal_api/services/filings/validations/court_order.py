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
"""Validation for the Court Order filing."""
from http import HTTPStatus

from flask_babel import _ as babel

from business_model.models import Business
from legal_api.errors import Error
from legal_api.services.authz import MIGRATED_COURT_ORDER_FEATURE, is_new_feature_enabled
from legal_api.services.filings.validations.common_validations import validate_court_order


def validate(business: Business, court_order: dict) -> Error | None:
    """Validate the Court Order filing."""
    if not business or not court_order:
        return Error(HTTPStatus.BAD_REQUEST, [{"error": babel("A valid business and filing are required.")}])

    # the migrated court order page requires details and a document, the legacy page details or a document
    is_migrated = is_new_feature_enabled(MIGRATED_COURT_ORDER_FEATURE)
    msg = validate_court_order(
        "/filing/courtOrder",
        court_order["filing"]["courtOrder"],
        is_file_or_details_required=not is_migrated,
        is_file_and_details_required=is_migrated
    )

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None
