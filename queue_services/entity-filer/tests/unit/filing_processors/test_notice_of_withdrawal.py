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
"""The Unit Tests for the Notice Of Withdrawal filing."""
import copy
import datetime
import random
import pytest

from legal_api.models import Filing
from registry_schemas.example_data import FILING_HEADER, INCORPORATION, NOTICE_OF_WITHDRAWAL

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors import notice_of_withdrawal
from tests.unit import create_business, create_filing


def test_worker_notice_of_withdrawal(session):
    """Assert that the notice of withdrawal filing processes correctly."""
    # Setup
    identifier = 'BC1234567'
    business = create_business(identifier, legal_type='BC')
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    
    # Create IA filing
    ia_filing_json = copy.deepcopy(FILING_HEADER)
    ia_filing_json['filing']['business']['identifier'] = identifier
    ia_filing_json['filing']['incorporationApplication'] = copy.deepcopy(INCORPORATION)
    ia_filing = create_filing(payment_id, ia_filing_json, business_id=business.id)
    ia_filing.payment_completion_date = datetime.datetime.utcnow()
    ia_filing._meta_data = {}
    ia_filing.save()

    now_filing_json = copy.deepcopy(FILING_HEADER)
    now_filing_json['filing']['business']['identifier'] = identifier
    now_filing_json['filing']['noticeOfWithdrawal'] = copy.deepcopy(NOTICE_OF_WITHDRAWAL)
    now_filing_json['filing']['noticeOfWithdrawal']['filingId'] = ia_filing.id
    now_filing = create_filing(payment_id, now_filing_json, business_id=business.id)
    now_filing.withdrawn_filing_id = ia_filing.id
    now_filing.save()
    filing_meta = FilingMeta()

    assert ia_filing.status == Filing.Status.PAID.value

    # Test
    notice_of_withdrawal.process(now_filing, now_filing_json['filing'], filing_meta)
    business.save()

    # Check results
    final_ia_filing = Filing.find_by_id(ia_filing.id)
    final_now_filing = Filing.find_by_id(now_filing.id)

    assert now_filing_json['filing']['noticeOfWithdrawal']['courtOrder']['orderDetails'] == final_now_filing.order_details
    assert final_ia_filing.status == Filing.Status.WITHDRAWN.value
    assert final_ia_filing.withdrawal_pending == False
    assert final_ia_filing.meta_data.get('withdrawnDate')
