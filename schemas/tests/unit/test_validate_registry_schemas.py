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
from jsonschema import Draft7Validator, SchemaError

from registry_schemas import get_schema, get_schema_store

from .schema_data import TEST_SCHEMAS_DATA


@pytest.mark.parametrize('schema_filename', TEST_SCHEMAS_DATA)
def test_is_business_schema_valid(schema_filename):
    """Assert that the Schema is a valid Draft7 JSONSchema."""
    schema = get_schema(schema_filename)
    try:
        Draft7Validator.check_schema(schema)
        assert True
    except SchemaError as error:
        print(error)
        assert False


def test_get_schema_store():
    """Assert the schema store is setup correctly."""
    schema_store = get_schema_store()

    assert len(schema_store) == len(TEST_SCHEMAS_DATA)

    # assuming  test_is_business_schema_valid passes, this should pass too
    try:
        for k, schema in schema_store.items():
            print(f'checking schema:{k}')
            Draft7Validator.check_schema(schema)
    except SchemaError as error:
        print(error)
        assert False
    assert True
