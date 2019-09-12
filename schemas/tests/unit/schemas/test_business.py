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
"""Test Suite for the business schema."""
import copy

from registry_schemas import get_schema
from registry_schemas.example_data import BUSINESS
from registry_schemas.utils import validate


def test_sanity():
    """Assert that the business schema can be retrieved.

    If this fails, nothing else will work.
    """
    schema = get_schema('business.json')
    print(schema)
    assert schema


def test_get_legal_type():
    """Assert that the schema can be retrieved and that the enum has the right number of types."""
    current_types = 45
    schema = get_schema('business.json')
    legal_types = schema['properties']['business']['properties']['legalType']['enum']
    assert legal_types
    assert len(legal_types) == current_types


def test_fail_legal_types():
    """Assert that an invalid legalType fails to validate."""
    business = copy.deepcopy(BUSINESS)
    business['legalType'] = 'Total Failure Mode'

    valid, err_iter = validate(business, 'business')

    assert not valid


def test_legal_types():
    """Assert that all legalTypes validate in the schema."""
    schema = get_schema('business.json')
    legal_types = schema['properties']['business']['properties']['legalType']['enum']

    business = copy.deepcopy(BUSINESS)

    for t in legal_types:
        business['legalType'] = t
        print(t)
        assert validate(business, 'business')
