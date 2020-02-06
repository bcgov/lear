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
"""Test Suite to ensure annual report schemas are valid."""

import copy

from registry_schemas import validate
from registry_schemas.example_data import INCORPORATION


def test_incorporation_schema():
    """Assert that the JSONSchema validator is working."""
    is_valid, errors = validate(INCORPORATION, 'incorporationApplication')

    if errors:
        for err in errors:
            print(err.message)
    print(errors)

    assert is_valid


def test_validate_no_name_request():
    """Assert not valid if name request node is not present."""
    inc_json = copy.deepcopy(INCORPORATION)
    del inc_json['nameRequest']

    is_valid, errors = validate(inc_json, 'incorporationApplication')

    if errors:
        for err in errors:
            print(err.message)
    print(errors)

    assert not is_valid


def test_validate_name_request_type():
    """Assert valid if name request legalType node is present."""
    inc_json = copy.deepcopy(INCORPORATION)
    inc_json['nameRequest']['legalType'] = 'BC'

    is_valid, errors = validate(inc_json, 'incorporationApplication')

    if errors:
        for err in errors:
            print(err.message)
    print(errors)

    assert is_valid


def test_validate_invalid_name_request_type():
    """Assert not valid if legalType is not an accepted type."""
    inc_json = copy.deepcopy(INCORPORATION)
    inc_json['nameRequest']['legalType'] = 'ZZ'

    is_valid, errors = validate(inc_json, 'incorporationApplication')

    if errors:
        for err in errors:
            print(err.message)
    print(errors)

    assert not is_valid


def test_validate_no_offices():
    """Assert not valid if the required offices are not present."""
    inc_json = copy.deepcopy(INCORPORATION)
    del inc_json['offices']['registeredOffice']

    is_valid, errors = validate(inc_json, 'incorporationApplication')

    if errors:
        for err in errors:
            print(err.message)
    print(errors)

    assert not is_valid


def test_validate_no_contact():
    """Assert not valid if the required contact info is not present."""
    inc_json = copy.deepcopy(INCORPORATION)
    del inc_json['contactPoint']

    is_valid, errors = validate(inc_json, 'incorporationApplication')

    if errors:
        for err in errors:
            print(err.message)
    print(errors)

    assert not is_valid
