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
"""The Unit Tests for the admin freeze filing."""
import copy
import random

from legal_api.models import Business, Filing
from registry_schemas.example_data import ADMIN_FREEZE, FILING_HEADER

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors import admin_freeze
from entity_filer.worker import process_filing
from tests.unit import create_business, create_filing


def test_worker_admin_freeze(app, session):
    """Assert that the admin freeze object is correctly populated to model objects."""
    identifier = 'BC1234567'
    business = create_business(identifier, legal_type='BC')

    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['adminFreeze'] = copy.deepcopy(ADMIN_FREEZE)

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing = (create_filing(payment_id, filing_json, business_id=business.id))

    filing_msg = {'filing': {'id': filing.id}}

    filing_meta = FilingMeta()
    filing = create_filing('123', filing_json)

    # Test
    admin_freeze.process(business, filing_json['filing'], filing, filing_meta)
    business.save()

    # Check outcome
    final_filing = Filing.find_by_id(filing.id)

    assert business.admin_freeze == True
    assert business.state_filing_id is None
    assert business.dissolution_date is None
    assert filing_json['filing']['adminFreeze']['details'] == final_filing.order_details
