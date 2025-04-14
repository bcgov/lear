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
"""The Unit Tests for the Continuation Out filing."""
import copy
import random

from datetime import datetime
from business_model.models import Business, Filing

from registry_schemas.example_data import CONTINUATION_OUT, FILING_TEMPLATE
from business_filer.common.legislation_datetime import LegislationDatetime

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import continuation_out
from tests.unit import create_business, create_filing


async def test_worker_continuation_out(app, session):
    """Assert that the continuation out object is correctly populated to model objects."""
    identifier = 'BC1234567'
    business = create_business(identifier, legal_type='CP')

    filing_json = copy.deepcopy(FILING_TEMPLATE)
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['header']['name'] = 'continuationOut'
    filing_json['filing']['continuationOut'] = CONTINUATION_OUT

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    continuation_out_filing = create_filing(payment_id, filing_json, business_id=business.id)

    filing_meta = FilingMeta()

    # Test
    continuation_out.process(business, continuation_out_filing, filing_json['filing'], filing_meta)
    business.save()

    # Check outcome
    final_filing = Filing.find_by_id(continuation_out_filing.id)
    foreign_jurisdiction_json = filing_json['filing']['continuationOut']['foreignJurisdiction']
    continuation_out_date_str = filing_json['filing']['continuationOut']['continuationOutDate']
    continuation_out_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(continuation_out_date_str)

    assert filing_json['filing']['continuationOut']['courtOrder']['fileNumber'] == final_filing.court_order_file_number
    assert filing_json['filing']['continuationOut']['courtOrder']['effectOfOrder'] == final_filing.court_order_effect_of_order

    assert business.state == Business.State.HISTORICAL
    assert business.state_filing_id == final_filing.id
    assert business.jurisdiction == foreign_jurisdiction_json['country'].upper()
    assert business.foreign_jurisdiction_region == foreign_jurisdiction_json['region'].upper()
    assert business.foreign_legal_name == filing_json['filing']['continuationOut']['legalName']
    assert business.continuation_out_date == continuation_out_date

    assert filing_meta.continuation_out['country'] == foreign_jurisdiction_json['country']
    assert filing_meta.continuation_out['region'] == foreign_jurisdiction_json['region']
    assert filing_meta.continuation_out['continuationOutDate'] == continuation_out_date_str
    assert filing_meta.continuation_out['legalName'] == filing_json['filing']['continuationOut']['legalName']
