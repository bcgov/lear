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
"""The Unit Tests and the helper routines."""

from legal_api.models import Business, DCConnection, DCCredential, DCDefinition, Filing
from legal_api.models.db import VersioningProxy
from legal_api.models.dc_business_user import DCBusinessUser
from legal_api.models.user import User


def create_business(identifier):
    """Return a test business."""
    business = Business(identifier=identifier,
                        legal_type=Business.LegalTypes.SOLE_PROP,
                        legal_name='test_business')
    business.save()
    return business


def create_user(username='test_user', firstname='Test', lastname='User'):
    """Return a test user."""
    user = User(username=username, firstname=firstname, lastname=lastname)
    user.save()
    return user


def create_filing(session,
                  business_id=None,
                  filing_json=None,
                  filing_type=None,
                  filing_status=Filing.Status.COMPLETED.value):
    """Return a test filing."""
    filing = Filing()
    filing._filing_type = filing_type
    filing._filing_sub_type = 'test'
    filing._status = filing_status

    if filing_status == Filing.Status.COMPLETED.value:
        transaction_id = VersioningProxy.get_transaction_id(session())
        filing.transaction_id = transaction_id
    if filing_json:
        filing.filing_json = filing_json
    if business_id:
        filing.business_id = business_id

    filing.save()
    return filing


def create_dc_business_user(business, user) -> DCBusinessUser:
    """Create new dc_business_user object."""
    business_user = DCBusinessUser(
        business_id=business.id,
        user_id=user.id
    )
    business_user.save()
    return business_user


def create_dc_definition():
    """Create new dc_definition object."""
    definition = DCDefinition(
        credential_type=DCDefinition.CredentialType.business.name,
        schema_name='test_business_schema',
        schema_version='1.0.0',
        schema_id='test_schema_id',
        credential_definition_id='test_credential_definition_id'
    )
    definition.save()
    return definition


def create_dc_connection(business_user: DCBusinessUser, is_active=False) -> DCConnection:
    """Create new dc_connection object."""
    connection = DCConnection(
        connection_id='0d94e18b-3a52-4122-8adf-33e2ccff681f',
        invitation_url="""http://192.168.65.3:8020?c_i=eyJAdHlwZSI6ICJodHRwczovL2RpZGNvbW0ub3JnL2Nvbm5lY3Rpb
25zLzEuMC9pbnZpdGF0aW9uIiwgIkBpZCI6ICIyZjU1M2JkZS01YWJlLTRkZDctODIwZi1mNWQ2Mjc1OWQxODgi
LCAicmVjaXBpZW50S2V5cyI6IFsiMkFHSjVrRDlVYU45OVpSeUFHZVZKNDkxclZhNzZwZGZYdkxXZkFyc2lKWjY
iXSwgImxhYmVsIjogImZhYmVyLmFnZW50IiwgInNlcnZpY2VFbmRwb2ludCI6ICJodHRwOi8vMTkyLjE2OC42NS4zOjgwMjAifQ==""",
        is_active=is_active,
        connection_state=DCConnection.State.ACTIVE.value if is_active else DCConnection.State.INVITATION_SENT.value,
        business_user_id=business_user.id,
        # Kept for legacy reasons, remove when possible
        business_id=business_user.business_id
    )
    connection.save()
    return connection


def create_dc_credential(business_user=None,
                         credential_exchange_id='test_credential_exchange_id',
                         credential_revocation_id='123',
                         revocation_registry_id='123',
                         is_issued=True,
                         is_revoked=False) -> DCCredential:
    """Create new dc_credential object."""
    if not business_user:
        identifier = 'FM1234567'
        business_user = create_dc_business_user(
            create_business(identifier), create_user())
    definition = create_dc_definition()
    connection = create_dc_connection(business_user, is_active=True)
    issued_credential = DCCredential(
        definition_id=definition.id,
        connection_id=connection.id,
        credential_exchange_id=credential_exchange_id,
        credential_revocation_id=credential_revocation_id,
        revocation_registry_id=revocation_registry_id,
        is_issued=is_issued,
        is_revoked=is_revoked
    )
    issued_credential.save()
    return issued_credential
