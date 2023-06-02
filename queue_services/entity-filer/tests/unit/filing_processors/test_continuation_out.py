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
"""The Unit Tests for the Consent Continuation Out filing."""
import copy
import random
import pytest

from dateutil.relativedelta import relativedelta
from legal_api.models import Business, Filing
from legal_api.utils.legislation_datetime import LegislationDatetime

from registry_schemas.example_data import CONTINUATION_OUT, FILING_TEMPLATE

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors import continuation_out
from tests.unit import create_business, create_filing

@pytest.mark.parametrize('test_name, delta_months, state', [
    ('business_active', -6, Business.State.ACTIVE),
    ('business_historical', 6, Business.State.HISTORICAL),
])
async def test_worker_continuation_out(app, session, test_name, delta_months, state):
    """Assert that the continuation out object is correctly populated to model objects."""
    identifier = 'BC1234567'
    business = create_business(identifier, legal_type='CP')
    continuation_out_date = (LegislationDatetime.now() + relativedelta(months=delta_months)).strftime('%Y-%m-%d')

    filing_json = copy.deepcopy(FILING_TEMPLATE)
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['header']['name'] = 'continuationOut'
    filing_json['filing']['continuationOut'] = CONTINUATION_OUT
    filing_json['filing']['continuationOut']['continuationOutDate'] = continuation_out_date

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    continuation_out_filing = create_filing(payment_id, filing_json, business_id=business.id)

    filing_meta = FilingMeta()

    # Test
    continuation_out.process(business, continuation_out_filing, filing_json['filing'], filing_meta)
    business.save()

    # Check outcome
    final_filing = Filing.find_by_id(continuation_out_filing.id)
    foreign_jurisdiction_json = filing_json['filing']['continuationOut']['foreignJurisdiction']

    assert filing_json['filing']['continuationOut']['courtOrder']['fileNumber'] == final_filing.court_order_file_number
    assert filing_json['filing']['continuationOut']['courtOrder']['effectOfOrder'] == final_filing.court_order_effect_of_order
    assert filing_json['filing']['continuationOut']['details'] == final_filing.order_details

    assert business.state == state
    assert business.jurisdiction == foreign_jurisdiction_json['country']
    assert business.foreign_jurisdiction_region == foreign_jurisdiction_json['region']
    assert business.foreign_legal_name == filing_json['filing']['continuationOut']['legalName']
    
    assert filing_meta.continuation_out['foreignJurisdictionCountry'] == foreign_jurisdiction_json['country']
    assert filing_meta.continuation_out['foreignJurisdictionRegion'] == foreign_jurisdiction_json['region']
    assert filing_meta.continuation_out['foreignLegalName'] == filing_json['filing']['continuationOut']['legalName']
