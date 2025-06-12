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

"""Tests to assure the AuthorizedRolePermission Model.

Test-Suite to ensure that the AuthorizedRolePermission Model is working as expected.
"""
from legal_api.models import AuthorizedRolePermission, AuthorizedRole, Permission

def test_authorized_role_permission_save(session):
    """Assert that an AuthorizedRolePermission saves correctly."""
    role = AuthorizedRole(role_name='test_staff_role')
    permission = Permission(permission_name='TEST_PERMISSION_AUTH')
    role.save()
    permission.save()
    auth = AuthorizedRolePermission(role_id=role.id, permission_id=permission.id)
    auth.save()
    assert auth is not None
    assert auth.role_id == role.id
    assert auth.permission_id == permission.id

    # Check relationship from AuthorizedRole to Permission
    assert permission in [a.permission for a in role.permissions]
    # Check relationship from Permission to AuthorizedRole
    assert role in [r.role for r in permission.authorized_roles]

def test_get_authorized_permissions_by_role_name_empty(session):
    """Assert that an empty list is returned when the role has no authorized permissions."""
    role = AuthorizedRole(role_name='test_unauthorized_user')
    session.add(role)
    session.commit()

    authorized_role_permissions = AuthorizedRolePermission.get_authorized_permissions_by_role_name('test_unauthorized_user')
    assert authorized_role_permissions == []    

def test_get_authorized_permissions_by_role_name(session):
    """Assert that a list of authorized permissions are returned for a given role name."""
    permission = Permission(permission_name='TEST_NEW_PERMISSION')
    session.add(permission)
    session.commit()

    role = AuthorizedRole(role_name='test_staff_role')
    session.add(role)
    session.commit()

    role_permission = AuthorizedRolePermission(role_id=role.id, permission_id=permission.id)
    session.add(role_permission)
    session.commit()

    authorized_role_permissions = AuthorizedRolePermission.get_authorized_permissions_by_role_name('test_staff_role')
    assert authorized_role_permissions == ['TEST_NEW_PERMISSION']    
