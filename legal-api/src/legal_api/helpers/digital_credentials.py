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
"""Helper functions for digital credentials."""

from legal_api.models.business import Business
from legal_api.models.dc_connection import DCConnection
from legal_api.models.dc_issued_credential import DCIssuedCredential
from legal_api.services import digital_credentials


def get_business_issued_credentials(identifier: str):
    business = Business.find_by_identifier(identifier)
    if not business:
        raise Exception(f'{identifier} not found.')

    connection = DCConnection.find_active_by(business_id=business.id)
    if not connection:
        raise Exception(f'{identifier} active connection not found.')

    issued_credentials = DCIssuedCredential.find_by(dc_connection_id=connection.id)
    if not issued_credentials:
        return []

    return issued_credentials


def revoke_issued_credential(issued_credential: DCIssuedCredential):
    connection = DCConnection.find_by_id(issued_credential.dc_connection_id)
    if (not connection or not connection.is_active):
        raise Exception('Active connection not found for credential.')

    revoked = digital_credentials.revoke_credential(issued_credential.co,
                                                    issued_credential.credential_revocation_id,
                                                    issued_credential.revocation_registry_id)
    if not revoked:
        raise Exception('Failed to revoke credential.')

    return revoked
