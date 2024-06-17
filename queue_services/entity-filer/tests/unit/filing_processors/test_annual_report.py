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

from freezegun import freeze_time
from legal_api.models import BatchProcessing, Business, Filing
from registry_schemas.example_data import ANNUAL_REPORT

# from entity_filer.filing_processors.filing_components import create_party, create_role
from entity_filer.filing_meta import FilingMeta
from entity_filer.worker import process_filing
from tests.unit import (
    create_batch,
    create_batch_processing,
    create_business,
    create_filing,
)


@pytest.mark.parametrize('test_name,flag_on', [
    ('flag is on', True),
    ('flag is off', False)
])
def test_process_ar_filing_involuntary_dissolution(app, session, test_name, flag_on):
    """Assert that an AR filling can be applied to the model correctly."""
    from entity_filer.filing_processors import annual_report
    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'

    # create a business that is not eligible for dissolution. ('CP' is not eligible types)
    business = create_business(identifier, 'CP')
    # create the batch and batch_processing that are in processing.
    batch = create_batch()
    batch_processing = create_batch_processing(business, batch.id)
    now = datetime.date(2020, 9, 17)
    ar_date = datetime.date(2020, 8, 5)
    agm_date = datetime.date(2020, 7, 1)
    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['business']['identifier'] = identifier
    ar['filing']['annualReport']['annualReportDate'] = ar_date.isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = agm_date.isoformat()

    filing_meta = FilingMeta()

    # TEST
    with freeze_time(now):
        filing = create_filing(payment_id, ar, business.id)
        annual_report.process(business, filing.filing_json['filing'], filing_meta=filing_meta, flag_on=flag_on)

    # check it out
    if flag_on == 'enable-involuntary-dissolution':
        assert batch_processing.status == BatchProcessing.BatchProcessingStatus.WITHDRAWN.value
        assert batch_processing.notes == 'Moved back to good standing'

    assert str(business.last_agm_date) == str(agm_date)
    assert str(business.last_ar_date) == str(agm_date)


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
