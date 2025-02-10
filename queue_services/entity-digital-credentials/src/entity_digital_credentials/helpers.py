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

from legal_api.models import (
    Business,
    DCConnection,
    DCDefinition,
    DCIssuedBusinessUserCredential,
    DCIssuedCredential,
    DCRevocationReason,
    User,
)
from legal_api.services import digital_credentials
from legal_api.services.digital_credentials_helpers import get_digital_credential_data


def get_issued_digital_credentials(business: Business):
    """Get issued digital credentials for a business."""
    try:
        # pylint: disable=superfluous-parens
        if not (connection := DCConnection.find_active_by(business_id=business.id)):
            # pylint: disable=broad-exception-raised
            raise Exception(
                f'{business.identifier} active connection not found.')

        # pylint: disable=superfluous-parens
        if not (issued_credentials := DCIssuedCredential.find_by(dc_connection_id=connection.id)):
            return []

        return issued_credentials
    # pylint: disable=broad-exception-raised
    except Exception as err:  # noqa: B902
        raise err


def issue_digital_credential(business: Business, user: User, credential_type: DCDefinition.credential_type):
    """Issue a digital credential for a business to a user."""
    try:
        if not (definition := DCDefinition.find_by(DCDefinition.CredentialType[credential_type],
                                                   digital_credentials.business_schema_id,
                                                   digital_credentials.business_cred_def_id)):
            # pylint: disable=broad-exception-raised
            raise Exception(
                f'Definition not found for credential type: {credential_type}.')

        # pylint: disable=superfluous-parens
        if not (connection := DCConnection.find_active_by(business_id=business.id)):
            # pylint: disable=broad-exception-raised
            raise Exception(
                f'{business.identifier} active connection not found.')

        credential_data = get_digital_credential_data(
            user, business, definition.credential_type)
        credential_id = next(
            (item['value'] for item in credential_data if item['name'] == 'credential_id'), None)

        if not (response := digital_credentials.issue_credential(connection_id=connection.connection_id,
                                                                 definition=definition,
                                                                 data=credential_data)):
            raise Exception(
                'Failed to issue credential.')  # pylint: disable=broad-exception-raised

        issued_credential = DCIssuedCredential(
            dc_definition_id=definition.id,
            dc_connection_id=connection.id,
            credential_exchange_id=response['cred_ex_id'],
            credential_id=credential_id
        )
        issued_credential.save()

        return issued_credential
    # pylint: disable=broad-exception-raised
    except Exception as err:  # noqa: B902
        raise err


def revoke_issued_digital_credential(business: Business,
                                     issued_credential: DCIssuedCredential,
                                     reason: DCRevocationReason):
    """Revoke an issued digital credential for a business."""
    try:
        if not issued_credential.is_issued or issued_credential.is_revoked:
            # pylint: disable=broad-exception-raised
            raise Exception(
                'Credential is not issued yet or is revoked already.')

        # pylint: disable=superfluous-parens
        if not (connection := DCConnection.find_active_by(business_id=business.id)):
            # pylint: disable=broad-exception-raised
            raise Exception(
                f'{business.identifier} active connection not found.')

        if (revoked := digital_credentials.revoke_credential(connection.connection_id,
                                                             issued_credential.credential_revocation_id,
                                                             issued_credential.revocation_registry_id,
                                                             reason) is None):
            raise Exception(
                'Failed to revoke credential.')  # pylint: disable=broad-exception-raised

        issued_credential.is_revoked = True
        issued_credential.save()

        return revoked
    # pylint: disable=broad-exception-raised
    except Exception as err:  # noqa: B902
        raise err


def replace_issued_digital_credential(business: Business,
                                      issued_credential: DCIssuedCredential,
                                      credential_type: DCDefinition.CredentialType,
                                      reason: DCRevocationReason):  # pylint: disable=too-many-arguments
    """Replace an issued digital credential for a business."""
    try:
        if issued_credential.is_issued and not issued_credential.is_revoked:
            revoke_issued_digital_credential(
                business, issued_credential, reason)

        if (digital_credentials.fetch_credential_exchange_record(
                issued_credential.credential_exchange_id) is not None and
                digital_credentials.remove_credential_exchange_record(
                    issued_credential.credential_exchange_id) is None):
            raise Exception(
                'Failed to remove credential exchange record.')  # pylint: disable=broad-exception-raised

        if not (issued_business_user_credential := DCIssuedBusinessUserCredential.find_by_id(
                dc_issued_business_user_id=issued_credential.credential_id)):
            # pylint: disable=broad-exception-raised
            raise Exception(
                'Unable to find business user for issued credential.')

        if not (user := User.find_by_id(issued_business_user_credential.user_id)):  # pylint: disable=superfluous-parens
            # pylint: disable=broad-exception-raised
            raise Exception(
                'Unable to find user for issued business user credential.')

        issued_credential.delete()

        return issue_digital_credential(business, user, credential_type)
    # pylint: disable=broad-exception-raised
    except Exception as err:  # noqa: B902
        raise err
