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
"""Processing change of registration actions."""

from entity_queue_common.service_utils import logger
from legal_api.models import Business, DCDefinition, DCRevocationReason, Filing

from entity_digital_credentials.helpers import get_issued_digital_credentials, replace_issued_digital_credential


async def process(business: Business, filing: Filing):
    """Process change of registration actions."""
    if filing.filing_json.get('filing').get(filing.filing_type).get('nameRequest') is not None:

        issued_credentials = get_issued_digital_credentials(business=business)
        if not (issued_credentials and len(issued_credentials)):
            logger.warning('No issued credentials found for business: %s', business.identifier)
            return None

        return replace_issued_digital_credential(business=business,
                                                 issued_credential=issued_credentials[0],
                                                 credential_type=DCDefinition.CredentialType.business.name,
                                                 reason=DCRevocationReason.UPDATED_INFORMATION)
