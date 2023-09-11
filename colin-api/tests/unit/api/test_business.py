# Copyright © 2019 Province of British Columbia
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

"""Tests to assure the ops end-point.

Test-Suite to ensure that the /ops endpoint is working as expected.
"""
from registry_schemas import validate

from tests import oracle_integration


@oracle_integration
def test_get_business(client):
    """Assert that the business info for regular (not xpro) business is correct to spec."""
    rv = client.get('/api/v1/businesses/CP/CP0001965')

    assert 200 == rv.status_code
    is_valid, errors = validate(rv.json, 'business', validate_schema=True)
    if errors:
        for err in errors:
            print('\nERROR MESSAGE:')
            print(err.message)

    assert is_valid


@oracle_integration
def test_get_business_no_results(client):
    """Assert that the business info for regular (not xpro) business is correct to spec."""
    rv = client.get('/api/v1/businesses/CP/CP0000000')

    assert 404 == rv.status_code
    assert None is not rv.json['message']


@oracle_integration
def test_get_business_new_corp(client):
    """Assert that a new corp number can be retrieved from COLIN."""
    rv_cp = client.post('/api/v1/businesses/CP')
    rv_bc = client.post('/api/v1/businesses/BC')

    assert 200 == rv_cp.status_code
    assert 200 == rv_bc.status_code


@oracle_integration
def test_get_business_all_info(client):
    """Assert that a new corp number can be retrieved from COLIN."""
    rv = client.get('/api/v1/businesses/colin/CP0001965')

    assert 200 == rv.status_code
    is_valid, errors = validate(rv.json, 'business', validate_schema=True)
    if errors:
        for err in errors:
            print('\nERROR MESSAGE:')
            print(err.message)

    assert is_valid
