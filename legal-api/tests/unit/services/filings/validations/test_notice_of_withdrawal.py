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
            ('SUCCESS', True, Filing.Status.PAID, True, True, None, None),
            ('FAIL_NOT_PAID', True, Filing.Status.PENDING, True, True, HTTPStatus.BAD_REQUEST, [FILING_NOT_PAID_MSG]),
            ('FAIL_NOT_FED', True, Filing.Status.PAID, False, True, HTTPStatus.BAD_REQUEST, [FILING_NOT_FED_MSG]),
            ('FAIL_FILING_NOT_EXIST', False, Filing.Status.PAID, True, True, HTTPStatus.BAD_REQUEST, [FILING_NOT_EXIST_MSG]),
            ('FAIL_MISS_FILING_ID', True, Filing.Status.PAID, True, False, HTTPStatus.UNPROCESSABLE_ENTITY, ''),
            ('FAIL_NOT_PAID_NOT_FED', True, Filing.Status.PENDING, False, True, HTTPStatus.BAD_REQUEST, [FILING_NOT_FED_MSG, FILING_NOT_PAID_MSG])
        ]
)
def test_validate_notice_of_withdrawal_exist_business(session, test_name, is_filing_exist, withdrawn_filing_status, is_future_effective, has_filing_id, expected_code, expected_msg):
    """Assert that notice of withdrawal flings can be validated"""
    identifier = 'BC1234567'
    business = factory_business(identifier)
    # file a voluntary dissolution with a FED
    if is_filing_exist:
        dissolution_filing_json = copy.deepcopy(FILING_HEADER)
        dissolution_filing_json['filing']['header']['name'] = 'dissolution'
        dissolution_filing_json['filing']['business']['legalType'] = 'BC'
        dissolution_filing_json['filing']['dissolution'] = copy.deepcopy(DISSOLUTION)
        today = datetime.utcnow().date()
        future_effective_date = today + timedelta(days=5)
        future_effective_date = future_effective_date.isoformat()
        dissolution_filing_json['filing']['dissolution']['dissolutionDate'] = future_effective_date
        dissolution_filing = factory_pending_filing(business, dissolution_filing_json)

        if is_future_effective:
            dissolution_filing.effective_date = future_effective_date
        if withdrawn_filing_status == Filing.Status.PAID:
            dissolution_filing.payment_completion_date = datetime.utcnow().isoformat()
        dissolution_filing.save()
        withdrawn_filing_id = dissolution_filing.id
    
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
    


@pytest.mark.parametrize(
        'test_name, is_filing_exist, withdrawn_filing_status, is_future_effective, has_filing_id, expected_code, expected_msg',[
            ('SUCCESS', True, Filing.Status.PAID, True, True, None, None),
            ('FAIL_NOT_PAID', True, Filing.Status.PENDING, True, True, HTTPStatus.BAD_REQUEST, [FILING_NOT_PAID_MSG]),
            ('FAIL_NOT_FED', True, Filing.Status.PAID, False, True, HTTPStatus.BAD_REQUEST, [FILING_NOT_FED_MSG]),
            ('FAIL_FILING_NOT_EXIST', False, Filing.Status.PAID, True, True, HTTPStatus.BAD_REQUEST, [FILING_NOT_EXIST_MSG]),
            ('FAIL_MISS_FILING_ID', True, Filing.Status.PAID, True, False, HTTPStatus.UNPROCESSABLE_ENTITY, ''),
            ('FAIL_NOT_PAID_NOT_FED', True, Filing.Status.PENDING, False, True, HTTPStatus.BAD_REQUEST, [FILING_NOT_FED_MSG, FILING_NOT_PAID_MSG])
        ]
)
def test_validate_notice_of_withdrawal_new_business(session, test_name, is_filing_exist, withdrawn_filing_status, is_future_effective, has_filing_id, expected_code, expected_msg):
    identifier = 'Tb31yQIuBw'
    temp_bus = RegistrationBootstrap()
    temp_bus._identifier = identifier
    temp_bus.save()

    # file an IA with a FED
    ia_json = copy.deepcopy(FILING_HEADER)
    ia_json['filing']['header']['name'] = 'incorporationApplication'
    del ia_json['filing']['business']
    ia_dict = copy.deepcopy(INCORPORATION)
    ia_dict['nameRequest']['legalType'] = 'BC'
    ia_json['filing']['incorporationApplication'] = ia_dict
    ia_filing = factory_pending_filing(None, ia_json)
    ia_filing.temp_reg = identifier
    ia_filing.save()

    if is_future_effective:
        today = datetime.utcnow().date()
        future_effective_date = today + timedelta(days=5)
        future_effective_date = future_effective_date.isoformat()
        ia_filing.effective_date = future_effective_date
    if withdrawn_filing_status == Filing.Status.PAID:
        ia_filing.payment_completion_date = datetime.utcnow().isoformat()
    ia_filing.save()
    ia_filing_id = ia_filing.id

    # create a notice of withdrawal filing json
    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['header']['name'] = 'noticeOfWithdrawal'
    temp_business_dict =  {
        "legalType": "BC",
        "identifier": identifier
    }
    filing_json['filing']['business'] = temp_business_dict
    filing_json['filing']['noticeOfWithdrawal'] = copy.deepcopy(NOTICE_OF_WITHDRAWAL)

    if has_filing_id:
        if is_filing_exist:
            filing_json['filing']['noticeOfWithdrawal']['filingId'] = ia_filing_id
    else:
        del filing_json['filing']['noticeOfWithdrawal']['filingId']   

    err = validate(None, filing_json)
    if expected_code:
        assert err.code == expected_code
        if has_filing_id: # otherwise, won't pass schema validation, and the error msg will be very long
            assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None
