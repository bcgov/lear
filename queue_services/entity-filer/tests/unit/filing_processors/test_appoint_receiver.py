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
"""The Unit Tests for the Appoint Receiver filing."""

import copy
import random

from registry_schemas.example_data import APPOINT_RECEIVER, FILING_TEMPLATE

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors import appoint_receiver
from tests.unit import create_business, create_filing


def test_appoint_receiver_filing_process(app, session):
    """Assert that the appoint receiver object is correctly populated to model objects."""
    # Setup
    identifier = 'BC1234567'
    business = create_business(identifier, legal_type='BC')

    # Create filing
    filing_json = copy.deepcopy(FILING_TEMPLATE)
    filing_json['filing']['header']['name'] = 'appointReceiver'
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['appointReceiver'] = copy.deepcopy(APPOINT_RECEIVER)

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing = create_filing(payment_id, filing_json, business_id=business.id)

    filing_meta = FilingMeta()

    # Test
    appoint_receiver.process(business, filing_json['filing'], filing, filing_meta)
    business.save()

    # Assertions
    assert len(business.party_roles.all()) == 1
    assert business.party_roles[0].role == 'receiver'
