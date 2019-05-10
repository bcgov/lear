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
from registry_schemas import validate_schema, validate


def test_validate_business_schema():
    """Assert that the schema is performing as expected."""
    data = {
        'business': {
            'founding_date': '2007-04-08',
            'identifier': 'CP1234567',
            'last_ledger_timestamp': '2019-04-15T20:05:49.068272+00:00',
            'legal_name': 'legal name - CP1234567'
        },
    }

    is_valid, _ = validate_schema(data, 'business.json')

    assert is_valid


def test_validate_business_schema_on_empty_schema():
    """Assert that the schema is performing as expected."""
    data = {
        'business': {
            'founding_date': '2007-04-08',
            'identifier': 'CP1234567'
        },
    }

    is_valid, errors = validate_schema(data, 'business.json')

    for err in errors:
        print(err.message)

    assert not is_valid


def test_validate_schema():
    """Assert that the schema is performing as expected."""
    data = {
        'business': {
            'founding_date': '2007-04-08',
            'identifier': 'CP1234567'
        },
    }

    is_valid = validate(data, 'business.json')

    assert False
