# Copyright © 2026 Province of British Columbia
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
"""Test Registrars Order validations."""
import copy
from http import HTTPStatus

import pytest
from registry_schemas.example_data import REGISTRARS_ORDER_FILING_TEMPLATE

from legal_api.services.filings.validations.registrars_order import validate

from tests.unit.models import factory_business


@pytest.mark.parametrize(
    'test_status, expected_code, expected_msg',
    [
        ('FAIL_INVALID_EFFECT_OF_ORDER', HTTPStatus.BAD_REQUEST, [
            {'error': 'Invalid effectOfOrder.', 'path': '/filing/registrarsOrder/effectOfOrder'}]),
        ('FAIL_MISSING_FILE_NUMBER', HTTPStatus.BAD_REQUEST, [
            {'error': 'Court Order Number is required when this filing is pursuant to a Plan of Arrangement.',
             'path': '/filing/registrarsOrder/fileNumber'}]),
        ('SUCCESS', None, None)
    ]
)
def test_registrars_order(session, test_status, expected_code, expected_msg):
    """Assert valid registrars order."""
    business = factory_business('BC1234567')
    filing = copy.deepcopy(REGISTRARS_ORDER_FILING_TEMPLATE)
    if test_status == 'FAIL_INVALID_EFFECT_OF_ORDER':
        filing['filing']['registrarsOrder']['effectOfOrder'] = 'invalid'
    elif test_status == 'FAIL_MISSING_FILE_NUMBER':
        filing['filing']['registrarsOrder']['fileNumber'] = None
    err = validate(business, filing)

    if expected_code:
        assert err.code == expected_code
        assert err.msg[0]['error'] == expected_msg[0]['error']
        assert err.msg[0]['path'] == expected_msg[0]['path']
    else:
        assert err is None
