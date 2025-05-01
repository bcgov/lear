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
"""The Unit Tests for the admin freeze filing."""
import copy
import random

from business_model.models import Business, Filing
from registry_schemas.example_data import ADMIN_FREEZE, FILING_HEADER

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import admin_freeze
from business_filer.services.filer import process_filing
from tests.unit import create_business, create_filing
from business_filer.common.filing_message import FilingMessage


def tests_filer_admin_freeze(app, session, mocker):
    """Assert that the admin freeze object is correctly populated to model objects."""
    identifier = f'BC{random.randint(1000000, 9999999)}'
    business = create_business(identifier, legal_type='BC')

    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['adminFreeze'] = copy.deepcopy(ADMIN_FREEZE)

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing_json, business_id=business.id)).id

    filing_msg = FilingMessage(filing_identifier=filing_id)

        # mock out the email sender and event publishing
    mocker.patch('business_filer.services.publish_event.PublishEvent.publish_email_message', return_value=None)
    mocker.patch('business_filer.services.publish_event.PublishEvent.publish_event', return_value=None)
    # Test
    process_filing(filing_msg)

    # Check outcome
    final_filing = Filing.find_by_id(filing_id)
    business = Business.find_by_internal_id(final_filing.business_id)

    assert business.admin_freeze == True
    assert business.state_filing_id is None
    assert business.dissolution_date is None

    adminFreeze = final_filing.meta_data.get('adminFreeze')
    assert filing_json['filing']['adminFreeze']['freeze'] == adminFreeze.get('freeze')
