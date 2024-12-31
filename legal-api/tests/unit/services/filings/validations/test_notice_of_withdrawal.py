# Copyright © 2024 Province of British Columbia
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
"""Test suite to ensure the Notice of Withdrawal filing is validated correctly."""
import copy
from datetime import datetime, timedelta
from http import HTTPStatus

import pytest

from legal_api.models import Filing, RegistrationBootstrap
from legal_api.services.filings import validate
from legal_api.services.filings.validations.notice_of_withdrawal import (
    validate_withdrawn_filing,
    validate as validate_in_notice_of_withdrawal
)
from tests.unit.models import factory_pending_filing, factory_business
from . import lists_are_equal

from registry_schemas.example_data import FILING_HEADER, NOTICE_OF_WITHDRAWAL, DISSOLUTION, INCORPORATION


# setup
FILING_NOT_EXIST_MSG = {'error': 'The filing to be withdrawn cannot be found.'}
FILING_NOT_FED_MSG = {'error': 'Only filings with a future effective date can be withdrawn.'}
FILING_NOT_PAID_MSG = {'error': 'Only paid filings with a future effective date can be withdrawn.'}
MISSING_FILING_DICT_MSG = {'error': 'A valid filing is required.'}


# tests

@pytest.mark.parametrize(
        'test_name, is_filing_exist, withdrawn_filing_status, is_future_effective, has_filing_id, expected_code, expected_msg',[
            ('EXIST_BUSINESS_SUCCESS', True, Filing.Status.PAID, True, True, None, None),
            ('EXIST_BUSINESS_FAIL_NOT_PAID', True, Filing.Status.PENDING, True, True, HTTPStatus.BAD_REQUEST, [FILING_NOT_PAID_MSG]),
            ('EXIST_BUSINESS_FAIL_NOT_FED', True, Filing.Status.PAID, False, True, HTTPStatus.BAD_REQUEST, [FILING_NOT_FED_MSG]),
            ('EXIST_BUSINESS_FAIL_FILING_NOT_EXIST', False, Filing.Status.PAID, True, True, HTTPStatus.NOT_FOUND, [FILING_NOT_EXIST_MSG]),
            ('EXIST_BUSINESS_FAIL_MISS_FILING_ID', True, Filing.Status.PAID, True, False, HTTPStatus.UNPROCESSABLE_ENTITY, ''),
            ('EXIST_BUSINESS_FAIL_NOT_PAID_NOT_FED', True, Filing.Status.PENDING, False, True, HTTPStatus.BAD_REQUEST, [FILING_NOT_FED_MSG, FILING_NOT_PAID_MSG])
        ]
)
def test_validate_notice_of_withdrawal(session, test_name, is_filing_exist, withdrawn_filing_status, is_future_effective, has_filing_id, expected_code, expected_msg):
    """Assert that notice of withdrawal flings can be validated"""
    today = datetime.utcnow().date()
    future_effective_date = today + timedelta(days=5)
    future_effective_date = future_effective_date.isoformat()
    identifier = 'BC1234567'
    business = factory_business(identifier)
    # file a voluntary dissolution with a FED
    if is_filing_exist:
        withdrawn_json = copy.deepcopy(FILING_HEADER)
        withdrawn_json['filing']['header']['name'] = 'dissolution'
        withdrawn_json['filing']['business']['legalType'] = 'BC'
        withdrawn_json['filing']['dissolution'] = copy.deepcopy(DISSOLUTION)
        withdrawn_json['filing']['dissolution']['dissolutionDate'] = future_effective_date
        withdrawn_filing = factory_pending_filing(business, withdrawn_json)
    if is_filing_exist:
        if is_future_effective:
            withdrawn_filing.effective_date = future_effective_date
        if withdrawn_filing_status == Filing.Status.PAID:
            withdrawn_filing.payment_completion_date = datetime.utcnow().isoformat()
        withdrawn_filing.save()
        withdrawn_filing_id = withdrawn_filing.id

    # create a notice of withdrawal filing json
    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['header']['name'] = 'noticeOfWithdrawal'
    filing_json['filing']['business']['legalType'] = 'BC'
    filing_json['filing']['noticeOfWithdrawal'] = copy.deepcopy(NOTICE_OF_WITHDRAWAL)
    if has_filing_id:
        if is_filing_exist:
            filing_json['filing']['noticeOfWithdrawal']['filingId'] = withdrawn_filing_id
    else:
        del filing_json['filing']['noticeOfWithdrawal']['filingId']

    err = validate(business, filing_json)
    if expected_code:
        assert err.code == expected_code
        if has_filing_id: # otherwise, won't pass schema validation, and the error msg will be very long
            assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None
    