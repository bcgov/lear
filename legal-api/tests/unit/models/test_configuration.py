# Copyright © 2024 Province of British Columbia
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

"""Tests to assure the Configuration Model.

Test-Suite to ensure that the Configuration Model is working as expected.
"""
import pytest

from legal_api.models import Configuration

def test_valid_configuration_save(session):
    """Assert that a valid configuration can be saved."""
    configuration = Configuration(
        name='NEW_TEST_CONFIGURATION',
        val='100',
    )
    configuration.save()
    assert configuration.id


def test_find_configuration_by_id(session):
    """Assert that the method returns correct value."""
    configuration = Configuration(
        name='NEW_TEST_CONFIGURATION',
        val='100',
    )
    configuration.save()
    res = Configuration.find_by_id(configuration.id)
    assert res

def test_find_existing_configuration_by_id(session):
    """Assert that the method returns correct value."""
    num_dissolutions_allowed_id = 1
    res = Configuration.find_by_id(num_dissolutions_allowed_id)
    assert res


def test_find_configuration_by_name(session):
    """Assert that the method returns correct value."""
    configuration = Configuration(
        name='NEW_TEST_CONFIGURATION',
        val='100',
    )
    configuration.save()
    res = Configuration.find_by_name(configuration.name)
    assert res


def test_find_existing_configuration_by_name(session):
    """Assert that the method returns correct value."""
    num_dissolutions_allowed_name = 'NUM_DISSOLUTIONS_ALLOWED'
    res = Configuration.find_by_name(num_dissolutions_allowed_name)
    assert res

@pytest.mark.parametrize('config_name,test_val,succeeded', [
    ('NUM_DISSOLUTIONS_ALLOWED', 'ten', False),
    ('NUM_DISSOLUTIONS_ALLOWED', '10', True),
    ('MAX_DISSOLUTIONS_ALLOWED', 'one thousand', False),
    ('MAX_DISSOLUTIONS_ALLOWED', '1000', True),
    ('NEW_DISSOLUTIONS_SCHEDULE', '100', False),
    ('NEW_DISSOLUTIONS_SCHEDULE', '0 2 * * *', True),
    ('DISSOLUTIONS_ON_HOLD', '100', False),
    ('DISSOLUTIONS_ON_HOLD', 'True', True),
])
def test_configuration_value_validation(session, config_name, test_val, succeeded):
    configuration = Configuration.find_by_name(config_name)
    configuration.val = test_val
    
    try:
        configuration.save()
        assert configuration.val == test_val
    except ValueError:
        assert not succeeded
