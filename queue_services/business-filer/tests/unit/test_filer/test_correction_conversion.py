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
import io
import random

import pytest
from dateutil.parser import parse
from business_model.models import Business, Filing
from registry_schemas.example_data import CORRECTION_CONVERSION,\
                                        CONVERSION_FILING_TEMPLATE, FILING_HEADER

from business_filer.services.filer import process_filing
from tests.unit import create_entity, create_filing
from business_filer.common.filing_message import FilingMessage


@pytest.mark.parametrize(
    'test_name, filing_template, correction_template',
    [
        ('pending_correction_status', CONVERSION_FILING_TEMPLATE, CORRECTION_CONVERSION),
    ]
)
def test_conversion_correction(app, session, mocker, test_name, filing_template, correction_template):
    """Test the conversion correction functionality."""
    mocker.patch('business_filer.services.publish_event.PublishEvent.publish_email_message', return_value=None)
    mocker.patch('business_filer.services.publish_event.PublishEvent.publish_event', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.business_profile.update_business_profile',
                 return_value=None)
    mocker.patch('business_filer.services.AccountService.update_entity', return_value=None)

    # Create business
    identifier = f'FM{random.randint(1000000, 9999999)}'
    business = create_entity(identifier, 'SP', 'CONVERSION INC.')
    business_id = business.id
    business.save()

    # Create an initial conversion filing
    conversion_filing = copy.deepcopy(filing_template)
    conversion_payment_id = str(random.SystemRandom().getrandbits(0x58))
    conversion_filing_id = (create_filing(conversion_payment_id, conversion_filing, business_id=business_id)).id

    # Mock the filing message
    conversion_filing_msg = FilingMessage(filing_identifier=conversion_filing_id)

    # Call the process_filing method for the original conversion
    process_filing(conversion_filing_msg)

    # Simulate a correction filing
    correction_data = copy.deepcopy(FILING_HEADER)
    correction_data['filing']['correction'] = copy.deepcopy(correction_template)
    correction_data['filing']['header']['name'] = 'correction'
    correction_data['filing']['header']['legalType'] = 'SP'
    correction_data['filing']['business'] = {'identifier': identifier}
    # Update correction data to point to the original conversion filing
    if 'correction' not in correction_data['filing']:
        correction_data['filing']['correction'] = {}
    correction_data['filing']['correction']['correctedFilingId'] = conversion_filing_id
    correction_payment_id = str(random.SystemRandom().getrandbits(0x58))
    correction_filing_id = (create_filing(correction_payment_id, correction_data, business_id=business_id)).id

    # Mock the correction filing message
    correction_filing_msg = FilingMessage(filing_identifier=correction_filing_id)

    # Call the process_filing method for the correction
    process_filing(correction_filing_msg)

    # Assertions
    origin_filing = Filing.find_by_id(correction_filing_id)
    assert origin_filing.status
