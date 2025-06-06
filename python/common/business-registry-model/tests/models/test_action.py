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

"""Tests to assure the Action Model.

Test-Suite to ensure that the Action Model is working as expected.
"""
from business_model.models import Action

def test_action_save(session):
    """Assert that an Action saves correctly."""
    action = Action(action_name='TEST_ACTION_SAVE')
    action.save()
    assert action.id
    assert action.action_name == 'TEST_ACTION_SAVE'
