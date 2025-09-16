# Copyright © 2025 Province of British Columbia
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
"""Processing restoration actions."""

from flask import current_app
from enum import Enum

from business_model.models import Business

from .helpers import (
    get_all_digital_credentials_for_business,
    revoke_digital_credential,
)

class DCRevocationReason(Enum):
    """Digital Credential Revocation Reasons."""

    ADMINISTRATIVE_REVOCATION = 'Your credential was revoked.'
    UPDATED_INFORMATION = 'You were offered a new credential with updated information ' \
        'and that revoked all previous copies.'
    VOLUNTARY_DISSOLUTION = 'You chose to dissolve your business. ' \
        'A new credential was offered that reflects the new company status and that revoked all previous copies.'
    ADMINISTRATIVE_DISSOLUTION = 'Your business was dissolved by the Registrar.'
    PUT_BACK_ON = 'Your business was put back on the Registry. '
    RESTORATION = 'Your business was restored to the Registry. '
    SELF_REISSUANCE = 'You chose to issue yourself a new credential and that revoked all previous copies.'
    SELF_REVOCATION = 'You chose to revoke your own credential.'


def process(business: Business) -> None:
    """Process restoration actions."""
    current_app.logger.debug(f"Process restoration on actions for: {business.identifier}")
    credentials = get_all_digital_credentials_for_business(business=business)

    if not (credentials and len(credentials)):
        current_app.logger.warning(
            f"No issued credentials found for business: {business.identifier}"
        )
        return None

    for credential in credentials:
        revoke_digital_credential(
            credential=credential, reason=DCRevocationReason.RESTORATION
        )
    return None
