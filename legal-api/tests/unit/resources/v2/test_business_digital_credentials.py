# Copyright © 2022 Province of British Columbia
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

"""Tests to assure the digital credentials API end-point.

Test-Suite to ensure that the /digitalCredentials endpoint is working as expected.
"""

from datetime import datetime
from http import HTTPStatus
from unittest.mock import patch

from legal_api.services.authz import BASIC_USER
from legal_api.models import Business, DCConnection, DCDefinition, User
from legal_api.services.digital_credentials import DigitalCredentialsService

from tests.unit.models import factory_business
from tests.unit.models.test_dc_connection import create_dc_connection
from tests.unit.models.test_dc_definition import create_dc_definition
from tests.unit.models.test_dc_credential import create_dc_credential
from tests.unit.services.utils import create_header


content_type = 'application/json'


@patch('legal_api.decorators.are_digital_credentials_allowed', return_value=True)
def test_create_invitation(app, session, client, jwt):  # pylint:disable=unused-argument
    """Assert create invitation endpoint returns invitation_url."""
    headers = create_header(jwt, [BASIC_USER])
    identifier = 'FM1234567'
    factory_business(identifier)

    invitation_id = '0d94e18b-3a52-4122-8adf-33e2ccff681f'
    invitation_url = """http://192.168.65.3:8020?c_i=eyJAdHlwZSI6ICJodHRwczovL2RpZGNvbW0ub3JnL2Nvbm5lY3Rpb
25zLzEuMC9pbnZpdGF0aW9uIiwgIkBpZCI6ICIyZjU1M2JkZS01YWJlLTRkZDctODIwZi1mNWQ2Mjc1OWQxODgi
LCAicmVjaXBpZW50S2V5cyI6IFsiMkFHSjVrRDlVYU45OVpSeUFHZVZKNDkxclZhNzZwZGZYdkxXZkFyc2lKWjY
iXSwgImxhYmVsIjogImZhYmVyLmFnZW50IiwgInNlcnZpY2VFbmRwb2ludCI6ICJodHRwOi8vMTkyLjE2OC42NS4zOjgwMjAifQ=="""

    with patch.object(DigitalCredentialsService, 'create_invitation', return_value={
            'invitation': {'@id': invitation_id}, 'invitation_url': invitation_url}):

        rv = client.post(f'/api/v2/businesses/{identifier}/digitalCredentials/invitation',
                         headers=headers, content_type=content_type)
        assert rv.status_code == HTTPStatus.OK
        assert rv.json.get('invitationUrl') == invitation_url


@patch('legal_api.decorators.are_digital_credentials_allowed', return_value=True)
def test_get_connections_not_found(app, session, client, jwt):  # pylint:disable=unused-argument
    """Assert get connections endpoint returns not found when there is no active connection."""
    headers = create_header(jwt, [BASIC_USER])
    identifier = 'FM1234567'
    factory_business(identifier)

    rv = client.get(f'/api/v2/businesses/{identifier}/digitalCredentials/connections',
                    headers=headers, content_type=content_type)
    assert rv.status_code == HTTPStatus.OK
    assert rv.json.get('connections') == []


@patch('legal_api.decorators.are_digital_credentials_allowed', return_value=True)
def test_get_connections(app, session, client, jwt):  # pylint:disable=unused-argument
    """Assert get connection endpoint returns connection json."""
    headers = create_header(jwt, [BASIC_USER])
    identifier = 'FM1234567'
    business = factory_business(identifier)

    connection = create_dc_connection(business, is_active=True)

    rv = client.get(f'/api/v2/businesses/{identifier}/digitalCredentials/connections',
                    headers=headers, content_type=content_type)

    assert rv.status_code == HTTPStatus.OK
    assert rv.json.get('connections')[0].get(
        'invitationUrl') == connection.invitation_url
    assert rv.json.get('connections')[0].get(
        'connectionId') == connection.connection_id
    assert rv.json.get('connections')[0].get(
        'isActive') == connection.is_active
    assert rv.json.get('connections')[0].get(
        'connectionState') == connection.connection_state


@patch('legal_api.decorators.are_digital_credentials_allowed', return_value=True)
def test_attest_connection(app, session, client, jwt):  # pylint:disable=unused-argument
    """Assert attest connection endpoint sends a request."""
    headers = create_header(jwt, [BASIC_USER])
    identifier = 'FM1234567'
    business = factory_business(identifier)

    connection = create_dc_connection(business)

    with patch.object(DigitalCredentialsService, 'attest_connection', return_value={}):
        rv = client.post(f'/api/v2/businesses/{identifier}/digitalCredentials/connections/{connection.connection_id}/attest',
                         headers=headers, content_type=content_type)
        assert rv.status_code == HTTPStatus.OK
        assert rv.json.get('message') == 'Connection attestation request sent.'


