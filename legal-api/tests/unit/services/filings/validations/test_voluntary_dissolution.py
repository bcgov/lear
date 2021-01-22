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
"""Test suite to ensure Voluntary Dissolution is validated correctly."""
import copy
from http import HTTPStatus

import pytest
from registry_schemas.example_data import FILING_HEADER, VOLUNTARY_DISSOLUTION

from legal_api.models import Business
from legal_api.services.filings.validations.voluntary_dissolution import validate


@pytest.mark.parametrize(
    'test_name, dissolution_date, has_liabilities, identifier, expected_code, expected_msg',
    [
        ('SUCCESS', '2018-04-08', True, 'CP1234567', None, None),
        ('MISSING - dissolution date', None, True, 'CP1234567', HTTPStatus.BAD_REQUEST,
            'Dissolution date must be provided.'),
        ('MISSING - has liabilities', '2018-04-08', None, 'CP1234567', HTTPStatus.BAD_REQUEST,
            'Liabilities flag must be provided.'),
    ]
)
def test_validate(session, test_name, dissolution_date, has_liabilities, identifier,
                  expected_code, expected_msg):  # pylint: disable=too-many-arguments
    """Assert that a VD can be validated."""
    # setup
    business = Business(identifier=identifier)

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['voluntaryDissolution'] = copy.deepcopy(VOLUNTARY_DISSOLUTION)
    if dissolution_date:
        filing['filing']['voluntaryDissolution']['dissolutionDate'] = dissolution_date
    else:
        del filing['filing']['voluntaryDissolution']['dissolutionDate']
    if has_liabilities:
        filing['filing']['voluntaryDissolution']['hasLiabilities'] = has_liabilities
    else:
        del filing['filing']['voluntaryDissolution']['hasLiabilities']

    # perform test
    err = validate(business, filing)

    # validate outcomes
    if expected_code or expected_msg:
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err
