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
"""Test suite to ensure Special Resolution is validated correctly."""
import copy
from http import HTTPStatus

import pytest
from registry_schemas.example_data import FILING_HEADER, SPECIAL_RESOLUTION

from legal_api.models import Business
from legal_api.services.filings.validations.special_resolution import validate


# from tests.unit.models import factory_business, factory_business_mailing_address, factory_filing
@pytest.mark.parametrize(
    'test_name, resolution, identifier, expected_code, expected_msg',
    [
        ('SUCCESS', 'some resolution', 'CP1234567', None, None),
        ('MISSING - resolution', None, 'CP1234567', HTTPStatus.BAD_REQUEST, 'Resolution must be provided.'),
    ]
)
def test_validate(session, test_name, resolution, identifier, expected_code, expected_msg):
    """Assert that a SR can be validated."""
    # setup
    business = Business(identifier=identifier)

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['specialResolution'] = copy.deepcopy(SPECIAL_RESOLUTION)
    if resolution:
        filing['filing']['specialResolution']['resolution'] = resolution
    else:
        del filing['filing']['specialResolution']['resolution']

    # perform test
    err = validate(business, filing)

    # validate outcomes
    if expected_code or expected_msg:
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err