@patch('legal_api.decorators.are_digital_credentials_allowed', return_value=True)
def test_attest_connection_fail(app, session, client, jwt):  # pylint:disable=unused-argument
    """Assert attest connection endpoint fails to send a request."""
    headers = create_header(jwt, [BASIC_USER])
    identifier = 'FM1234567'
    business = factory_business(identifier)

    connection = create_dc_connection(business)

    with patch.object(DigitalCredentialsService, 'attest_connection', return_value=None):
        rv = client.post(f'/api/v2/businesses/{identifier}/digitalCredentials/connections/{connection.connection_id}/attest',
                         headers=headers, content_type=content_type)
        assert rv.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert rv.json.get(
            'message') == 'Unable to request connection attestation.'


@patch('legal_api.decorators.are_digital_credentials_allowed', return_value=True)
def test_send_credential(app, session, client, jwt):  # pylint:disable=unused-argument
    """Assert issue credentials to the connection."""
    headers = create_header(jwt, [BASIC_USER])
    identifier = 'FM1234567'
    business = factory_business(
        identifier, entity_type=Business.LegalTypes.BCOMP.value)
    definition = create_dc_definition()
    test_user = User(username='test-user', firstname='test', lastname='test')
    test_user.save()
    create_dc_connection(business, is_active=True)
    cred_ex_id = '3fa85f64-5717-4562-b3fc-2c963f66afa6'

    json_data = {}

    with patch.object(User, 'find_by_jwt_token', return_value=test_user):
        with patch.object(DCDefinition, 'find_by', return_value=definition):
            with patch.object(DCConnection, 'find_active_by', return_value=DCConnection(is_attested=True,
                                                                                        last_attested=datetime.utcnow())):
                with patch.object(DigitalCredentialsService, 'issue_credential', return_value={'cred_ex_id': cred_ex_id}):
                    rv = client.post(
                        f'/api/v2/businesses/{identifier}/digitalCredentials/{DCDefinition.CredentialType.business.name}',
                        json=json_data, headers=headers, content_type=content_type)
                    assert rv.status_code == HTTPStatus.OK
                    assert rv.json.get('credentialExchangeId') == cred_ex_id


@patch('legal_api.decorators.are_digital_credentials_allowed', return_value=True)
def test_send_credential_attestation_not_complete_fail(app, session, client, jwt):  # pylint:disable=unused-argument
    """Assert issue credentials to the connection fails when attestation not complete."""
    headers = create_header(jwt, [BASIC_USER])
    identifier = 'FM1234567'
    business = factory_business(identifier)
    definition = create_dc_definition()
    test_user = User(username='test-user', firstname='test', lastname='test')
    test_user.save()
    create_dc_connection(business, is_active=True)
    cred_ex_id = '3fa85f64-5717-4562-b3fc-2c963f66afa6'

    with patch.object(User, 'find_by_jwt_token', return_value=test_user):
        with patch.object(DCDefinition, 'find_by', return_value=definition):
            with patch.object(DCConnection, 'find_active_by', return_value=DCConnection(is_attested=False,
                                                                                        last_attested=None)):
                with patch.object(DigitalCredentialsService, 'issue_credential', return_value={'cred_ex_id': cred_ex_id}):
                    rv = client.post(
                        f'/api/v2/businesses/{identifier}/digitalCredentials/{DCDefinition.CredentialType.business.name}',
                        headers=headers, content_type=content_type)
                    assert rv.status_code == HTTPStatus.UNAUTHORIZED
                    assert rv.json.get(
                        'message') == 'Connection not attested.'


@patch('legal_api.decorators.are_digital_credentials_allowed', return_value=True)
def test_send_credential_attestation_fail(app, session, client, jwt):  # pylint:disable=unused-argument
    """Assert issue credentials to the connection fails attestation."""
    headers = create_header(jwt, [BASIC_USER])
    identifier = 'FM1234567'
    business = factory_business(identifier)
    definition = create_dc_definition()
    test_user = User(username='test-user', firstname='test', lastname='test')
    test_user.save()
    create_dc_connection(business, is_active=True)
    cred_ex_id = '3fa85f64-5717-4562-b3fc-2c963f66afa6'

    with patch.object(User, 'find_by_jwt_token', return_value=test_user):
        with patch.object(DCDefinition, 'find_by', return_value=definition):
            with patch.object(DCConnection, 'find_active_by', return_value=DCConnection(is_attested=False,
                                                                                        last_attested=datetime.utcnow())):
                with patch.object(DigitalCredentialsService, 'issue_credential', return_value={'cred_ex_id': cred_ex_id}):
                    rv = client.post(
                        f'/api/v2/businesses/{identifier}/digitalCredentials/{DCDefinition.CredentialType.business.name}',
                        headers=headers, content_type=content_type)
                    assert rv.status_code == HTTPStatus.UNAUTHORIZED
                    assert rv.json.get(
                        'message') == 'Connection failed attestation.'


