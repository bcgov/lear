# Copyright © 2025 Province of British Columbia
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
"""Test Suite for Change of Address validations."""

import copy
import pytest
from http import HTTPStatus

from registry_schemas.example_data import CHANGE_OF_ADDRESS, FILING_HEADER

from legal_api.errors import Error
from legal_api.models import Business
from legal_api.services.filings.validations.validation import validate

from tests.unit.models import factory_business



def test_valid_address_change(session):
    """Test that a valid address change passes validation."""
    business = factory_business('CP1234567')
    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['changeOfAddress'] = copy.deepcopy(CHANGE_OF_ADDRESS)
    error = validate(business, filing_json)
    assert error is None


@pytest.mark.parametrize('test_data', [
    ('streetAddress', 'x' * 50, 'Street address exceeds max length of 50 characters'),
    ('streetAddressAdditional', 'x' * 105, 'Street address additional exceeds max length of 105 characters')
])
def test_validate_max_length_street_addresses(session, test_data):
    """Test that validation fails when street addresses exceed max length."""
    field, value, msg = test_data
    business = factory_business('CP1234567')
    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['changeOfAddress'] = copy.deepcopy(CHANGE_OF_ADDRESS)
    filing_json['filing']['changeOfAddress']['offices']['registeredOffice']['deliveryAddress'][field] = value
    error = validate(business, filing_json)
    assert error is None


@pytest.mark.parametrize('test_data', [
    ('streetAddress', 'x' * 51, 'Street address exceeds max length of 50 characters'),
    ('streetAddressAdditional', 'x' * 106, 'Street address additional exceeds max length of 105 characters')
])
def test_exceed_max_length_street_addresses(session, test_data):
    """Test that validation fails when street addresses exceed max length."""
    field, value, msg = test_data
    business = factory_business('CP1234567')
    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['changeOfAddress'] = copy.deepcopy(CHANGE_OF_ADDRESS)
    filing_json['filing']['changeOfAddress']['offices']['registeredOffice']['deliveryAddress'][field] = value
    error = validate(business, filing_json)
    assert error.code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_invalid_region(session):
    """Test that validation fails when region is not BC."""
    business = factory_business('CP1234567')
    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['changeOfAddress'] = copy.deepcopy(CHANGE_OF_ADDRESS)
    filing_json['filing']['changeOfAddress']['offices']['registeredOffice']['deliveryAddress']['addressRegion'] = 'AB'

    error = validate(business, filing_json)

    assert error is not None
    assert error.code == HTTPStatus.BAD_REQUEST
    assert "Address Region must be 'BC'" in error.msg[0]['error']


def test_invalid_country(session):
    """Test that validation fails when country is not CA."""
    business = factory_business('CP1234567')
    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['changeOfAddress'] = copy.deepcopy(CHANGE_OF_ADDRESS)
    filing_json['filing']['changeOfAddress']['offices']['registeredOffice']['deliveryAddress']['addressCountry'] = 'US'

    error = validate(business, filing_json)

    assert error is not None
    assert error.code == HTTPStatus.BAD_REQUEST
    assert "Address Country must be 'CA'" in error.msg[0]['error']
