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
Processing admin revocation actions.

Used in the event that a DBC is administratively revoked for any particular reason but may include:

- Identifier changed/incorrect
- Business Type changed/incorrect
- Registered On changed/incorrect

Note: The credential is not replaced, it is simply revoked.
"""
from flask import current_app

from business_model.models import Business, DCRevocationReason

from .helpers import get_all_digital_credentials_for_business, revoke_digital_credential


def process(business: Business) -> None:
    """Process admin actions."""
    current_app.logger.debug(f"Process Admin Revoke for: {business.identifier}")
    credentials = get_all_digital_credentials_for_business(business=business)

    if not (credentials and len(credentials)):
        current_app.logger.warning(
            f"No issued credentials found for business: {business.identifier}"
        )
        return None

    for credential in credentials:
        revoke_digital_credential(
            credential=credential, reason=DCRevocationReason.ADMINISTRATIVE_REVOCATION
        )
    return None
