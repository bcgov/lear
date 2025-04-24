# Copyright © 2025 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""The Test Suites to ensure that the worker is operating correctly."""
import copy
import datetime
import pytest
import random
from unittest.mock import patch

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from business_model.models import BatchProcessing, Business, Filing
from registry_schemas.example_data import ANNUAL_REPORT

# from business_filer.filing_processors.filing_components import create_party, create_role
from business_filer.common.filing_message import FilingMessage
from business_filer.filing_meta import FilingMeta
from business_filer.services.filer import process_filing
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
    from business_filer.filing_processors import annual_report
    # vars
    identifier = f'CP{random.randint(1000000, 9999999)}'

    business = create_business(identifier, legal_type)
    business.founding_date = EPOCH_DATETIME
    business.save()
    # create the batch and batch_processing.
    batch_status = 'PROCESSING'
    if in_dissolution:
        batch = factory_batch(status=batch_status)
        batch_processing = factory_batch_processing(batch_id=batch.id, identifier=identifier, business_id=business.id, status=batch_status)

    now = datetime.datetime.now(datetime.timezone.utc)
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
            # if legal_type == 'CP':
            #     # require the agm for [Business.LegalTypes.COOP.value, Business.LegalTypes.XPRO_LIM_PARTNR.value]
            #     assert str(business.last_agm_date) == str(agm_date)
            #     assert str(business.last_ar_date) == str(agm_date)
            # else:
            #     assert str(business.last_ar_date) == str(ar_date)
            assert str(business.last_ar_date) == str(ar_date)
            assert str(business.last_agm_date) == str(agm_date)


def test_process_ar_filing_no_agm(app, session):
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

    # mock out the email sender and event publishing
    # mocker.patch('business_filer.services.publish_event.PublishEvent.publish_email_message', return_value=None)
    # mocker.patch('business_filer.services.publish_event.PublishEvent.publish_event', return_value=None)

    # TEST
    with freeze_time(now):
        filing = create_filing(payment_id, ar, business.id)
        filing_id = filing.id
        filing_msg = FilingMessage(id=filing_id, filing_identifier=filing_id)
        process_filing(filing_msg)

    # Get modified data
    filing = Filing.find_by_id(filing_id)
    business = Business.find_by_internal_id(business_id)

    # check it out
    assert filing.transaction_id
    assert filing.business_id == business_id
    assert filing.status == Filing.Status.COMPLETED.value
    assert business.last_agm_date == agm_date
    assert datetime.datetime.date(business.last_ar_date) == ar_date
