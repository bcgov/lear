# Copyright © 2022 Province of British Columbia
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
"""The Unit Tests for the Registrars Notation filing."""
import copy
import random

from legal_api.models import Business, Filing
from registry_schemas.example_data import PUT_BACK_ON, FILING_HEADER

from entity_filer.worker import process_filing
from tests.unit import create_business, create_filing


async def test_worker_registrars_notation(app, session):
    """Assert that the put back on object is correctly populated to model objects."""
    identifier = 'BC1234567'
    business = create_business(identifier, legal_type='BC')

    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['putBackOn'] = PUT_BACK_ON

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing = (create_filing(payment_id, filing_json, business_id=business.id))

    filing_msg = {'filing': {'id': filing.id}}

    # Test
    await process_filing(filing_msg, app)

    # Check outcome
    final_filing = Filing.find_by_id(filing.id)

    assert business.state == Business.State.ACTIVE
    assert business.state_filing_id == filing.id