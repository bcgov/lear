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

"""Tests to assure the business-addresses end-point.

Test-Suite to ensure that the /naics?search_term=asjkdfj endpoint is working as expected.
"""
from http import HTTPStatus

from legal_api.services.authz import BASIC_USER
from tests.unit.services.utils import create_header

def test_search_naics_using_search_term_with_results(session, client, jwt):
    """Assert that search results are returned when searching with search term.

    Note: we are able to hard code a search term and verify specific values because the test data will always be
    the same.  This test search term provides a quick way of testing that a lot of paths of the search logic is
    working correctly.  A bit overloaded but a quick way to uncover any issues with the NAICS search.
    """
    # test
    rv = client.get(f'/api/v2/naics?search_term=roast',
                    headers=create_header(jwt, [BASIC_USER], 'user'))

    # check
    assert rv.status_code == HTTPStatus.OK
    assert 'results' in rv.json
    results = rv.json['results']
    assert len(results) == 9

    # verify elements are filtered correctly
    results_with_more_than_one_element = [result for result in results if len(result['naicsElements']) > 0]
    assert len(results_with_more_than_one_element) == 7

    results_with_3_elements = [result for result in results if len(result['naicsElements']) == 3]
    assert len(results_with_3_elements) == 2

    # verify naics structures with no naics element matches are returned
    results_with_no_elements = [result for result in results if len(result['naicsElements']) == 0]
    assert len(results_with_no_elements) == 2


def test_search_naics_using_code_with_result(session, client, jwt):
    """Assert that search result is returned when searching with valid naics code."""

    # test
    rv = client.get(f'/api/v2/naics?search_term=311911',
                    headers=create_header(jwt, [BASIC_USER], 'user'))

    # check
    assert rv.status_code == HTTPStatus.OK
    assert 'results' in rv.json
    results = rv.json['results']
    assert len(results) == 1

    assert len(results[0]["naicsElements"]) == 3


def test_search_naics_using_code_with_no_result(session, client, jwt):
    """Assert that no search result is returned when searching with non-existent naics code."""

    # test
    rv = client.get(f'/api/v2/naics?search_term=999999',
                    headers=create_header(jwt, [BASIC_USER], 'user'))

    # check
    assert rv.status_code == HTTPStatus.OK
    assert 'results' in rv.json
    results = rv.json['results']
    assert len(results) == 0


def test_search_naics_no_results(session, client, jwt):
    """Assert that 200 is returned with no results."""

    # test
    rv = client.get(f'/api/v2/naics?search_term=jaklsjdf',
                    headers=create_header(jwt, [BASIC_USER], 'user'))

    # check
    assert rv.status_code == HTTPStatus.OK
    assert 'results' in rv.json
    results = rv.json['results']
    assert len(results) == 0


def test_search_naics_with_no_search_term_param(session, client, jwt):
    """Assert that hitting naics endpoint with no search_term query param returns 400 and correct error message."""

    # test
    rv = client.get(f'/api/v2/naics',
                    headers=create_header(jwt, [BASIC_USER], 'user'))

    # check
    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert 'message' in rv.json
    assert 'search_term query parameter is required.' in rv.json['message']


def test_search_naics_with_no_value_for_search_term_param(session, client, jwt):
    """Assert that hitting naics endpoint with no value for search_term query param returns 400 and correct error message."""

    # test
    rv = client.get(f'/api/v2/naics?search_term',
                    headers=create_header(jwt, [BASIC_USER], 'user'))

    # check
    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert 'message' in rv.json
    assert 'search_term query parameter is required.' in rv.json['message']


def test_search_naics_with_search_term_param_too_short(session, client, jwt):
    """Assert that hitting naics endpoint with search_term query param with value of less than 3 characters
        returns 400 and correct error message."""

    # test
    rv = client.get(f'/api/v2/naics?search_term=ab',
                    headers=create_header(jwt, [BASIC_USER], 'user'))

    # check
    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert 'message' in rv.json
    assert 'search_term cannot be less than 3 characters.' in rv.json['message']


def test_get_naics_code_by_code(session, client, jwt):
    """Assert that naics code can be retrieved using code."""

    # setup
    naics_code = '311911'

    # test
    rv = client.get(f'/api/v2/naics/{naics_code}',
                    headers=create_header(jwt, [BASIC_USER], 'user'))

    # check
    assert rv.status_code == HTTPStatus.OK
    assert 'code' in rv.json
    assert rv.json['code'] == naics_code
    assert 'classDefinition' in rv.json
    assert 'classTitle' in rv.json
    assert 'year' in rv.json

    assert 'naicsElements' in rv.json
    assert len(rv.json['naicsElements']) == 3


def test_get_naics_code_by_key(session, client, jwt):
    """Assert that naics code can be retrieved using key."""

    # setup
    naics_code = '311911'
    naics_key = 'd2fca3f1-f391-49a7-8b67-00381b569612'

    # test
    rv = client.get(f'/api/v2/naics/{naics_key}',
                    headers=create_header(jwt, [BASIC_USER], 'user'))

    # check
    assert rv.status_code == HTTPStatus.OK
    assert 'code' in rv.json
    assert rv.json['code'] == naics_code
    assert 'naicsKey' in rv.json
    assert rv.json['naicsKey'] == naics_key
    assert 'classDefinition' in rv.json
    assert 'classTitle' in rv.json
    assert 'year' in rv.json

    assert 'naicsElements' in rv.json
    assert len(rv.json['naicsElements']) == 3


def test_get_naics_code_invalid_code_or_key_format(session, client, jwt):
    """Assert that retrieving naics code with invalid code format returns 400."""

    # setup
    naics_code = '311aaa'

    # test
    rv = client.get(f'/api/v2/naics/{naics_code}',
                    headers=create_header(jwt, [BASIC_USER], 'user'))

    # check
    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert 'message' in rv.json
    assert rv.json['message'] == 'Invalid NAICS code(6 digits) or naics key(uuid v4) format.'


def test_get_naics_code_not_found(session, client, jwt):
    """Assert that retrieving naics code returns 404 when not found."""

    # setup
    naics_code = '999999'

    # test
    rv = client.get(f'/api/v2/naics/{naics_code}',
                    headers=create_header(jwt, [BASIC_USER], 'user'))

    # check
    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert 'message' in rv.json
    assert rv.json['message'] == 'NAICS code not found.'
