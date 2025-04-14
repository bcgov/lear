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

from business_model.models import Business, Filing
from registry_schemas.example_data import ADMIN_FREEZE, FILING_HEADER

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import admin_freeze
from business_filer.worker import process_filing
from tests.unit import create_business, create_filing


async def test_worker_admin_freeze(app, session, mocker):
    """Assert that the admin freeze object is correctly populated to model objects."""
    identifier = 'BC1234567'
    business = create_business(identifier, legal_type='BC')

    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['adminFreeze'] = copy.deepcopy(ADMIN_FREEZE)

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing_json, business_id=business.id)).id

    filing_msg = {'filing': {'id': filing_id}}

        # mock out the email sender and event publishing
    mocker.patch('entity_filer.worker.publish_email_message', return_value=None)
    mocker.patch('entity_filer.worker.publish_event', return_value=None)
    # Test
    await process_filing(filing_msg, app)

    # Check outcome
    final_filing = Filing.find_by_id(filing_id)
    business = Business.find_by_internal_id(final_filing.business_id)

    assert business.admin_freeze == True
    assert business.state_filing_id is None
    assert business.dissolution_date is None

    adminFreeze = final_filing.meta_data.get('adminFreeze')
    assert filing_json['filing']['adminFreeze']['freeze'] == adminFreeze.get('freeze')
