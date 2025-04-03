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

from typing import List, Union

from legal_api.models import Business, DCBusinessUser, DCConnection, DCCredential, DCDefinition, DCRevocationReason
from legal_api.services import digital_credentials
from legal_api.services.digital_credentials_helpers import get_digital_credential_data


def get_all_digital_credentials_for_business(business: Business) -> Union[List[DCCredential], None]:
    """
    Get issued digital credentials for a business.

    TODO: Once DCCredential references DCBusinessUser, this function can be refactored
    """
    try:
        credentials = []
        for business_user in business.business_users:
            active_connections = list(filter(lambda connection: connection.is_active,
                                             business_user.connections))
            if active_connections and len(active_connections) == 1:
                active_connection = active_connections[0]
                for credential in list(filter(lambda credential: (credential.is_issued and not credential.is_revoked),
                                              active_connection.credentials)):
                    credentials.append(credential)

        return credentials
    # pylint: disable=broad-exception-raised
    except Exception as err:  # noqa: B902
        raise err


def issue_digital_credential(business_user: DCBusinessUser,
                             credential_type: DCDefinition.CredentialType) -> Union[DCCredential, None]:
    """Issue a digital credential for a business to a user."""
    try:
        if not (definition := DCDefinition.find_by(DCDefinition.CredentialType[credential_type],
                                                   digital_credentials.business_schema_id,
                                                   digital_credentials.business_cred_def_id)):
            # pylint: disable=broad-exception-raised
            raise Exception(
                f'Definition not found for credential type: {credential_type}.')

        # pylint: disable=superfluous-parens
        if not (connection := DCConnection.find_active_by_business_user_id(business_user_id=business_user.id)):
            # pylint: disable=broad-exception-raised
            raise Exception(
                f'Active connection not found for business user with ID: {business_user.id}.')

        credential_data = get_digital_credential_data(
            business_user, definition.credential_type)
        credential_id = next(
            (item['value'] for item in credential_data if item['name'] == 'credential_id'), None)

        if not (response := digital_credentials.issue_credential(connection_id=connection.connection_id,
                                                                 definition=definition,
                                                                 data=credential_data)):
            # pylint: disable=broad-exception-raised
            raise Exception('Failed to issue credential.')

        issued_credential = DCCredential(
            definition_id=definition.id,
            connection_id=connection.id,
            credential_exchange_id=response['cred_ex_id'],
            credential_id=credential_id
        )
        issued_credential.save()

        return issued_credential
    # pylint: disable=broad-exception-raised
    except Exception as err:  # noqa: B902
        raise err


def revoke_digital_credential(credential: DCCredential,
                              reason: DCRevocationReason) -> Union[dict, None]:
    """Revoke an issued digital credential."""
    try:
        if not credential.is_issued or credential.is_revoked:
            # pylint: disable=broad-exception-raised
            raise Exception(
                'Credential is not issued yet or is revoked already.')

        # pylint: disable=superfluous-parens
        if not (connection := credential.connection) or not connection.is_active:
            # pylint: disable=broad-exception-raised
            raise Exception(
                f'Active connection not found for credential with ID: {credential.credential_id}.')

        if (digital_credentials.revoke_credential(connection.connection_id,
                                                  credential.credential_revocation_id,
                                                  credential.revocation_registry_id,
                                                  reason) is None):
            # pylint: disable=broad-exception-raised
            raise Exception('Failed to revoke credential.')

        credential.is_revoked = True
        credential.save()

        return None
    # pylint: disable=broad-exception-raised
    except Exception as err:  # noqa: B902
        raise err


# pylint: disable=too-many-arguments
def replace_digital_credential(credential: DCCredential,
                               credential_type: DCDefinition.CredentialType,
                               reason: DCRevocationReason) -> Union[DCCredential, None]:
    """Replace an issued digital credential for a business."""
    try:
        if credential.is_issued and not credential.is_revoked:
            revoke_digital_credential(credential, reason)

        if (digital_credentials.fetch_credential_exchange_record(credential.credential_exchange_id) is not None
                and digital_credentials.remove_credential_exchange_record(credential.credential_exchange_id) is None):
            # pylint: disable=broad-exception-raised
            raise Exception('Failed to remove credential exchange record.')

        issue_digital_credential(credential.connection.business_user,
                                 credential_type)  # pylint: disable=too-many-function-args
        # We delete the old credential after issuing the new one so that the connection is not lost
        credential.delete()

        return None
    # pylint: disable=broad-exception-raised
    except Exception as err:  # noqa: B902
        raise err
