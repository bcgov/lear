# Copyright © 2023 Province of British Columbia
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
    get_issued_digital_credentials,
    replace_issued_digital_credential,
    revoke_issued_digital_credential,
)


async def process(business: Business, filing_sub_type: str):
    """Process dissolution actions."""
    issued_credentials = get_issued_digital_credentials(business=business)

    if not (issued_credentials and len(issued_credentials)):
        logger.warning('No issued credentials found for business: %s', business.identifier)
        return None

    if filing_sub_type == 'voluntary':  # pylint: disable=no-else-return
        reason = DCRevocationReason.VOLUNTARY_DISSOLUTION
        return replace_issued_digital_credential(business=business,
                                                 issued_credential=issued_credentials[0],
                                                 credential_type=DCDefinition.CredentialType.business.name,
                                                 reason=reason)
    elif filing_sub_type == 'administrative':
        reason = DCRevocationReason.ADMINISTRATIVE_DISSOLUTION
        return revoke_issued_digital_credential(business=business,
                                                issued_credential=issued_credentials[0],
                                                reason=reason)
    else:
        raise Exception('Invalid filing sub type.')  # pylint: disable=broad-exception-raised
