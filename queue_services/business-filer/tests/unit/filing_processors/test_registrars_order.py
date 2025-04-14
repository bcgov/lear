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
"""The Unit Tests for the Registrars Order filing."""
import copy
import random

from business_model.models import Filing
from registry_schemas.example_data import REGISTRARS_ORDER_FILING_TEMPLATE

from business_filer.worker import process_filing
from tests.unit import create_business, create_filing


async def test_worker_registrars_order(app, session):
    """Assert that the registrars order object is correctly populated to model objects."""
    identifier = 'BC1234567'
    business = create_business(identifier, legal_type='BC')

    filing = copy.deepcopy(REGISTRARS_ORDER_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing, business_id=business.id)).id

    filing_msg = {'filing': {'id': filing_id}}

    # Test
    await process_filing(filing_msg, app)

    # Check outcome
    final_filing = Filing.find_by_id(filing_id)
    assert filing['filing']['registrarsOrder']['fileNumber'] == final_filing.court_order_file_number
    assert filing['filing']['registrarsOrder']['effectOfOrder'] == final_filing.court_order_effect_of_order
    assert filing['filing']['registrarsOrder']['orderDetails'] == final_filing.order_details
