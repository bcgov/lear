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
"""The Unit Tests for the agm extension filing."""
import copy
import random

import pytest
from business_model.models import Filing
from registry_schemas.example_data import AGM_EXTENSION, FILING_HEADER

from business_filer.services.filer import process_filing
from business_filer.common.filing_message import FilingMessage
from tests.unit import create_business, create_filing


@pytest.mark.parametrize(
        'test_name',
        [
            ('general'), ('first_agm_year'), ('more_extension'), ('final_extension')
        ]
)
def test_filer_agm_extension(app, session, mocker, test_name):
    """Assert that the agm extension object is correctly populated to model objects."""
    identifier = f'BC{random.randint(1000000, 9999999)}'
    business = create_business(identifier, legal_type='BC')

    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['agmExtension'] = copy.deepcopy(AGM_EXTENSION)

    if test_name == 'first_agm_year':
        del filing_json['filing']['agmExtension']['prevAgmRefDate']

    if test_name != 'more_extension':
        del filing_json['filing']['agmExtension']['expireDateCurrExt']

    if test_name == 'final_extension':
        filing_json['filing']['agmExtension']['totalApprovedExt'] = 12
    else:
        filing_json['filing']['agmExtension']['totalApprovedExt'] = 6

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing = create_filing(payment_id, filing_json, business_id=business.id)

    filing_msg = FilingMessage(filing_identifier=filing.id)

    # mock out the email sender and event publishing
    mocker.patch('business_filer.services.publish_event.PublishEvent.publish_email_message', return_value=None)
    mocker.patch('business_filer.services.publish_event.PublishEvent.publish_event', return_value=None)

    # test
    process_filing(filing_msg)

    # check outcome
    final_filing = Filing.find_by_id(filing.id)
    assert final_filing.id
    assert final_filing.meta_data

    agm_extension = final_filing.meta_data.get('agmExtension')
    assert agm_extension
    assert filing_json['filing']['agmExtension']['year'] == agm_extension.get('year')
    assert filing_json['filing']['agmExtension']['isFirstAgm'] == agm_extension.get('isFirstAgm')
    assert filing_json['filing']['agmExtension']['extReqForAgmYear'] == agm_extension.get('extReqForAgmYear')
    assert filing_json['filing']['agmExtension']['totalApprovedExt'] == agm_extension.get('totalApprovedExt')
    assert filing_json['filing']['agmExtension']['extensionDuration'] == agm_extension.get('extensionDuration')

    if test_name == 'first_agm_year':
        assert agm_extension.get('prevAgmRefDate') is None
    else:
        assert filing_json['filing']['agmExtension']['prevAgmRefDate'] == agm_extension.get('prevAgmRefDate')

    if test_name == 'more_extension':
        assert filing_json['filing']['agmExtension']['expireDateCurrExt'] == agm_extension.get('expireDateCurrExt')
    else:
        assert agm_extension.get('expireDateCurrExt') is None

    if test_name == 'final_extension':
        assert agm_extension.get('isFinalExtension') is True
    else:
        assert agm_extension.get('isFinalExtension') is False
