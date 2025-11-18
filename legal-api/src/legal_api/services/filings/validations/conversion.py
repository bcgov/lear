# Copyright © 2022 Province of British Columbia
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
"""Validation for the Conversion filing."""

from http import HTTPStatus  # pylint: disable=wrong-import-order
from typing import Dict, Optional

from flask_babel import _ as babel  # noqa: N813, I004, I001, I003

from legal_api.errors import Error
from legal_api.models import Business
from legal_api.services.filings.validations.common_validations import (
    validate_name_request,
    validate_offices_addresses,
    validate_parties_addresses,
)
from legal_api.services.filings.validations.registration import validate_offices, validate_party
from legal_api.services.utils import get_str


def validate(business: Business, filing: Dict) -> Optional[Error]:
    """Validate the Conversion filing."""
    filing_type = "conversion"
    if not filing:
        return Error(HTTPStatus.BAD_REQUEST, [{"error": babel("A valid filing is required.")}])

    legal_type_path = "/filing/business/legalType"
    legal_type = get_str(filing, legal_type_path)
    if legal_type in [Business.LegalTypes.SOLE_PROP.value, Business.LegalTypes.PARTNERSHIP.value]:
        msg = []
        if filing.get("filing", {}).get("conversion", {}).get("nameRequest", None):
            msg.extend(validate_name_request(filing, legal_type, filing_type))
        msg.extend(validate_party(filing, legal_type, filing_type))
        msg.extend(validate_parties_addresses(filing, filing_type))
        msg.extend(validate_offices(filing, filing_type))
        msg.extend(validate_offices_addresses(filing, filing_type))

        if msg:
            return Error(HTTPStatus.BAD_REQUEST, msg)
    return None
