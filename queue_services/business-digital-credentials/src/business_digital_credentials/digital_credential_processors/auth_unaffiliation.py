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
"""
Processing auth affiliation actions.

Used in the event that a user is unaffiliated from a business where they have a DBC:

- Business Unaffiliated
- Team Member Removed

Note: The credential is not replaced, it is simply revoked.
"""
from flask import current_app

from business_model.models import Business, DCRevocationReason, User

from .helpers import (
    get_all_digital_credentials_for_business,
    revoke_digital_credential,
)


def process(idp_userid: str, unaffiliated_identifiers: list) -> None:
    """Process auth actions."""
    current_app.logger.debug(
        f"Process auth unaffiliation for user: {idp_userid} from identifiers: {unaffiliated_identifiers}"
    )

    # Look up the user by idp_userid using existing helper method
    userobj = {"idp_userid": idp_userid}
    user = User.find_by_jwt_token(userobj)

    if not user:
        current_app.logger.warning(f"User not found for {idp_userid}.")
        return

    # For each unaffiliated identifier, find any digital credentials for that business and revoke them
    for identifier in unaffiliated_identifiers:
        current_app.logger.debug(
            f"Processing unaffiliation for business identifier: {identifier} for user: {user.id}."
        )
        business = Business.find_by_identifier(identifier)
        if not business:
            # No business found, skip
            continue

        credentials = get_all_digital_credentials_for_business(business)
        if not credentials:
            # No issued credentials found for this business
            continue

        # Revoke any credentials that belong to this user
        for credential in credentials:
            try:
                if credential.connection.business_user.user.id == user.id:
                    # Revoke the credential
                    current_app.logger.info(
                        f"Revoking credential {credential.id} for unaffiliated user {credential.connection.business_user.user.id}."
                    )
                    revoke_digital_credential(
                        credential=credential,
                        reason=DCRevocationReason.AUTH_UNAFFILIATED,
                    )
            except Exception as err:
                current_app.logger.error(
                    f"Error processing credential {credential.id}: {err}", exc_info=True
                )
                continue

    return None
