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

from entity_queue_common.service_utils import logger
from legal_api.models import Business, DCRevocationReason

from entity_digital_credentials.helpers import get_issued_digital_credentials, revoke_issued_digital_credential


async def process(business: Business) -> None:
    """Process admin actions."""
    issued_credentials = get_issued_digital_credentials(business=business)

    if not (issued_credentials and len(issued_credentials)):
        logger.warning(
            'No issued credentials found for business: %s', business.identifier)
        return None

    for issued_credential in issued_credentials:
        revoke_issued_digital_credential(business=business,
                                         issued_credential=issued_credential,
                                         reason=DCRevocationReason.ADMINISTRATIVE_REVOCATION)
    return None
