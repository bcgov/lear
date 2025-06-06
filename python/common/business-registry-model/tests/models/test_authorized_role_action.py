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

"""Tests to assure the AuthorizedRoleAction Model.

Test-Suite to ensure that the AuthorizedRoleAction Model is working as expected.
"""
from business_model.models import Action, AuthorizedRoleAction, Role

def test_authorized_role_action_save(session):
    """Assert that an AuthorizedRoleAction saves correctly."""
    role = Role(role_name=Role.RoleType.STAFF)
    action = Action(action_name='TEST_ACTION_AUTH')
    role.save()
    action.save()
    auth = AuthorizedRoleAction(role_id=role.id, action_id=action.id)
    auth.save()
    assert auth is not None
    assert auth.role_id == role.id
    assert auth.action_id == action.id

    # Check relationship from Role to Action
    assert action in [a.action for a in role.authorized_actions]
    # Check relationship from Action to Role
    assert role in [r.role for r in action.authorized_roles]

