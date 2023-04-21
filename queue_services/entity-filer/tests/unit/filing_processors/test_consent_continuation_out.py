# Copyright © 2021 Province of British Columbia
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
"""The Unit Tests for the Court Order filing."""
import copy
import random
from datetime import datetime
from dateutil.relativedelta import relativedelta

from legal_api.models import DocumentType, Filing
from registry_schemas.example_data import CONSENT_CONTINUATION_OUT

from entity_filer.worker import process_filing
from tests.unit import create_business, create_filing


async def test_worker_consent_continuation_out(app, session):
    """Assert that the court order object is correctly populated to model objects."""
    identifier = 'BC1234567'
    business = create_business(identifier, legal_type='BC')
    filing_type = 'consentContinuationOut'

    filing = copy.deepcopy(CONSENT_CONTINUATION_OUT)
    filing['filing']['business']['identifier'] = identifier

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing, business_id=business.id)).id

    filing_msg = {'filing': {'id': filing_id}}

    # Test
    await process_filing(filing_msg, app)

    # Check outcome
    final_filing = Filing.find_by_id(filing_id)
    assert filing['filing']['consentContinuationOut']['courtOrder']['fileNumber'] == final_filing.filing_type.court_order_file_number
    assert filing['filing']['consentContinuationOut']['courtOrder']['effectOfOrder'] == final_filing.filing_type.court_order_effect_of_order
    assert filing['filing']['consentContinuationOut']['orderDetails'] == final_filing.order_details
    assert final_filing.meta_data.consentContinuationOut == {'expiry': datetime.now() + relativedelta(months=6)}
    assert final_filing.meta_data.legalFilings == ['consentContinuationOut']
