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
"""Perform various validations."""
from http import HTTPStatus

from flask_babel import _ as babel

from legal_api.errors import Error
from legal_api.models import Business
from legal_api.services import flags

document_rule_set = {
    "cstat": {
        "excluded_types": ["SP", "GP"],
        "status": Business.State.ACTIVE
    },
    "cogs": {
        "excluded_types": ["SP", "GP"],
        "goodStanding": True
    },
    "lseal": {
        # NB: will be available for all business types once the outputs have been updated for them
        "excluded_types": []
    }
}


def validate_document_request(document_type, business: Business):
    """Validate the business document request."""
    errors = []
    # basic checks
    enabled_filings = flags.value("enabled-business-summary-entities").split()
    if document_type == "summary" and business.legal_type not in enabled_filings:
        return Error(HTTPStatus.FORBIDDEN,
                     [{"error": babel(f"{business.legal_type} is not enabled business summary.")}])
    if document_rules := document_rule_set.get(document_type):
        excluded_legal_types = document_rules.get("excluded_types", None)
        if excluded_legal_types and business.legal_type in excluded_legal_types:
            errors.append({"error": babel("Specified document type is not valid for the entity.")})

        if (status := document_rules.get("status", None)) and business.state != status:
            errors.append({"error": babel("Specified document type is not valid for the current entity status.")})

        if document_rules.get("goodStanding", None) and not business.good_standing:
            errors.append({"error": babel("Specified document type is not valid for the current entity status.")})

    if errors:
        return Error(HTTPStatus.BAD_REQUEST, errors)
    return None
