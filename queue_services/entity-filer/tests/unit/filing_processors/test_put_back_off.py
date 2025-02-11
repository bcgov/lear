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
"""The Unit Tests for the Put Back Off filing."""
import copy
import random

from legal_api.models import Business, Filing
from legal_api.utils.datetime import datetime
from legal_api.utils.legislation_datetime import LegislationDatetime
from registry_schemas.example_data import FILING_HEADER, PUT_BACK_OFF

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors import put_back_off
from tests.unit import create_business, create_filing


def test_worker_put_back_off(session):
    """Assert that the put back off filing processes correctly."""
    # Setup
    identifier = 'BC1234567'
    business = create_business(identifier, legal_type='BC')
    expiry = datetime.utcnow()
    business.restoration_expiry_date = expiry
    
    # Create filing
    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['putBackOff'] = copy.deepcopy(PUT_BACK_OFF)
    
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing = create_filing(payment_id, filing_json, business_id=business.id)
    
    filing_meta = FilingMeta()
    
    # Test
    put_back_off.process(business, filing_json['filing'], filing, filing_meta)
    business.save()
    
    # Check results
    final_filing = Filing.find_by_id(filing.id)
    
    assert business.state == Business.State.HISTORICAL
    assert business.state_filing_id == filing.id
    assert business.restoration_expiry_date is None
    assert filing.order_details == final_filing.order_details
    
    assert filing_meta.reason == 'Limited Restoration Expired'
    assert filing_meta.expiryDate == expiry.date().isoformat() 
