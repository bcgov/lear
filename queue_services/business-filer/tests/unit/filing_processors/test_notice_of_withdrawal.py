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

from business_model.models import Filing
# from legal_api.services import RegistrationBootstrapService
from registry_schemas.example_data import ALTERATION, FILING_HEADER, INCORPORATION, NOTICE_OF_WITHDRAWAL

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import notice_of_withdrawal
from tests.unit import create_business, create_filing


@pytest.mark.parametrize('test_name,filing_type,filing_template,identifier', [
    ('IA Withdrawn Filing', 'incorporationApplication', INCORPORATION, 'TJO4XI2qMo'),
    ('alteration Withdrawn Filing', 'alteration', ALTERATION, 'BC1234567')
])
def test_worker_notice_of_withdrawal(session, test_name, filing_type, filing_template, identifier):
    """Assert that the notice of withdrawal filing processes correctly."""
    # Setup
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    
    # Create withdrawn_filing
    withdrawn_filing_json = copy.deepcopy(FILING_HEADER)
    withdrawn_filing_json['filing']['business']['legalType'] = 'BC'
    withdrawn_filing_json['filing']['business']['identifier'] = identifier
    withdrawn_filing_json['filing'][filing_type] = copy.deepcopy(filing_template)
    if identifier.startswith('T'):
        # TODO: Fix this
        # business = RegistrationBootstrapService.create_bootstrap(account=28)
        withdrawn_filing = create_filing(token=payment_id, json_filing=withdrawn_filing_json, bootstrap_id=business.identifier)
    else:
        business = create_business(identifier, legal_type='BC')
        withdrawn_filing = create_filing(payment_id, withdrawn_filing_json, business_id=business.id)
    withdrawn_filing.payment_completion_date = datetime.datetime.utcnow()  # for setting the filing status PAID
    withdrawn_filing._meta_data = {}
    withdrawn_filing.save()

    # Create NoW filing
    now_filing_json = copy.deepcopy(FILING_HEADER)
    now_filing_json['filing']['business']['identifier'] = business.identifier
    now_filing_json['filing']['noticeOfWithdrawal'] = copy.deepcopy(NOTICE_OF_WITHDRAWAL)
    now_filing_json['filing']['noticeOfWithdrawal']['filingId'] = withdrawn_filing.id
    now_filing = create_filing(payment_id, now_filing_json)
    now_filing.withdrawn_filing_id = withdrawn_filing.id
    now_filing.save()
    filing_meta = FilingMeta()

    assert withdrawn_filing.status == Filing.Status.PAID.value

    # Test
    notice_of_withdrawal.process(now_filing, now_filing_json['filing'], filing_meta)
    withdrawn_filing.save()

    # Check results
    final_withdrawn_filing = Filing.find_by_id(withdrawn_filing.id)
    final_now_filing = Filing.find_by_id(now_filing.id)

    assert now_filing_json['filing']['noticeOfWithdrawal']['courtOrder']['orderDetails'] == final_now_filing.order_details
    assert final_withdrawn_filing.status == Filing.Status.WITHDRAWN.value
    assert final_withdrawn_filing.withdrawal_pending == False
    assert final_withdrawn_filing.meta_data.get('withdrawnDate')
