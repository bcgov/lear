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

"""Tests to assure the configuration end-point.

Test-Suite to ensure that admin/configuration endpoints are working as expected.
"""
import pytest
from http import HTTPStatus

from legal_api.services.authz import BASIC_USER, STAFF_ROLE
from tests.unit.services.utils import create_header


def test_get_configurations(app, session, client, jwt):
    """Assert that get results are returned."""

    # test
    rv = client.get(f'/api/v2/admin/configurations',
                    headers=create_header(jwt, [STAFF_ROLE], 'user'))

    # check
    assert rv.status_code == HTTPStatus.OK
    assert 'configurations' in rv.json
    results = rv.json['configurations']
    assert len(results) == 5

    names = {'NUM_DISSOLUTIONS_ALLOWED',
             'MAX_DISSOLUTIONS_ALLOWED',
             'DISSOLUTIONS_STAGE_1_SCHEDULE',
             'DISSOLUTIONS_STAGE_2_SCHEDULE',
             'DISSOLUTIONS_STAGE_3_SCHEDULE'
             }
    for res in results:
        assert res['name'] in names


def test_get_configurations_with_invalid_user(app, session, client, jwt):
    """Assert that is unauthorized."""

    # test
    rv = client.get(f'/api/v2/admin/configurations',
                    headers=create_header(jwt, [BASIC_USER], 'user'))

    # check
    assert rv.status_code == HTTPStatus.UNAUTHORIZED


def test_get_configurations_with_single_filter_name(app, session, client, jwt):
    """Assert that get results with a single filter name are returned."""
    filter_name = 'NUM_DISSOLUTIONS_ALLOWED'

    # test
    rv = client.get(f'/api/v2/admin/configurations?names={filter_name}',
                    headers=create_header(jwt, [STAFF_ROLE], 'user'))

    # check
    assert rv.status_code == HTTPStatus.OK
    assert 'configurations' in rv.json
    results = rv.json['configurations']
    assert len(results) == 1
    for res in results:
        assert res['name'] == filter_name


def test_get_configurations_with_multiple_filter_names(app, session, client, jwt):
    """Assert that get results with multiple filter names are returned."""
    filter_names = 'MAX_DISSOLUTIONS_ALLOWED, NUM_DISSOLUTIONS_ALLOWED'
    expected_names = [name.strip().upper() for name in filter_names.split(',') if name.strip()]

    # test
    rv = client.get(f'/api/v2/admin/configurations?names={filter_names}',
                    headers=create_header(jwt, [STAFF_ROLE], 'user'))

    # check
    assert rv.status_code == HTTPStatus.OK
    assert 'configurations' in rv.json
    results = rv.json['configurations']
    assert len(results) == len(expected_names)
    for res in results:
        assert res['name'] in expected_names


def test_get_configurations_with_empty_filter_names(app, session, client, jwt):
    """Assert that a bad request is returned when configuration names are invalid."""
    empty_names = ' '

    # Test
    rv = client.get(f'/api/v2/admin/configurations?names={empty_names}',
                    headers=create_header(jwt, [STAFF_ROLE], 'user'))

    # Check
    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json['message'] == 'Configuration names are invalid'


def test_get_configurations_with_filter_names_no_matching_configurations(app, session, client, jwt):
    """Assert that not found is returned when configuration names have no matches."""
    filter_names = 'NON_EXISTENT_CONFIGURATION_NAME1, NON_EXISTENT_CONFIGURATION_NAME2'

    # Test
    rv = client.get(f'/api/v2/admin/configurations?names={filter_names}',
                    headers=create_header(jwt, [STAFF_ROLE], 'user'))

    # Check
    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json['message'] == 'Configurations not found'


