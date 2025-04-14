# Copyright © 2020 Province of British Columbia
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
"""The Test Suites to ensure that the worker is operating correctly."""
import copy
import random

# from legal_api.core import Filing as FilingCore
from business_model.models import Business, Filing, PartyRole
from registry_schemas.example_data import ANNUAL_REPORT, FILING_HEADER, SPECIAL_RESOLUTION

from business_filer.worker import process_filing
from tests.unit import create_business, create_filing


async def test_technical_correction_ar(app, session):
    """Assert we can create a business based on transition filing."""
    filing_data = copy.deepcopy(ANNUAL_REPORT)

    business = create_business(filing_data['filing']['business']['identifier'])
    business_identifier = business.identifier

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing = (create_filing(payment_id, filing_data, business.id))
    filing_id = filing.id

    filing_msg = {'filing': {'id': filing.id}}

    # sanity check
    # that it is an AR, and it is based on the ANNUAL_REPORT template
    assert filing.json['filing']['annualReport']
    assert filing.json['filing']['annualReport']['annualGeneralMeetingDate']  \
        == ANNUAL_REPORT['filing']['annualReport']['annualGeneralMeetingDate']
    # and the businesses last AR date is null
    assert not business.last_ar_date
    
    # subvert the filing
    technical_correction_filing = copy.deepcopy(FILING_HEADER)
    technical_correction_filing['specialResolution'] = copy.deepcopy(SPECIAL_RESOLUTION)
    filing.tech_correction_json = technical_correction_filing 
    # over ride the state and skip state setting listeners for this test
    filing.skip_status_listener = True
    filing._status = 'PENDING'
    filing.save()

    # Test
    await process_filing(filing_msg, app)

    # Check outcome
    business = Business.find_by_identifier(business_identifier)
    filing = Filing.find_by_id(filing_id)
    assert not business.last_ar_date
    assert filing.filing_type == 'annualReport'
