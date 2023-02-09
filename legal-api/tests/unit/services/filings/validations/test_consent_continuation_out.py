# Copyright © 2023 Province of British Columbia
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
"""Test suite to ensure Consent Continuation Out is validated correctly."""
import copy
import datedelta
from http import HTTPStatus

import pytest
from registry_schemas.example_data import FILING_HEADER, CONSENT_CONTINUATION_OUT

from legal_api.models import Business
from legal_api.services.filings.validations.validation import validate
from legal_api.utils.datetime import datetime

legal_name = 'Test name request'


class MockResponse:
    """Mock http response."""

    def __init__(self, json_data):
        """Initialize mock http response."""
        self.json_data = json_data

    def json(self):
        """Return mock json data."""
        return self.json_data


@pytest.mark.parametrize(
    'test_name, expected_code',
    [
        ('FAIL_NOT_ACTIVE', HTTPStatus.BAD_REQUEST),
        ('FAIL_NOT_IN_GOOD_STANDING', HTTPStatus.BAD_REQUEST),
        ('SUCCESS', None)
    ]
)
def test_consent_continuation_out_active_and_good_standing(session, test_name, expected_code):
    """Assert valid court order."""
    business = Business(
        identifier='BC1234567',
        legal_type='BC',
        state=Business.State.ACTIVE,
        founding_date=datetime.utcnow()
    )
    if test_name == 'FAIL_NOT_ACTIVE':
        business.state = Business.State.HISTORICAL
    elif test_name == 'FAIL_NOT_IN_GOOD_STANDING':
        business.founding_date = datetime.utcnow() - datedelta.datedelta(years=2)

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['consentContinuationOut'] = copy.deepcopy(CONSENT_CONTINUATION_OUT)
    filing['filing']['header']['name'] = 'consentContinuationOut'

    err = validate(business, filing)

    # validate outcomes
    if test_name != 'SUCCESS':
        assert expected_code == err.code
        assert 'Business should be Active and in Good Standing to file Consent Continuation Out.' == err.msg[0]['error']
    else:
        assert not err


@pytest.mark.parametrize(
    'test_status, file_number, expected_code',
    [
        ('FAIL', None, HTTPStatus.UNPROCESSABLE_ENTITY),
        ('SUCCESS', '12345678901234567890', None)
    ]
)
def test_consent_continuation_out_court_order(session, test_status, file_number, expected_code):
    """Assert valid court order."""
    business = Business(
        identifier='BC1234567',
        legal_type='BC',
        state=Business.State.ACTIVE,
        founding_date=datetime.utcnow()
    )
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['consentContinuationOut'] = copy.deepcopy(CONSENT_CONTINUATION_OUT)
    filing['filing']['header']['name'] = 'consentContinuationOut'

    if file_number:
        court_order = {}
        court_order['fileNumber'] = file_number
        filing['filing']['consentContinuationOut']['courtOrder'] = court_order
    else:
        del filing['filing']['consentContinuationOut']['courtOrder']['fileNumber']

    err = validate(business, filing)

    # validate outcomes
    if test_status == 'FAIL':
        assert expected_code == err.code
    else:
        assert not err
