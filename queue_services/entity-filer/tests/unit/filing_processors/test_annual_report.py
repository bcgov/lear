# Copyright © 2021 Province of British Columbia
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
import pytest
import random
from unittest.mock import patch

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from legal_api.models import BatchProcessing, Business, Filing
from registry_schemas.example_data import ANNUAL_REPORT

# from entity_filer.filing_processors.filing_components import create_party, create_role
from entity_filer.filing_meta import FilingMeta
from entity_filer.worker import process_filing
from tests.unit import (
    create_business,
    create_filing,
    factory_batch,
    factory_batch_processing
)
from tests import EPOCH_DATETIME


@pytest.mark.parametrize('test_name,flag_on,in_dissolution,eligibility,legal_type,', [
    ('AR successfully', True, False, False, 'CP'),
    ('AR successfully', True, False, False, 'BC'),
    ('Not withdrawn from the dissolution process', True, True, True, 'BC'),
    ('Withdrawn from the dissolution process', True, True, False, 'BC'),
    ('AR successfully when flag is off', False, True, False, 'BC'),
    ('AR successfully when flag is off', False, False, False, 'CP')
])
def test_process_ar_filing_involuntary_dissolution(app, session, test_name, flag_on, in_dissolution, eligibility, legal_type):
    """Assert that an AR filling can be applied to the model correctly."""
    from entity_filer.filing_processors import annual_report
    # vars
    identifier = 'CP1234567'

    business = create_business(identifier, legal_type)
    business.founding_date = EPOCH_DATETIME
    business.save()
    # create the batch and batch_processing.
    batch_status = 'PROCESSING'
    if in_dissolution:
        batch = factory_batch(status=batch_status)
        batch_processing = factory_batch_processing(batch_id=batch.id, identifier=identifier, business_id=business.id, status=batch_status)

    now = datetime.datetime.utcnow()
    if eligibility:
        # setup ar_date to """INTERVAL '26 MONTHS'"" to make the businees is eligibility
        ar_date = (now - relativedelta(years=4, months=1)).date()
        agm_date = (now - relativedelta(years=4, months=2)).date()
    else:
        ar_date = (now - relativedelta(months=1)).date()
        agm_date = (now - relativedelta(months=2)).date()

    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['business']['identifier'] = identifier
    ar['filing']['annualReport']['annualReportDate'] = ar_date.isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = agm_date.isoformat()

    filing_meta = FilingMeta()

    # TEST
    with freeze_time(now):
        filing = create_filing(json_filing=ar, business_id=business.id)
        annual_report.process(business, filing.filing_json['filing'], filing_meta=filing_meta, flag_on=flag_on)

        # check it out
        if flag_on and in_dissolution and not eligibility:
            assert batch_processing.status == BatchProcessing.BatchProcessingStatus.WITHDRAWN.value
            assert batch_processing.notes == 'Moved back into good standing'
        else:
            if in_dissolution:
                assert batch_processing.status == BatchProcessing.BatchProcessingStatus.PROCESSING.value
                assert batch_processing.notes == ''
            if legal_type == 'CP':
                # require the agm for [Business.LegalTypes.COOP.value, Business.LegalTypes.XPRO_LIM_PARTNR.value]
                assert str(business.last_agm_date) == str(agm_date)
                assert str(business.last_ar_date) == str(agm_date)
            else:
                assert str(business.last_ar_date) == str(ar_date)


async def test_process_ar_filing_no_agm(app, session):
    """Assert that a no agm AR filling can be applied to the model correctly."""
    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'

    # setup
    business = create_business(identifier)
    business_id = business.id
    now = datetime.date(2020, 9, 17)
    ar_date = datetime.date(2020, 8, 5)
    agm_date = None
    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['business']['identifier'] = identifier
    ar['filing']['annualReport']['annualReportDate'] = ar_date.isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = None

    # TEST
    with freeze_time(now):
        filing = create_filing(payment_id, ar, business.id)
        filing_id = filing.id
        filing_msg = {'filing': {'id': filing_id}}
        await process_filing(filing_msg, app)

    # Get modified data
    filing = Filing.find_by_id(filing_id)
    business = Business.find_by_internal_id(business_id)

    # check it out
    assert filing.transaction_id
    assert filing.business_id == business_id
    assert filing.status == Filing.Status.COMPLETED.value
    assert business.last_agm_date == agm_date
    assert datetime.datetime.date(business.last_ar_date) == ar_date
