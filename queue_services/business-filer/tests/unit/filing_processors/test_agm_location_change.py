# Copyright © 2023 Province of British Columbia
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
"""The Unit Tests for the agm location change filing."""
import copy
import random

from business_model.models import Filing
from registry_schemas.example_data import AGM_LOCATION_CHANGE, FILING_HEADER

from business_filer.worker import process_filing
from tests.unit import create_business, create_filing


async def test_worker_agm_location_change(app, session, mocker):
    """Assert that the agm location change object is correctly populated to model objects."""
    identifier = 'BC1234567'
    business = create_business(identifier, legal_type='BC')

    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['agmLocationChange'] = copy.deepcopy(AGM_LOCATION_CHANGE)

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing = create_filing(payment_id, filing_json, business_id=business.id)

    filing_msg = {'filing': {'id': filing.id}}

        # mock out the email sender and event publishing
    mocker.patch('entity_filer.worker.publish_email_message', return_value=None)
    mocker.patch('entity_filer.worker.publish_event', return_value=None)
    # Test
    await process_filing(filing_msg, app)

    # Check outcome
    final_filing = Filing.find_by_id(filing.id)
    assert final_filing.id
    assert final_filing.meta_data
    
    agm_location_change = final_filing.meta_data.get('agmLocationChange')
    assert filing_json['filing']['agmLocationChange']['year'] == agm_location_change.get('year')
    assert filing_json['filing']['agmLocationChange']['agmLocation'] == agm_location_change.get('agmLocation')
    assert filing_json['filing']['agmLocationChange']['reason'] == agm_location_change.get('reason')
