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

"""Tests to assure the business schemas are operating correctly.

Test-Suite to ensure that the schema, validator and helpers are working correctly.
"""
from legal_api.schemas import validate_schema


def test_validate_schema_fail_empty():
    """Assert that the empty set does not pass validation."""
    data = {}
    valid, errors = validate_schema(data, 'business.json')

    for error in errors:
        print('Error:', error.message)
        for suberror in sorted(error.context, key=lambda e: e.schema_path):
            print('Schema Errors', list(suberror.schema_path), suberror.message, sep=', ')

    assert not valid


def test_validate_schema_pass_business_info_data():
    """Assert that the basic schema setup validates the JSON correctly."""
    data = {
        'business': {
            'last_ledger_timestamp': '2019-04-16T00:00:00+00:00',
            'founding_date': '2019-04-08',
            'identifier': 'CP1234567',
            'legal_name': 'legal name'
        },
    }
    valid, errors = validate_schema(data, 'business.json')

    if errors:
        for error in errors:
            print('listing errors')
            print('Error:', error.message, 'context', error.context)
            for suberror in sorted(error.context, key=lambda e: e.schema_path):
                print('Schema Errors', list(suberror.schema_path), suberror.message, sep=', ')

    assert valid
