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
import pytz

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from legal_api.models import Filing
from legal_api.utils.legislation_datetime import LegislationDatetime

from registry_schemas.example_data import CONSENT_CONTINUATION_OUT, FILING_TEMPLATE

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors import consent_continuation_out
from tests.unit import create_business, create_filing


async def test_worker_consent_continuation_out(app, session):
    """Assert that the consent continuation out object is correctly populated to model objects."""
    identifier = 'BC1234567'
    business = create_business(identifier, legal_type='CP')

    filing_json = copy.deepcopy(FILING_TEMPLATE)
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['header']['name'] = 'consentContinuationOut'
    filing_json['filing']['consentContinuationOut'] = CONSENT_CONTINUATION_OUT

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    cco_filing = create_filing(payment_id, filing_json, business_id=business.id)

    filing_meta = FilingMeta()

    # Test
    consent_continuation_out.process(business, cco_filing, filing_json['filing'], filing_meta)
    business.save()

    # Check outcome
    final_filing = Filing.find_by_id(cco_filing.id)

    assert filing_json['filing']['consentContinuationOut']['courtOrder']['fileNumber'] == final_filing.court_order_file_number
    assert filing_json['filing']['consentContinuationOut']['courtOrder']['effectOfOrder'] == final_filing.court_order_effect_of_order
    assert filing_json['filing']['consentContinuationOut']['details'] == final_filing.order_details
    expiry_date = datetime.combine(LegislationDatetime.now(),
                                   datetime.min.time(),
                                   tzinfo=pytz.timezone("UTC")) \
                  + relativedelta(months=6) \
                  + timedelta(hours=8)
    assert datetime.fromisoformat(filing_meta.consent_continuation_out['expiry']) == expiry_date
    assert business.cco_expiry_date == expiry_date