def test_put_configurations_with_valid_data(app, session, client, jwt):
    """Assert that update values successfully."""

    input_data = {
        'configurations': [
            {
                'name': 'NUM_DISSOLUTIONS_ALLOWED',
                'value': '400'
            },
            {
                'name': 'MAX_DISSOLUTIONS_ALLOWED',
                'value': '2500'
            },
            {
                'name': 'dissolutions_stage_1_schedule', # should work with downcase name
                'value': '0 0 2 * *'
            },
            {
                'name': 'DISSOLUTIONS_STAGE_2_SCHEDULE',
                'value': '0 0 2 * *'
            },
            {
                'name': 'DISSOLUTIONS_STAGE_3_SCHEDULE',
                'value': '0 0 2 * *'
            }
        ]
    }
    
    # test
    rv = client.put(f'/api/v2/admin/configurations', json=input_data,
                    headers=create_header(jwt, [STAFF_ROLE], 'user'))
        
    assert rv.status_code == HTTPStatus.OK


@pytest.mark.parametrize('test_name,input_data,message,status_code', [
    ('num_dissolution_with_over_max', {'configurations': [{'name': 'NUM_DISSOLUTIONS_ALLOWED','value': '4000'}]},
     'NUM_DISSOLUTIONS_ALLOWED is greater than MAX_DISSOLUTIONS_ALLOWED.', HTTPStatus.BAD_REQUEST),
    ('num_dissolution_with_non_str_value', {'configurations': [{'name': 'NUM_DISSOLUTIONS_ALLOWED','value': 100}]},
     'Value type must be string.', HTTPStatus.BAD_REQUEST),
    ('num_dissolution_with_negative_int', {'configurations': [{'name': 'NUM_DISSOLUTIONS_ALLOWED','value': '-200'}]},
     'Value for key NUM_DISSOLUTIONS_ALLOWED must be a positive integer', HTTPStatus.BAD_REQUEST),
    ('max_dissolution_less_than_num', {'configurations': [{'name': 'MAX_DISSOLUTIONS_ALLOWED','value': '1'}]},
     'NUM_DISSOLUTIONS_ALLOWED is greater than MAX_DISSOLUTIONS_ALLOWED.', HTTPStatus.BAD_REQUEST),
    ('invalid_key', {'configurations': [{'name': 'INVALID_KEY','value': '1'}]},
     'Invalid name error.', HTTPStatus.BAD_REQUEST),
    ('duplicated_key',{'configurations': [{'name': 'NUM_DISSOLUTIONS_ALLOWED','value': '1'},
                                          {'name': 'NUM_DISSOLUTIONS_ALLOWED','value': '10'}]},
     'Duplicate names error.', HTTPStatus.BAD_REQUEST),
    ('invalid_dissolution_schedule_1', {'configurations': [{'name': 'DISSOLUTIONS_STAGE_1_SCHEDULE','value': '1'}]},
     'Value for key DISSOLUTIONS_STAGE_1_SCHEDULE must be a cron string', HTTPStatus.BAD_REQUEST),
    ('invalid_dissolution_schedule_2', {'configurations': [{'name': 'DISSOLUTIONS_STAGE_2_SCHEDULE','value': '1'}]},
     'Value for key DISSOLUTIONS_STAGE_2_SCHEDULE must be a cron string', HTTPStatus.BAD_REQUEST),
    ('invalid_dissolution_schedule_3', {'configurations': [{'name': 'DISSOLUTIONS_STAGE_3_SCHEDULE','value': '1'}]},
     'Value for key DISSOLUTIONS_STAGE_3_SCHEDULE must be a cron string', HTTPStatus.BAD_REQUEST),
    ('blank_request_body', None, 'Request body cannot be blank', HTTPStatus.BAD_REQUEST),
    ('request_body_without_configuration_list', {'configurations': []}, 'Configurations list cannot be empty', HTTPStatus.BAD_REQUEST),
])
def test_put_configurations_with_invalid_data(app, session, client, jwt, test_name, input_data, message, status_code):
    """Assert that failure update."""
    
    # test
    rv = client.put(f'/api/v2/admin/configurations', json=input_data,
                    headers=create_header(jwt, [STAFF_ROLE], 'user'))
        
    assert rv.status_code == status_code
    assert 'message' in rv.json
    assert rv.json['message'] == message
