# Copyright © 2025 Province of British Columbia
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

"""Tests to assure the permissions end-point.

Test-Suite to ensure that the /permissions endpoint is working as expected.
"""
import pytest
from http import HTTPStatus

from legal_api.models import AuthorizedRole, AuthorizedRolePermission, Permission
from legal_api.services.authz import STAFF_ROLE, PUBLIC_USER

from tests.unit.services.utils import create_header


@pytest.fixture(scope='function')
def setup_permissions(session):
    """Fixture to set up roles and permissions for testing."""
    permission = Permission(permission_name='STAFF_ONLY_PERMISSION')
    session.add(permission)
    session.commit()

    role = session.query(AuthorizedRole).filter_by(role_name=STAFF_ROLE).first()
    if not role:
        role = AuthorizedRole(role_name=STAFF_ROLE)
        session.add(role)
        session.commit()

    role_permission = AuthorizedRolePermission(role_id=role.id, permission_id=permission.id)
    session.add(role_permission)
    session.commit()

def test_permissions_endpoint_with_unknown_role(client, jwt, setup_permissions):
    """Should return empty authorizedPermissions for an unknown role."""
    rv = client.get(
        '/api/v2/permissions',
        headers=create_header(jwt, ['unknown_role'], 'user')
    )
    assert rv.status_code == HTTPStatus.OK
    assert rv.json['authorizedPermissions'] == []
    assert 'message' in rv.json     

def test_permissions_endpoint_with_staff_role(client, jwt, setup_permissions):
    """Should return newly added permission in the authorizedPermissions for a staff user."""
    rv = client.get(
        '/api/v2/permissions',
        headers=create_header(jwt, [STAFF_ROLE], 'user')
    )
    assert rv.status_code == HTTPStatus.OK
    assert 'STAFF_ONLY_PERMISSION' in rv.json['authorizedPermissions']

def test_permissions_endpoint_with_public_user_role(client, jwt, setup_permissions):
    """Should not return newly added permission in the authorizedPermissions for a public user."""
    rv = client.get(
        '/api/v2/permissions',
        headers=create_header(jwt, [PUBLIC_USER], 'user')
    )
    assert rv.status_code == HTTPStatus.OK
    assert 'STAFF_ONLY_PERMISSION' not in rv.json['authorizedPermissions']    
