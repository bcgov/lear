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
"""The Unit Tests for the Special Resolution filing."""


import copy
import random

import pytest
from business_model.models import Business, Filing
from registry_schemas.example_data import CP_SPECIAL_RESOLUTION_TEMPLATE

from business_filer.services.filer import process_filing
from tests.unit import create_entity, create_filing


@pytest.mark.parametrize(
    'test_name, legal_name, new_legal_name,legal_type, filing_template',
    [
        ('name_change', 'Test Resolution', 'New Name', 'CP', CP_SPECIAL_RESOLUTION_TEMPLATE),
        ('no_change', 'Test Resolution', None, 'CP', CP_SPECIAL_RESOLUTION_TEMPLATE)
    ]
)
def test_special_resolution(app, session, mocker, test_name, legal_name, new_legal_name,
                                  legal_type, filing_template):
    """Assert the worker process calls the legal name change correctly."""
    identifier = 'CP1234567'
    business = create_entity(identifier, legal_type, legal_name)
    business_id = business.id
    filing = copy.deepcopy(filing_template)
    if test_name == 'name_change':
        filing['filing']['changeOfName']['nameRequest']['legalName'] = new_legal_name
    else:
        del filing['filing']['changeOfName']

    payment_id = str(random.SystemRandom().getrandbits(0x58))

    filing_id = (create_filing(payment_id, filing, business_id=business_id)).id
    filing_msg = FilingMessage(filing_identifier=filing_id)

    # mock out the email sender and event publishing
    mocker.patch('business_filer.services.filer.publish_email_message', return_value=None)
    mocker.patch('business_filer.services.filer.publish_event', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)

    # Test
    process_filing(filing_msg)

    # Check outcome
    final_filing = Filing.find_by_id(filing_id)
    change_of_name = final_filing.meta_data.get('changeOfName', {})
    business = Business.find_by_internal_id(business_id)

    assert len(business.resolutions.all()) == 1
    resolution = business.resolutions.first()
    assert resolution.id
    assert resolution.resolution_type == 'SPECIAL'
    assert resolution.resolution_sub_type == 'specialResolution'

    if new_legal_name:
        assert business.legal_name == new_legal_name
        assert change_of_name.get('toLegalName') == new_legal_name
        assert change_of_name.get('fromLegalName') == legal_name
    else:
        assert business.legal_name == legal_name
        assert change_of_name == {}
