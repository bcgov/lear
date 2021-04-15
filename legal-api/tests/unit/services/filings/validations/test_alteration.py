# Copyright © 2021 Province of British Columbia
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
"""Test Correction validations."""
import copy
from http import HTTPStatus
from unittest.mock import patch

import pytest
from registry_schemas.example_data import ALTERATION_FILING_TEMPLATE

from legal_api.services import NameXService
from legal_api.services.filings import validate
from tests.unit.models import factory_business


ALTERATION_FILING = copy.deepcopy(ALTERATION_FILING_TEMPLATE)

TEST_DATA = [
    (False, '', 'BEN', '', True, 0),
    (True, 'legal_name-BC1234567_Changed', 'BEN', 'BEC', True, 0),
    (True, 'legal_name-BC1234567_Changed', 'BC', 'CCR', False, 1),
    (True, 'legal_name-BC1234568', 'CP', 'XCLP', False, 2)
]

class MockResponse:
            def __init__(self, json_data, status_code):
                self.json_data = json_data
                self.status_code = status_code

            def json(self):
                return self.json_data


@ pytest.mark.parametrize('use_nr, new_name, legal_type, nr_type, should_pass, num_errors', TEST_DATA)
def test_alteration(session, use_nr, new_name, legal_type, nr_type, should_pass, num_errors):
    """Test that a valid Alteration without NR correction passes validation."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier)

    f = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    f['filing']['header']['identifier'] = identifier
    f['filing']['alteration']['business']['legalType'] = legal_type

    if use_nr:
        f['filing']['business']['identifier'] = identifier
        f['filing']['business']['legalName'] = 'legal_name-BC1234567'

        f['filing']['alteration']['nameRequest']['nrNumber'] = identifier
        f['filing']['alteration']['nameRequest']['legalName'] = new_name
        f['filing']['alteration']['nameRequest']['legalType'] = legal_type

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
            err = validate(business, f)
    else:
        del f['filing']['alteration']['nameRequest']
        err = validate(business, f)

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
