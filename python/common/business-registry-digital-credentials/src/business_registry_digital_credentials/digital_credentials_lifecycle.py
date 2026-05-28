# Copyright © 2025 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Credential-lifecycle helpers: DB-persistence wrappers over the Traction service.

These wrap the ``digital_credentials`` singleton (Traction REST client) with
``DCCredential`` row save/delete/update operations. Pulled out of the queue
service so both legal-api and the queue service can share them.

The ``digital_credentials`` singleton is bound at module import time — package
``__init__.py`` creates it BEFORE importing this module, so the top-level
``from . import digital_credentials`` resolves cleanly. Tests can patch
``business_registry_digital_credentials.digital_credentials_lifecycle.digital_credentials``
to swap out the Traction client.
"""

from business_model.models import Business, DCBusinessUser, DCConnection, DCCredential, DCDefinition, DCRevocationReason

from . import digital_credentials
from .digital_credentials_helpers import get_digital_credential_data


class DigitalCredentialError(Exception):
    """Raised when an issue/revoke/replace lifecycle operation cannot complete."""


def get_all_digital_credentials_for_business(business: Business) -> list[DCCredential]:
    """Get all currently-issued, non-revoked digital credentials for a business.

    TODO: Once DCCredential references DCBusinessUser, this function can be refactored.
    """
    credentials = []
    for business_user in business.business_users:
        active_connections = [conn for conn in business_user.connections if conn.is_active]
        if active_connections and len(active_connections) == 1:
            active_connection = active_connections[0]
            for credential in active_connection.credentials:
                if credential.is_issued and not credential.is_revoked:
                    credentials.append(credential)
    return credentials


def issue_digital_credential(
    business_user: DCBusinessUser,
    credential_type: DCDefinition.CredentialType | str,
) -> DCCredential:
    """Issue a digital credential for a business to a user.

    ``credential_type`` accepts either a ``DCDefinition.CredentialType`` enum
    member or its name string (e.g. ``"business"``).
    """
    ct = (
        credential_type
        if isinstance(credential_type, DCDefinition.CredentialType)
        else DCDefinition.CredentialType[credential_type]
    )
    if not (
        definition := DCDefinition.find_by(
            ct,
            digital_credentials.business_schema_id,
            digital_credentials.business_cred_def_id,
        )
    ):
        raise DigitalCredentialError(f"Definition not found for credential type: {credential_type}.")

    if not (connection := DCConnection.find_active_by_business_user_id(business_user_id=business_user.id)):
        raise DigitalCredentialError(f"Active connection not found for business user with ID: {business_user.id}.")

    credential_data = get_digital_credential_data(business_user, definition.credential_type)
    credential_id = next(
        (item["value"] for item in credential_data if item["name"] == "credential_id"),
        None,
    )

    if not (
        response := digital_credentials.issue_credential(
            connection_id=connection.connection_id,
            definition=definition,
            data=credential_data,
        )
    ):
        raise DigitalCredentialError("Failed to issue credential.")

    issued_credential = DCCredential(
        definition_id=definition.id,
        connection_id=connection.id,
        business_user_id=business_user.id,
        credential_exchange_id=response["cred_ex_id"],
        credential_id=credential_id,
    )
    issued_credential.save()
    return issued_credential


def revoke_digital_credential(credential: DCCredential, reason: DCRevocationReason) -> None:
    """Revoke an issued digital credential."""
    if not credential.is_issued or credential.is_revoked:
        raise DigitalCredentialError("Credential is not issued yet or is revoked already.")

    if not (connection := credential.connection) or not connection.is_active:
        raise DigitalCredentialError(f"Active connection not found for credential with ID: {credential.credential_id}.")

    if (
        digital_credentials.revoke_credential(
            connection.connection_id,
            credential.credential_revocation_id,
            credential.revocation_registry_id,
            reason,
        )
        is None
    ):
        raise DigitalCredentialError("Failed to revoke credential.")

    credential.is_revoked = True
    credential.save()


def replace_digital_credential(
    credential: DCCredential,
    credential_type: DCDefinition.CredentialType,
    reason: DCRevocationReason,
) -> None:
    """Replace an issued digital credential: revoke, issue new, delete old."""
    if credential.is_issued and not credential.is_revoked:
        revoke_digital_credential(credential, reason)

    if (
        digital_credentials.fetch_credential_exchange_record(credential.credential_exchange_id) is not None
        and digital_credentials.remove_credential_exchange_record(credential.credential_exchange_id) is None
    ):
        raise DigitalCredentialError("Failed to remove credential exchange record.")

    issue_digital_credential(credential.connection.business_user, credential_type)
    # We delete the old credential after issuing the new one so that the connection is not lost
    credential.delete()
