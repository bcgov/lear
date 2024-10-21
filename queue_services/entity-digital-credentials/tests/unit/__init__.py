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

from legal_api.models import Business, DCConnection, DCDefinition, DCIssuedCredential, Filing
from legal_api.models.db import versioning_manager


def create_business(identifier):
    """Return a test business."""
    business = Business()
    business.identifier = identifier
    business.legal_type = Business.LegalTypes.SOLE_PROP
    business.legal_name = 'test_business'
    business.save()
    return business


def create_filing(session,  business_id=None,
                  filing_json=None, filing_type=None,
                  filing_status=Filing.Status.COMPLETED.value):
    """Return a test filing."""
    filing = Filing()
    filing._filing_type = filing_type
    filing._filing_sub_type = 'test'
    filing._status = filing_status

    if filing_status == Filing.Status.COMPLETED.value:
        uow = versioning_manager.unit_of_work(session)
        transaction = uow.create_transaction(session)
        filing.transaction_id = transaction.id
    if filing_json:
        filing.filing_json = filing_json
    if business_id:
        filing.business_id = business_id

    filing.save()
    return filing


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


def create_dc_connection(business, is_active=False):
    """Create new dc_connection object."""
    connection = DCConnection(
        connection_id='0d94e18b-3a52-4122-8adf-33e2ccff681f',
        invitation_url="""http://192.168.65.3:8020?c_i=eyJAdHlwZSI6ICJodHRwczovL2RpZGNvbW0ub3JnL2Nvbm5lY3Rpb
25zLzEuMC9pbnZpdGF0aW9uIiwgIkBpZCI6ICIyZjU1M2JkZS01YWJlLTRkZDctODIwZi1mNWQ2Mjc1OWQxODgi
LCAicmVjaXBpZW50S2V5cyI6IFsiMkFHSjVrRDlVYU45OVpSeUFHZVZKNDkxclZhNzZwZGZYdkxXZkFyc2lKWjY
iXSwgImxhYmVsIjogImZhYmVyLmFnZW50IiwgInNlcnZpY2VFbmRwb2ludCI6ICJodHRwOi8vMTkyLjE2OC42NS4zOjgwMjAifQ==""",
        is_active=is_active,
        connection_state='active' if is_active else 'invitation',
        business_id=business.id
    )
    connection.save()
    return connection


def create_dc_issued_credential(business=None,
                                credential_exchange_id='test_credential_exchange_id',
                                credential_revocation_id='123',
                                revocation_registry_id='123',
                                is_issued=True, is_revoked=False):
    """Create new dc_issued_credential object."""
    if not business:
        identifier = 'FM1234567'
        business = create_business(identifier)
    definition = create_dc_definition()
    connection = create_dc_connection(business, is_active=True)
    issued_credential = DCIssuedCredential(
        dc_definition_id=definition.id,
        dc_connection_id=connection.id,
        credential_exchange_id=credential_exchange_id,
        credential_revocation_id=credential_revocation_id,
        revocation_registry_id=revocation_registry_id,
        is_issued=is_issued,
        is_revoked=is_revoked
    )
    issued_credential.save()
    return issued_credential
