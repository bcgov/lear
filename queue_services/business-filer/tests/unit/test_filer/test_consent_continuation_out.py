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
"""The Unit Tests for the Consent Continuation Out filing."""
import copy
import random
from datetime import datetime

import pytest
from business_model.models import ConsentContinuationOut, Filing
from business_filer.common.legislation_datetime import LegislationDatetime
from registry_schemas.example_data import CONSENT_CONTINUATION_OUT, FILING_TEMPLATE

from business_filer.services.filer import process_filing
from tests.unit import create_business, create_filing
from business_filer.common.filing_message import FilingMessage


@pytest.mark.parametrize(
    'test_name, effective_date, expiry_date',
    [
        ('STD_TO_DST', '2023-05-31T17:00:00-07:00', '2023-12-01T23:59:00-08:00'),
        ('DST_TO_STD', '2023-01-31T17:00:00-08:00', '2023-07-31T23:59:00-07:00'),
        ('STD_TO_STD', '2023-03-12T17:00:00-07:00', '2023-09-12T23:59:00-07:00'),
        # DST_TO_DST is not possible. Example: 2023-11-06 (starting day of DST) + 6 months = 2024-05-06 (in STD)
    ]
)
def tests_filer_consent_continuation_out(app, session, mocker, test_name, effective_date, expiry_date):
    """Assert that the consent continuation out object is correctly populated to model objects."""
    effective_date = LegislationDatetime.as_legislation_timezone(datetime.fromisoformat(effective_date))
    expiry_date = LegislationDatetime.as_legislation_timezone(datetime.fromisoformat(expiry_date))

    identifier = 'BC1234567'
    business = create_business(identifier, legal_type='BC')
    business.save()
    business_id = business.id

    filing_json = copy.deepcopy(FILING_TEMPLATE)
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['header']['name'] = 'consentContinuationOut'
    filing_json['filing']['consentContinuationOut'] = CONSENT_CONTINUATION_OUT

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    cco_filing = create_filing(payment_id, filing_json, business_id=business_id)

    cco_filing.effective_date = LegislationDatetime.as_utc_timezone(effective_date)
    cco_filing.save()
    filing_msg = FilingMessage(filing_identifier=cco_filing.id)

    # mock out the email sender and event publishing
    mocker.patch('business_filer.services.filer.publish_email_message', return_value=None)
    mocker.patch('business_filer.services.filer.publish_event', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.business_profile.update_business_profile',
                 return_value=None)
    mocker.patch('business_filer.services.AccountService.update_entity', return_value=None)

    # Test
    process_filing(filing_msg)

    # Check outcome
    final_filing = Filing.find_by_id(cco_filing.id)

    assert filing_json['filing']['consentContinuationOut']['courtOrder']['fileNumber'] == \
        final_filing.court_order_file_number
    assert filing_json['filing']['consentContinuationOut']['courtOrder']['effectOfOrder'] == \
        final_filing.court_order_effect_of_order

    expiry_date_utc = LegislationDatetime.as_utc_timezone(expiry_date)

    cco = ConsentContinuationOut.get_active_cco(business_id, expiry_date_utc)
    assert cco
    assert cco[0].consent_type == ConsentContinuationOut.ConsentTypes.continuation_out
    assert cco[0].foreign_jurisdiction == \
        filing_json['filing']['consentContinuationOut']['foreignJurisdiction']['country']
    assert cco[0].foreign_jurisdiction_region == \
        filing_json['filing']['consentContinuationOut']['foreignJurisdiction']['region']
    assert cco[0].expiry_date == expiry_date_utc

    assert final_filing.meta_data['consentContinuationOut']['country'] == \
        filing_json['filing']['consentContinuationOut']['foreignJurisdiction']['country']
    assert final_filing.meta_data['consentContinuationOut']['region'] == \
        filing_json['filing']['consentContinuationOut']['foreignJurisdiction']['region']
    assert final_filing.meta_data['consentContinuationOut']['expiry'] == expiry_date_utc.isoformat()
