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
"""Test Suite to ensure legal filing schemas are valid.

This suite should have at least 1 test for every filing type allowed.
"""
import copy

from registry_schemas import validate
from registry_schemas.example_data import ADDRESS


def test_valid_address():
    """Assert that the schema is performing as expected."""
    is_valid, errors = validate(ADDRESS, 'address')

    if errors:
        for err in errors:
            print(err.message)
    print(errors)

    assert is_valid


def test_valid_address_null_region():
    """Assert that region is allowed to be null."""
    address = copy.deepcopy(ADDRESS)
    address['addressRegion'] = None

    is_valid, errors = validate(address, 'address')

    if errors:
        for err in errors:
            print(err.message)
    print(errors)

    assert is_valid


def test_invalid_address():
    """Assert that an invalid address fails."""
    address = copy.deepcopy(ADDRESS)
    address['streetAddress'] = 'This is a really long string, over the 50 char maximum'

    is_valid, errors = validate(address, 'address')

    if errors:
        for err in errors:
            print(err.message)
    print(errors)

    assert not is_valid


def test_invalid_address_missing_region():
    """Assert that an invalid address fails - missing required field addressRegion."""
    address = copy.deepcopy(ADDRESS)
    del address['addressRegion']

    is_valid, errors = validate(address, 'address')

    if errors:
        for err in errors:
            print(err.message)
    print(errors)

    assert not is_valid
