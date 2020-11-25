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

import pytest
from registry_schemas.example_data import CHANGE_OF_NAME, FILING_HEADER

from legal_api.models import Business
from legal_api.services.filings.validations.change_of_name import validate


# from tests.unit.models import factory_business, factory_business_mailing_address, factory_filing
@pytest.mark.parametrize(
    'test_name, resolution, identifier, expected_code, expected_msg',
    [
        ('SUCCESS', 'some name', 'CP1234567', None, None),
        ('MISSING - legalName', None, 'CP1234567', HTTPStatus.BAD_REQUEST, 'Legal Name must be provided.'),
    ]
)
def test_validate(session, test_name, resolution, identifier, expected_code, expected_msg):
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
    if expected_code or expected_msg:
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err
