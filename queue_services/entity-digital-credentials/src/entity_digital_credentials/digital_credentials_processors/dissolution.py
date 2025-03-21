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
"""Processing dissolution actions."""

from entity_queue_common.service_utils import logger
from legal_api.models import Business, DCDefinition, DCRevocationReason

from entity_digital_credentials.helpers import (
    get_all_digital_credentials_for_business,
    replace_digital_credential,
    revoke_digital_credential,
)


async def process(business: Business, filing_sub_type: str) -> None:
    """Process dissolution actions."""
    credentials = get_all_digital_credentials_for_business(business=business)

    if not (credentials and len(credentials)):
        logger.warning(
            'No issued credentials found for business: %s', business.identifier)
        return None

    if filing_sub_type == 'voluntary':  # pylint: disable=no-else-return
        reason = DCRevocationReason.VOLUNTARY_DISSOLUTION
        credential_type = DCDefinition.CredentialType.business.name
        for credential in credentials:
            replace_digital_credential(
                credential=credential, credential_type=credential_type, reason=reason)
        return None
    elif filing_sub_type == 'administrative':
        reason = DCRevocationReason.ADMINISTRATIVE_DISSOLUTION
        for credential in credentials:
            revoke_digital_credential(credential=credential, reason=reason)
        return None
    else:
        raise Exception('Invalid filing sub type.')  # pylint: disable=broad-exception-raised
