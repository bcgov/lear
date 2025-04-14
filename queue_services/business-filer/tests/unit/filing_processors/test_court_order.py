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

from business_model.models import DocumentType, Filing
from registry_schemas.example_data import COURT_ORDER_FILING_TEMPLATE

from business_filer.worker import process_filing
from tests.unit import create_business, create_filing


async def test_worker_court_order(app, session):
    """Assert that the court order object is correctly populated to model objects."""
    identifier = 'BC1234567'
    business = create_business(identifier, legal_type='BC')

    filing = copy.deepcopy(COURT_ORDER_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing, business_id=business.id)).id

    filing_msg = {'filing': {'id': filing_id}}

    # Test
    await process_filing(filing_msg, app)

    # Check outcome
    final_filing = Filing.find_by_id(filing_id)
    assert filing['filing']['courtOrder']['fileNumber'] == final_filing.court_order_file_number
    assert filing['filing']['courtOrder']['effectOfOrder'] == final_filing.court_order_effect_of_order
    assert filing['filing']['courtOrder']['orderDetails'] == final_filing.order_details

    court_order_file = final_filing.documents.one_or_none()
    assert court_order_file
    assert court_order_file.type == DocumentType.COURT_ORDER.value
    assert court_order_file.file_key == filing['filing']['courtOrder']['fileKey']
