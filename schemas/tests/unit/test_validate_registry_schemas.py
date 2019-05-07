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
"""Test Suite for ensuring the JSON Schemas validate structurally.

Every schema should be listed in the TEST_SCHEMAS_DATA to be validated.
"""
import pytest
from jsonschema import Draft7Validator

from registry_schemas import get_schema


# testdata pattern is ({str: environment}, {expected return value})
TEST_SCHEMAS_DATA = [
    ('business.json'),
]


@pytest.mark.parametrize('schema_filename', TEST_SCHEMAS_DATA)
def test_is_business_schema_valid(schema_filename):
    """Assert that the Schema is a valid Draft7 JSONSchema."""
    schema = get_schema(schema_filename)
    Draft7Validator.check_schema(schema)
