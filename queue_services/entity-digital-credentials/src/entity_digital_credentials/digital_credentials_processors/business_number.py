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
"""Processing business number actions."""

from entity_queue_common.service_utils import logger
from legal_api.models import Business, DCDefinition, DCRevocationReason

from entity_digital_credentials.helpers import get_all_digital_credentials_for_business, replace_digital_credential


async def process(business: Business) -> None:
    """Process business number actions."""
    credentials = get_all_digital_credentials_for_business(business=business)

    if not (credentials and len(credentials)):
        logger.warning(
            'No issued credentials found for business: %s', business.identifier)
        return None

    for credential in credentials:
        replace_digital_credential(credential=credential,
                                   credential_type=DCDefinition.CredentialType.business.name,
                                   reason=DCRevocationReason.UPDATED_INFORMATION)
    return None
