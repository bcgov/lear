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

from legal_api.models import (
    Business,
    CorpType,
    DCConnection,
    DCDefinition,
    DCIssuedBusinessUserCredential,
    DCIssuedCredential,
    User,
)
from legal_api.services import digital_credentials


class DCRevocationReason(Enum):
    """Digital Credential Revocation Reasons."""

    UPDATED_INFORMATION = 'You were offered a new credential with updated information \
        and that revoked all previous copies.'
    VOLUNTARY_DISSOLUTION = 'You chose to dissolve your business. \
        A new credential was offered that reflects the new company status and that revoked all previous copies.'
    ADMINISTRATIVE_DISSOLUTION = 'Your business was dissolved by the Registrar.'
    PUT_BACK_ON = 'Your business was put back on the Registry.'
    RESTORATION = 'Your business was put back on the Registry. \
        A new credential was offered that reflects the new company status and that revoked all previous copies.'
    ACCESS_REMOVED = 'Your role in the business was changed and you no longer have system access to the business.'
    SELF_REISSUANCE = 'You chose to issue yourself a new credential and that revoked all previous copies.'
    SELF_REVOCATION = 'You chose to revoke your own credential.'


def get_issued_digital_credentials(business: Business):
    """Get issued digital credentials for a business."""
    try:
        if not (connection := DCConnection.find_active_by(business_id=business.id)):
            raise Exception(f'{Business.identifier} active connection not found.')

        if not (issued_credentials := DCIssuedCredential.find_by(dc_connection_id=connection.id)):
            return []

        return issued_credentials
    except Exception as err:
        raise err


def issue_digital_credential(business: Business, user: User, credential_type: DCDefinition.credential_type):
    """Issue a digital credential for a business."""
    try:
        if not (definition := DCDefinition.find_by_credential_type(DCDefinition.CredentialType[credential_type])):
            raise Exception(f'Definition not found for credential type: {credential_type}')

        if not (connection := DCConnection.find_active_by(business_id=business.id)):
            raise Exception(f'{Business.identifier} active connection not found.')

        if not (issued := digital_credentials.issue_credential(
            connection_id=connection.connection_id,
            definition=definition,
            credential_data=get_digital_credential_data(business, user, definition.credential_type)
        )):
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


def revoke_issued_digital_credential(business: Business,
                                     issued_credential: DCIssuedCredential,
                                     reason: DCRevocationReason):
    """Revoke an issued digital credential for a business."""
    try:
        if not (connection := DCConnection.find_active_by(business_id=business.id)):
            raise Exception(f'{Business.identifier} active connection not found.')

        if not (revoked := digital_credentials.revoke_credential(connection.connection_id,
                                                                 issued_credential.credential_revocation_id,
                                                                 issued_credential.revocation_registry_id,
                                                                 reason)):
            raise Exception('Failed to revoke credential.')

        return revoked
    except Exception as err:
        raise err


def replace_issued_digital_credential(business: Business,
                                      issued_credential: DCIssuedCredential,
                                      credential_type: DCDefinition.CredentialType,
                                      reason: DCRevocationReason):
    """Replace an issued digital credential for a business."""
    try:
        revoke_issued_digital_credential(business, issued_credential, reason)
        issued_credential.delete()

        return issue_digital_credential(business, credential_type)
    except Exception as err:
        raise err


def get_digital_credential_data(business: Business, user: User, credential_type: DCDefinition.CredentialType):
    """Get the data for a digital credential."""
    if credential_type == DCDefinition.CredentialType.business:

        # Find the credential id from dc_issued_business_user_credentials and if there isn't one create one
        if not (issued_business_user_credential := DCIssuedBusinessUserCredential.find_by(
                business_id=business.id, user_id=user.id)):
            issued_business_user_credential = DCIssuedBusinessUserCredential(business_id=business.id, user_id=user.id)
            issued_business_user_credential.save()

        credential_id = f'{issued_business_user_credential.id:08}'

        if (business_type := CorpType.find_by_id(business.legal_type)):
            business_type = business_type.full_desc
        else:
            business_type = business.legal_type

        registered_on_dateint = ''
        if business.founding_date:
            registered_on_dateint = business.founding_date.strftime('%Y%m%d')

        company_status = Business.State(business.state).name

        family_name = (user.lastname or '').strip().upper()

        given_names = ' '.join([x.strip() for x in [user.firstname, user.middlename] if x and x.strip()]).upper()

        return [
            {
                'name': 'credential_id',
                'value':  credential_id or ''
            },
            {
                'name': 'identifier',
                'value': business.identifier or ''
            },
            {
                'name': 'business_name',
                'value': business.legal_name or ''
            },
            {
                'name': 'business_type',
                'value': business_type or ''
            },
            {
                'name': 'cra_business_number',
                'value': business.tax_id or ''
            },
            {
                'name': 'registered_on_dateint',
                'value': registered_on_dateint or ''
            },
            {
                'name': 'company_status',
                'value': company_status or ''
            },
            {
                'name': 'family_name',
                'value': family_name or ''
            },
            {
                'name': 'given_names',
                'value': given_names or ''
            },
            {
                'name': 'role',
                'value': ''
            }
        ]

    return None


def extract_invitation_message_id(json_message: dict):
    """Extract the invitation message id from the json message."""
    if 'invitation' in json_message and json_message['invitation'] is not None:
        invitation_message_id = json_message['invitation']['@id']
    else:
        invitation_message_id = json_message['invitation_msg_id']
    return invitation_message_id
