# Copyright © 2025 Province of British Columbia
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
"""Processing change of registration actions."""

from flask import current_app

from business_model.models import Business, DCDefinition, DCRevocationReason, Filing

from .helpers import (
    get_all_digital_credentials_for_business,
    replace_digital_credential,
)


def process(business: Business, filing: Filing) -> None:
    """Process change of registration actions."""
    current_app.logger.debug(f"Process change of reg for: {business.identifier}")

    filing_data = filing.filing_json.get("filing", {}).get(filing.filing_type, {})
    if filing_data.get("nameRequest") is not None:

        credentials = get_all_digital_credentials_for_business(business=business)
        if not (credentials and len(credentials)):
            current_app.logger.debug(
                f"No issued credentials found for business: {business.identifier}"
            )
            return None

        for credential in credentials:
            replace_digital_credential(
                credential=credential,
                credential_type=DCDefinition.CredentialType.business.name,
                reason=DCRevocationReason.UPDATED_INFORMATION,
            )
    return None
