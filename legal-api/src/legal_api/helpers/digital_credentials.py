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

from enum import Enum

from legal_api.models.business import Business
from legal_api.models.dc_connection import DCConnection
from legal_api.models.dc_definition import DCDefinition
from legal_api.models.dc_issued_credential import DCIssuedCredential
from legal_api.services import digital_credentials


class DCRevocationReason(Enum):
    UPDATED_INFORMATION = 'You were offered a new credential with updated information and that revoked all previous copies.'
    VOLUNTARY_DISSOLUTION = 'You chose to dissolve your business. A new credential was offered that reflects the new company status and that revoked all previous copies.'
    ADMINISTRATIVE_DISSOLUTION = 'Your business was dissolved by the Registrar.'
    PUT_BACK_ON = 'Your business was put back on the Registry.'
    RESTORATION = 'Your business was put back on the Registry. A new credential was offered that reflects the new company status and that revoked all previous copies.'
    ACCESS_REMOVED = 'Your role in the business was changed and you no longer have system access to the business.'
    SELF_REISSUANCE = 'You chose to issue yourself a new credential and that revoked all previous copies.'
    SELF_REVOCATION = 'You chose to revoke your own credential.'


def get_issued_digital_credentials(business: Business):
    try:
        connection = DCConnection.find_active_by(business_id=business.id)
        if not connection:
            raise Exception(f'{Business.identifier} active connection not found.')

        issued_credentials = DCIssuedCredential.find_by(dc_connection_id=connection.id)
        if not issued_credentials:
            return []

        return issued_credentials
    except Exception as err:
        raise err


def issue_digital_credential(business: Business, credential_type: DCDefinition.credential_type):
    try:
        definition = DCDefinition.find_by_credential_type(DCDefinition.CredentialType[credential_type])
        if (not definition):
            raise Exception(f'Definition not found for credential type: {credential_type}')

        connection = DCConnection.find_active_by(business_id=business.id)
        if (not connection):
            raise Exception(f'{Business.identifier} active connection not found.')

        issued = digital_credentials.issue_credential(
            connection_id=connection.connection_id,
            definition=definition,
            data=get_data_for_credential(business, definition.credential_type)
        )
        if not issued:
            raise Exception('Failed to issue credential.')

        issued_credential = DCIssuedCredential(
            dc_definition_id=definition.id,
            dc_connection_id=connection.id,
            credential_exchange_id=issued['cred_ex_id'],
            # TODO: Add a real ID
            credential_id='123456'
        )
        issued_credential.save()

        return issued_credential
    except Exception as err:
        raise err


def revoke_issued_digital_credential(business: Business, issued_credential: DCIssuedCredential, reason: DCRevocationReason):
    try:
        connection = DCConnection.find_active_by(business_id=business.id)
        if (not connection):
            raise Exception(f'{Business.identifier} active connection not found.')

        revoked = digital_credentials.revoke_credential(connection.connection_id,
                                                        issued_credential.credential_revocation_id,
                                                        issued_credential.revocation_registry_id,
                                                        reason)
        if not revoked:
            raise Exception('Failed to revoke credential.')

        return revoked
    except Exception as err:
        raise err


def replace_issued_digital_credential(business: Business, issued_credential: DCIssuedCredential, credential_type: DCDefinition.CredentialType, reason: DCRevocationReason):
    try:
        revoke_issued_digital_credential(business, issued_credential, reason)
        issued_credential.delete()

        return issue_digital_credential(business, credential_type)
    except Exception as err:
        raise err


def get_digital_credential_data(business: Business, credential_type: DCDefinition.CredentialType,):
    if credential_type == DCDefinition.CredentialType.business:
        return [
            {
                'name': 'credential_id',
                'value': ''
            },
            {
                'name': 'identifier',
                'value': business.identifier
            },
            {
                'name': 'business_name',
                'value': business.legal_name
            },
            {
                'name': 'business_type',
                'value': business.legal_type
            },
            {
                'name': 'cra_business_number',
                'value': business.tax_id or ''
            },
            {
                'name': 'registered_on_dateint',
                'value': business.founding_date.isoformat()
            },
            {
                'name': 'company_status',
                'value': business.state
            },
            {
                'name': 'family_name',
                'value': ''
            },
            {
                'name': 'given_names',
                'value': ''
            },
            {
                'name': 'role',
                'value': ''
            }
        ]

    return None
