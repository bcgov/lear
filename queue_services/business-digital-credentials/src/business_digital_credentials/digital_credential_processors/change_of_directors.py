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
"""Processing change of director filing actions."""

from flask import current_app

from business_model.models import Business, DCRevocationReason, Filing

from .helpers import (
    does_officer_have_action,
    get_all_digital_credentials_for_business,
    revoke_digital_credential,
)


def process(business: Business, filing: Filing) -> None:
    """Process change of director actions."""
    current_app.logger.debug(f"Process change of directors for: {business.identifier}")

    # Only BEN supported for DBC at this time (CoD can happen for others so bail if not)
    if business.legal_type not in {Business.LegalTypes.BCOMP.value, Business.LegalTypes.BCOMP_CONTINUE_IN.value}:
        current_app.logger.debug(f"Business {business.identifier} is not a BEN, skipping DBC handling.")
        return None

    filing_data = filing.filing_json.get("filing", {}).get(filing.filing_type, {})

    credentials = get_all_digital_credentials_for_business(business=business)
    if not (credentials and len(credentials)):
        current_app.logger.debug(
            f"No issued credentials found for business: {business.identifier}"
        )
        return None

    for credential in credentials:
        try:
            # Go through each credential and see if the user for that credential
            # was ceased as a director. Revoke if so.
            if (conn := credential.connection) and (biz := conn.business_user):
                user = biz.user
            else:
                current_app.logger.warning(f"Credential {credential.id} has no associated user, skipping.")
                continue

            # Check if this user's credential should be revoked due to director cessation
            if does_officer_have_action(user, filing_data, "directors", "ceased"):
                revoke_digital_credential(
                    credential=credential, reason=DCRevocationReason.CHANGE_OF_DIRECTORS
                )

        except Exception as err:
            current_app.logger.error(f"Error processing credential {credential.id}: {err}", exc_info=True)
            continue

    return None
