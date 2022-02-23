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

"""Tests to assure the NaicsStructure Model.

Test-Suite to ensure that the NaicsStructure Model is working as expected.
"""
import json

from legal_api.models import NaicsStructure

def test_naics_find_by_search_term(session):
    """Assert matching naics search results are returned.

    Note: we are able to hard code a search term and verify specific values because the test data will always be
    the same.  This test search term provides a quick way of testing that a lot of paths of the search logic is
    working correctly.  A bit overloaded but a quick way to uncover any issues with the NAICS search.
    """
    results = NaicsStructure.find_by_search_term('roast')
    assert results
    assert len(results) == 9

    # verify elements are filtered correctly
    results_with_more_than_one_element = [result for result in results if len(result.naics_elements) > 0]
    assert len(results_with_more_than_one_element) == 7

    results_with_3_elements = [result for result in results if len(result.naics_elements) == 3]
    assert len(results_with_3_elements) == 2

    # verify naics structures with no naics element matches are returned
    results_with_no_elements = [result for result in results if len(result.naics_elements) == 0]
    assert len(results_with_no_elements) == 2


def test_naics_find_by_search_term_no_results(session):
    """Assert no matching naics search results are returned."""
    results = NaicsStructure.find_by_search_term('roastasdf')
    assert len(results) == 0


def test_naics_find_by_naics_code(session):
    """Assert naics code can be retrieved by code."""

    # setup
    naics_code = '311911'

    # test
    result = NaicsStructure.find_by_code(naics_code)

    # check
    assert result
    assert result.code == naics_code


def test_naics_find_by_naics_code_no_match(session):
    """Assert no result retrieved for non-existent naics code."""

    # setup
    naics_code = '311911a'

    # test
    result = NaicsStructure.find_by_code(naics_code)

    # check
    assert not result


def test_naics_find_by_naics_key(session):
    """Assert naics code can be retrieved by key."""

    # setup
    naics_code = '311911'
    naics_key = 'd2fca3f1-f391-49a7-8b67-00381b569612'

    # test
    result = NaicsStructure.find_by_naics_key(naics_key)

    # check
    assert result
    assert result.naics_key == naics_key
    assert result.code == naics_code


def test_naics_find_by_naics_key_no_match(session):
    """Assert no result retrieved for non-existent naics key."""

    # setup
    naics_key = 'd2fca3f1-f391-49a7-8b67-00381b569aaa'

    # test
    result = NaicsStructure.find_by_naics_key(naics_key)

    # check
    assert not result
