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
import random
import pytest

from legal_api.models import Business, Filing
from registry_schemas.example_data import FILING_HEADER, INCORPORATION, NOTICE_OF_WITHDRAWAL

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors import notice_of_withdrawal
from tests.unit import create_business, create_filing


@pytest.mark.parametrize('test_name, withdrawal_pending,withdrawn_filing_status', [
    ('Process the Filing', False, False),
    ('Dont process the Filing', False, True),
    ('Dont process the Filing', True, False),
    ('Dont process the Filing', True, True),
])
def test_worker_notice_of_withdrawal(session, test_name, withdrawal_pending, withdrawn_filing_status):
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
    ia_filing.withdrawal_pending = withdrawal_pending
    if withdrawn_filing_status:
        ia_filing._status = Filing.Status.WITHDRAWN.value
    else:
        ia_filing._status = 'PENDING'
    ia_filing.skip_status_listener = True
    ia_filing.save()

    now_filing_json = copy.deepcopy(FILING_HEADER)
    now_filing_json['filing']['business']['identifier'] = identifier
    now_filing_json['filing']['noticeOfWithdrawal'] = copy.deepcopy(NOTICE_OF_WITHDRAWAL)
    now_filing_json['filing']['noticeOfWithdrawal']['filingId'] = ia_filing.id
    now_filing = create_filing(payment_id, now_filing_json, business_id=business.id)
    now_filing.withdrawn_filing_id = ia_filing.id
    now_filing.save()

    filing_meta = FilingMeta()
    
    # Test
    notice_of_withdrawal.process(now_filing, now_filing_json['filing'], filing_meta)
    business.save()
    
    # Check results
    final_ia_filing = Filing.find_by_id(ia_filing.id)
    final_now_filing = Filing.find_by_id(now_filing.id)

    assert now_filing_json['filing']['noticeOfWithdrawal']['courtOrder']['orderDetails'] == final_now_filing.order_details
    if withdrawal_pending or withdrawn_filing_status:
        assert final_ia_filing.status == ia_filing.status
        assert final_ia_filing.withdrawal_pending == ia_filing.withdrawal_pending
    else:
        assert final_ia_filing.status == Filing.Status.WITHDRAWN.value
        assert final_ia_filing.withdrawal_pending == False
