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
import datetime
import random

from legal_api.models import Business, Filing
from registry_schemas.example_data import TRANSITION_FILING_TEMPLATE

from entity_filer.worker import process_filing
from tests.pytest_marks import integration_affiliation
from tests.unit import create_filing


@integration_affiliation
async def test_transition_filing(app, session, account):
    """Assert we can create a business based on transition filing."""
    filing = copy.deepcopy(TRANSITION_FILING_TEMPLATE)

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing = (create_filing(payment_id, filing))
    filing.payment_account = account
    filing.save()

    filing_msg = {'filing': {'id': filing.id}}

    # Test
    await process_filing(filing_msg, app)

    # Check outcome
    filing = Filing.find_by_id(filing.id)
    business = Business.find_by_internal_id(filing.business_id)

    filing_json = filing.filing_json
    assert business
    assert filing
    assert filing.status == Filing.Status.COMPLETED.value
    assert business.identifier == filing_json['filing']['business']['identifier']
    assert business.founding_date == datetime.datetime.fromisoformat(filing['filing']['business']['foundingDate'])
    assert business.legal_type == filing['filing']['business']['legalType']
    assert business.legal_name == filing['filing']['business']['legalName']
    assert business.restriction_ind is False
    assert len(business.share_classes.all()) == len(filing_json['filing']['transition']['shareClasses'])
    assert len(business.offices.all()) == len(filing_json['filing']['transition']['offices'])
    assert len(business.aliases.all()) == 3
    assert len(business.resolutions.all()) == 2
    assert len(business.party_roles.all()) == 2
