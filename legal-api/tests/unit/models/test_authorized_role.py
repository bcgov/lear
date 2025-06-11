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

"""Tests to assure the AuthorizedRole Model.

Test-Suite to ensure that the AuthorizedRole Model is working as expected.
"""
from legal_api.models import AuthorizedRolePermission, AuthorizedRole, Permission

def test_role_save(session):
    """Assert that a Role saves correctly."""
    role = AuthorizedRole(role_name='test_new_role')
    role.save()
    assert role.id
    assert role.role_name == 'test_new_role'

def test_get_authorized_permissions_by_role_name_empty(session):
    """Assert that an empty list is returned when the role has no authorized permissions."""
    role = AuthorizedRole(role_name='test_unauthorized_user')
    session.add(role)
    session.commit()

    authorized_role_permissions = AuthorizedRole.get_authorized_permissions_by_role_name('test_unauthorized_user')
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

    authorized_role_permissions = AuthorizedRole.get_authorized_permissions_by_role_name('test_staff_role')
    assert authorized_role_permissions == ['TEST_NEW_PERMISSION']

