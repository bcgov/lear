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

from http import HTTPStatus
from unittest.mock import patch

from legal_api.services.authz import BASIC_USER
from legal_api.services.digital_credentials import DigitalCredentialsService

from tests.unit.models import factory_business
from tests.unit.models.test_dc_connection import create_dc_connection
from tests.unit.services.utils import create_header


content_type = 'application/json'


def test_create_invitation(client, jwt, session):  # pylint:disable=unused-argument
    """Assert create invitation endpoint returns invitation_url."""
    headers = create_header(jwt, [BASIC_USER])
    identifier = 'FM1234567'
    factory_business(identifier)

    connection_id = '0d94e18b-3a52-4122-8adf-33e2ccff681f'
    invitation_url = """http://192.168.65.3:8020?c_i=eyJAdHlwZSI6ICJodHRwczovL2RpZGNvbW0ub3JnL2Nvbm5lY3Rpb
25zLzEuMC9pbnZpdGF0aW9uIiwgIkBpZCI6ICIyZjU1M2JkZS01YWJlLTRkZDctODIwZi1mNWQ2Mjc1OWQxODgi
LCAicmVjaXBpZW50S2V5cyI6IFsiMkFHSjVrRDlVYU45OVpSeUFHZVZKNDkxclZhNzZwZGZYdkxXZkFyc2lKWjY
iXSwgImxhYmVsIjogImZhYmVyLmFnZW50IiwgInNlcnZpY2VFbmRwb2ludCI6ICJodHRwOi8vMTkyLjE2OC42NS4zOjgwMjAifQ=="""

    with patch.object(DigitalCredentialsService, 'create_invitation', return_value={
            'connection_id': connection_id, 'invitation_url': invitation_url}):
        rv = client.post(f'/api/v2/businesses/{identifier}/digitalCredentials/invitation',
                         headers=headers, content_type=content_type)
        assert rv.status_code == HTTPStatus.OK
        assert rv.json.get('invitationUrl') == invitation_url


def test_get_connection_not_found(client, jwt, session):  # pylint:disable=unused-argument
    """Assert get connection endpoint returns not found when there is no active connection."""
    headers = create_header(jwt, [BASIC_USER])
    identifier = 'FM1234567'
    business = factory_business(identifier)
    create_dc_connection(business)

    rv = client.get(f'/api/v2/businesses/{identifier}/digitalCredentials/connection',
                    headers=headers, content_type=content_type)
    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json.get('message') == 'No active connection found.'


def test_get_connection(client, jwt, session):  # pylint:disable=unused-argument
    """Assert get connection endpoint returns connection json."""
    headers = create_header(jwt, [BASIC_USER])
    identifier = 'FM1234567'
    business = factory_business(identifier)

    connection = create_dc_connection(business)
    connection.is_active = True
    connection.connection_state = 'active'

    rv = client.get(f'/api/v2/businesses/{identifier}/digitalCredentials/connection',
                    headers=headers, content_type=content_type)
    assert rv.status_code == HTTPStatus.OK
    assert rv.json.get('invitationUrl') == connection.invitation_url
    assert rv.json.get('connectionId') == connection.connection_id
    assert rv.json.get('isActive') == connection.is_active
    assert rv.json.get('connectionState') == connection.connection_state


def test_webhook_connection_notification(client, jwt, session):  # pylint:disable=unused-argument
    """Assert webhook connection notification endpoint updated connection to active."""
    headers = create_header(jwt, [BASIC_USER])
    identifier = 'FM1234567'
    business = factory_business(identifier)

    connection = create_dc_connection(business)

    json_data = {
        'connection_id': connection.connection_id,
        'state': 'active'
    }
    rv = client.post('/api/v2/digitalCredentials/topic/connections',
                     json=json_data,
                     headers=headers, content_type=content_type)
    assert rv.status_code == HTTPStatus.OK

    rv = client.get(f'/api/v2/businesses/{identifier}/digitalCredentials/connection',
                    headers=headers, content_type=content_type)
    assert rv.status_code == HTTPStatus.OK
    assert rv.json.get('isActive') == connection.is_active
    assert rv.json.get('connectionState') == connection.connection_state
