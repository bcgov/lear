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

from business_model.models import Business, DCDefinition, DCRevocationReason, Filing, PartyRole

from .helpers import (
    get_all_digital_credentials_for_business,
    is_user_in_officers,
    replace_digital_credential,
    revoke_digital_credential,
)


def process(business: Business, filing: Filing) -> None:
    """Process change of registration actions."""
    current_app.logger.debug(f"Process change of reg for: {business.identifier}")

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
            # no longer exists in the filing parties for Partner role. Revoke if so.
            if (conn := credential.connection) and (biz := conn.business_user):
                user = biz.user
            else:
                current_app.logger.warning(f"Credential {credential.id} has no associated user, skipping.")
                continue

            if is_user_in_officers(user, filing_data, PartyRole.RoleTypes.PARTNER.value):
                # If the name has changed, replace the credential (unless the partner was also removed)
                if filing_data.get("nameRequest") is not None:
                    current_app.logger.debug("Firm name changed, replacing cred")
                    replace_digital_credential(
                        credential=credential,
                        credential_type=DCDefinition.CredentialType.business.name,
                        reason=DCRevocationReason.UPDATED_INFORMATION,
                    )
            else:
                current_app.logger.info(f"User {user.id} not in filing parties, revoking.")
                revoke_digital_credential(
                    credential=credential, reason=DCRevocationReason.CHANGE_OF_DIRECTORS
                )
        except Exception as err:
            current_app.logger.error(f"Error processing credential {credential.id}: {err}", exc_info=True)
            continue

    return None
