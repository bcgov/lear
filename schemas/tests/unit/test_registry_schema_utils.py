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
"""Test Suite to validate the schemas against example data.

Every schema should have at least 1 example to validate against and use as an exemplar.
"""
import os
import uuid

import pytest

from registry_schemas import get_schema_store, validate


def test_validate_business_schema():
    """Assert that the schema is performing as expected."""
    data = {
        'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08',
            'identifier': 'CP1234567',
            'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
            'lastPreBobFilingTimestamp': '2019-04-15T20:05:49.068272+00:00',
            'legalName': 'legal name - CP1234567'
        },
    }

    is_valid, _ = validate(data, 'business', validate_schema=True)

    assert is_valid


def test_validate_business_schema_on_empty_schema():
    """Assert that the schema is performing as expected."""
    data = {
        'business': {
            'foundingDate': '2007-04-08',
            'identifier': 'CP1234567'
        },
    }

    is_valid, errors = validate(data, 'business', validate_schema=True)

    for err in errors:
        print(err.message)

    assert not is_valid


def test_validate_schema():
    """Assert that the schema is performing as expected."""
    data = {
        'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08',
            'identifier': 'CP1234567',
            'legalName': 'legal name CP1234567'
        },
    }

    is_valid, _ = validate(data, 'business', validate_schema=True)

    assert is_valid


def test_invalid_schema():
    """Assert that an invalid schema returns errors and False on validate."""
    # setup
    uid = uuid.uuid4()
    schema_dir = f'/tmp/{uid}'
    schema_file = f'{schema_dir}/bad_schema.json'
    os.makedirs(schema_dir)
    text_file = open(schema_file, 'w')
    text_file.write('this will fail[];fail()')
    text_file.close()

    data = {}

    # test
    is_valid, errors = validate(data, 'bad_schema', validate_schema=True)

    # teardown
    os.remove(schema_file)
    os.removedirs(schema_dir)

    assert not is_valid
    assert errors


def test_invalid_schema_in_get_schema():
    """Asserts that an invalid schema throws an error in get_schema."""
    from json import JSONDecodeError

    # setup
    uid = uuid.uuid4()
    schema_dir = f'/tmp/{uid}'
    schema_file = f'{schema_dir}/bad_schema.json'
    os.makedirs(schema_dir)
    text_file = open(schema_file, 'w')
    text_file.write('this will fail[];fail()')
    text_file.close()

    with pytest.raises(JSONDecodeError):
        get_schema_store(validate_schema=True, schema_search_path=schema_dir)
