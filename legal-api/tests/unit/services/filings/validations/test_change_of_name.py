# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test suite to ensure Change of Name is validated correctly."""
import copy
from http import HTTPStatus
from unittest.mock import patch

import pytest
from registry_schemas.example_data import CHANGE_OF_NAME, FILING_HEADER

from legal_api.services import NameXService
from legal_api.models import Business
from legal_api.services.filings.validations.change_of_name import validate
from tests.unit.models import factory_business

class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data


@pytest.mark.parametrize(
    'test_name, resolution, identifier, expected_code',
    [
        ('SUCCESS', 'some name', 'CP1234567', None),
        ('MISSING - legalName', None, 'CP1234567', HTTPStatus.BAD_REQUEST),
    ]
)
def test_validate(session, test_name, resolution, identifier, expected_code):
    """Assert that a CoN can be validated."""
    # setup
    business = Business(identifier=identifier)

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['changeOfName'] = copy.deepcopy(CHANGE_OF_NAME)
    if resolution:
        filing['filing']['changeOfName']['legalName'] = resolution
    else:
        del filing['filing']['changeOfName']['legalName']

    # perform test
    err = validate(business, filing)

    # validate outcomes
    if expected_code:
        assert expected_code == err.code
    else:
        assert not err

TEST_DATA = [
    (True, 'legal_name-CP1234568', 'CP', 'XCLP', True, 1),
    (True, 'wrong_name-CP1234568', 'CP', 'XCLP', False, 1),
    (False, 'legal_name-CP1234568', 'CP', 'XCLP', True, 1)
]
@pytest.mark.parametrize('use_nr, new_name, legal_type, nr_type, should_pass, num_errors', TEST_DATA)
def test_validate_nr(session, use_nr, new_name, legal_type, nr_type, should_pass, num_errors):
    """Assert that a CoN can be validated."""
    """Test that a valid Alteration without NR correction passes validation."""
    # setup
    identifier = 'CP1234567'
    business = factory_business(identifier)

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['changeOfName'] = copy.deepcopy(CHANGE_OF_NAME)

    if use_nr:
        del filing['filing']['changeOfName']['legalName']

        nr_json = {
            "state": "APPROVED",
            "expirationDate": "",
            "requestTypeCd": nr_type,
            "names": [{
                "name": new_name,
                "state": "APPROVED",
                "consumptionDate": ""
            }]
        }

        nr_response = MockResponse(nr_json, 200)

        with patch.object(NameXService, 'query_nr_number', return_value=nr_response):
            err = validate(business, filing)
    else:
        del filing['filing']['changeOfName']['nameRequest']
        err = validate(business, filing)

    if err:
        print(err.msg)

    if should_pass:
        # check that validation passed
        assert None is err
    else:
        # check that validation failed
        assert err
        assert HTTPStatus.BAD_REQUEST == err.code
        assert len(err.msg) == num_errors