@patch('legal_api.decorators.are_digital_credentials_allowed', return_value=True)
def test_get_issued_credentials(app, session, client, jwt):  # pylint:disable=unused-argument
    """Assert get all issued credentials json."""
    headers = create_header(jwt, [BASIC_USER])
    identifier = 'FM1234567'
    business = factory_business(identifier)

    issued_credential = create_dc_credential(business=business)

    rv = client.get(
        f'/api/v2/businesses/{identifier}/digitalCredentials', headers=headers, content_type=content_type)
    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json.get('issuedCredentials')) == 1
    assert rv.json.get('issuedCredentials')[0].get(
        'legalName') == business.legal_name
    assert rv.json.get('issuedCredentials')[0].get(
        'credentialType') == DCDefinition.CredentialType.business.name
    assert rv.json.get('issuedCredentials')[0].get(
        'credentialId') == issued_credential.credential_id
    assert not rv.json.get('issuedCredentials')[0].get('isIssued')
    assert rv.json.get('issuedCredentials')[0].get('dateOfIssue') == ''
    assert not rv.json.get('issuedCredentials')[0].get('isRevoked')


@patch('legal_api.decorators.are_digital_credentials_allowed', return_value=True)
def test_webhook_connections_notification(app, session, client, jwt):  # pylint:disable=unused-argument
    """Assert webhook connection notification endpoint when connection to active."""
    headers = create_header(jwt, [BASIC_USER])
    identifier = 'FM1234567'
    business = factory_business(identifier)

    connection = create_dc_connection(business)

    json_data = {
        'invitation': {'@id': connection.connection_id},
        "connection_id": connection.connection_id,
        'state': 'active'
    }
    rv = client.post('/api/v2/digitalCredentials/topic/connections',
                     json=json_data,
                     headers=headers, content_type=content_type)
    assert rv.status_code == HTTPStatus.OK

    rv = client.get(f'/api/v2/businesses/{identifier}/digitalCredentials/connections',
                    headers=headers, content_type=content_type)
    assert rv.status_code == HTTPStatus.OK
    assert rv.json.get('connections')[0].get(
        'isActive') == connection.is_active
    assert rv.json.get('connections')[0].get(
        'connectionState') == connection.connection_state


@patch('legal_api.decorators.are_digital_credentials_allowed', return_value=True)
def test_webhook_issue_credential_notification(app, session, client, jwt):  # pylint:disable=unused-argument
    """Assert webhook issue_credential notification endpoint when credential issued."""
    headers = create_header(jwt, [BASIC_USER])
    identifier = 'FM1234567'
    business = factory_business(identifier)

    issued_credential = create_dc_credential(business=business)

    json_data = {
        'cred_ex_id': issued_credential.credential_exchange_id,
        'state': 'done'
    }
    rv = client.post('/api/v2/digitalCredentials/topic/issue_credential_v2_0',
                     json=json_data,
                     headers=headers, content_type=content_type)
    assert rv.status_code == HTTPStatus.OK

    rv = client.get(f'/api/v2/businesses/{identifier}/digitalCredentials',
                    headers=headers, content_type=content_type)
    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json.get('issuedCredentials')) == 1
    assert rv.json.get('issuedCredentials')[0].get('isIssued')
    assert rv.json.get('issuedCredentials')[0].get('dateOfIssue')
    assert not rv.json.get('issuedCredentials')[0].get('isRevoked')


@patch('legal_api.decorators.are_digital_credentials_allowed', return_value=True)
def test_webhook_connection_attest_notification(app, session, client, jwt):
    """Assert webhook connection attest notification endpoint when connection attested."""
    headers = create_header(jwt, [BASIC_USER])
    identifier = 'FM1234567'
    business = factory_business(identifier)

    connection = create_dc_connection(business)

    json_data = {
        'connection_id': connection.connection_id,
        'state': 'done',
        'verified': 'true'
    }
    rv = client.post('/api/v2/digitalCredentials/topic/present_proof_v2_0',
                     json=json_data,
                     headers=headers, content_type=content_type)
    assert rv.status_code == HTTPStatus.OK

    rv = client.get(f'/api/v2/businesses/{identifier}/digitalCredentials/connections',
                    headers=headers, content_type=content_type)
    assert rv.status_code == HTTPStatus.OK
    assert rv.status_code == HTTPStatus.OK
    assert rv.json.get('connections')[0].get('isAttested') == True
    assert rv.json.get('connections')[0].get('lastAttested') != ''
    assert rv.json.get('connections')[0].get(
        'connectionState') == connection.connection_state
