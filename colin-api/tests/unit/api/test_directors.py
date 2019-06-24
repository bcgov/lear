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

"""Tests to assure the change of directors filing end-point."""

from registry_schemas import validate

from tests import oracle_integration


@oracle_integration
def test_get_cod(client):
    """Assert that the business info for regular (not xpro) business is correct to spec."""
    rv = client.get('/api/v1/businesses/CP0001965/filings/changeOfDirectors')
    assert 404 == rv.status_code

    # todo: once event_id is fixed for directors uncomment below
    # assert 200 == rv.status_code
    # is_valid, errors = validate(rv.json, 'filing', validate_schema=True)
    # if errors:
    #     for err in errors:
    #         print('\nERROR MESSAGE:')
    #         print(err.message)
    #
    # assert is_valid


@oracle_integration
def test_get_by_id(client):
    """Assert that the business info for regular (not xpro) business is correct to spec."""
    rv = client.get('/api/v1/businesses/CP0001965/filings/changeOfDirectors?eventId=111359103')
    assert 404 == rv.status_code

    # todo: once event_id is fixed for directors uncomment below
    # assert 200 == rv.status_code
    # is_valid, errors = validate(rv.json, 'filing', validate_schema=True)
    # if errors:
    #     for err in errors:
    #         print('\nERROR MESSAGE:')
    #         print(err.message)
    #
    # assert is_valid


@oracle_integration
def test_get_current(client):
    """Assert that the business info for regular (not xpro) business is correct to spec."""
    rv = client.get('/api/v1/businesses/CP0001965/directors')

    assert 200 == rv.status_code
    is_valid, errors = validate(rv.json, 'directors', validate_schema=True)
    if errors:
        for err in errors:
            print('\nERROR MESSAGE:')
            print(err.message)

    assert is_valid


@oracle_integration
def test_get_cod_no_results(client):
    """Assert that the business info for regular (not xpro) business is correct to spec."""
    rv = client.get('/api/v1/businesses/CP0000000/filings/changeOfDirectors')

    assert 404 == rv.status_code
