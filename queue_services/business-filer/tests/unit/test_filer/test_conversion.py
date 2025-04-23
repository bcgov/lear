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
"""The Unit Tests for the Conversion filing."""
import copy
import random

import pytest
from datetime import datetime, timezone
from unittest.mock import patch
from business_model.models import Address, Business, Filing, PartyRole
from registry_schemas.example_data import (
    CONVERSION_FILING_TEMPLATE,
    FIRMS_CONVERSION,
    COURT_ORDER,
    REGISTRATION,
)

from business_filer.services.filer import process_filing
from tests.unit import create_entity, create_filing, create_party, create_party_role
from business_filer.common.filing_message import FilingMessage
from business_filer.common.services import NaicsService


CONTACT_POINT = {
    'email': 'no_one@never.get',
    'phone': '123-456-7890'
}

naics_response = {
    'code': REGISTRATION['business']['naics']['naicsCode'],
    'naicsKey': 'a4667c26-d639-42fa-8af3-7ec73e392569'
}

GP_CONVERSION = copy.deepcopy(CONVERSION_FILING_TEMPLATE)
GP_CONVERSION['filing']['conversion'] = copy.deepcopy(FIRMS_CONVERSION)
GP_CONVERSION['filing']['business']['legalType'] = 'GP'
GP_CONVERSION['filing']['conversion']['nameRequest']['legalType'] = 'GP'

SP_CONVERSION = copy.deepcopy(CONVERSION_FILING_TEMPLATE)
SP_CONVERSION['filing']['conversion'] = copy.deepcopy(FIRMS_CONVERSION)
SP_CONVERSION['filing']['business']['legalType'] = 'SP'
SP_CONVERSION['filing']['conversion']['nameRequest']['legalType'] = 'SP'
del SP_CONVERSION['filing']['conversion']['parties'][1]
SP_CONVERSION['filing']['conversion']['parties'][0]['roles'] = [
    {
        'roleType': 'Completing Party',
        'appointmentDate': '2022-01-01'

    },
    {
        'roleType': 'Proprietor',
        'appointmentDate': '2022-01-01'

    }
]

@pytest.mark.parametrize(
    'test_name, legal_name, new_legal_name,legal_type, filing_template',
    [
        ('conversion_gp', 'Test Firm', 'New Name', 'GP', GP_CONVERSION),
        ('conversion_sp', 'Test Firm', 'New Name', 'SP', SP_CONVERSION)
    ]
)
def test_conversion(app, session, mocker, test_name, legal_name, new_legal_name,
                                                 legal_type, filing_template):
    """Assert the worker process conversion  filing correctly."""

    identifier = 'FM1234567'
    business = create_entity(identifier, legal_type, legal_name)
    business.save()
    business_id = business.id
    filing = copy.deepcopy(filing_template)
    filing['filing']['business']['legalType'] = legal_type
    # Name Change
    filing['filing']['conversion']['nameRequest']['legalName'] = new_legal_name

    payment_id = str(random.SystemRandom().getrandbits(0x58))

    filing_id = (create_filing(payment_id, filing, business_id=business_id)).id
    filing_msg = FilingMessage(filing_identifier=filing_id)

    # mock out the email sender and event publishing
    mocker.patch('business_filer.services.publish_event.PublishEvent.publish_email_message', return_value=None)
    mocker.patch('business_filer.services.publish_event.PublishEvent.publish_event', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.business_profile.update_business_profile',
                 return_value=None)
    mocker.patch('business_filer.services.AccountService.update_entity', return_value=None)

    # Test
    process_filing(filing_msg)

    # Check outcome
    final_filing = Filing.find_by_id(filing_id)
    business = Business.find_by_internal_id(business_id)

    # Name Change
    assert business.legal_name == new_legal_name

    # Parties
    if legal_type == 'SP':
        assert len(final_filing.filing_party_roles.all()) == 1
        assert len(business.party_roles.all()) == 1
    if legal_type == 'GP':
        assert len(final_filing.filing_party_roles.all()) == 1
        assert len(business.party_roles.all()) == 2

    # Offices
    assert len(business.offices.all()) == 1
    assert business.offices.first().office_type == 'businessOffice'

    assert business.naics_description == \
           filing_template['filing']['conversion']['business']['naics']['naicsDescription']


def tests_filer_proprietor_new_address(app, session, mocker):
    """Assert the worker process the party new address correctly."""
    identifier = 'FM1234567'
    business = create_entity(identifier, 'SP', 'Test Entity')
    business_id = business.id

    party = create_party(SP_CONVERSION['filing']['conversion']['parties'][0])
    party_id = party.id
    party.delivery_address = None
    party.mailing_address = None
    party.save()
    assert party.delivery_address_id is None
    assert party.mailing_address_id is None

    create_party_role(business, party, ['proprietor'], datetime.now(timezone.utc))

    filing = copy.deepcopy(SP_CONVERSION)
    filing['filing']['conversion']['contactPoint'] = CONTACT_POINT
    filing['filing']['conversion']['parties'][0]['officer']['id'] = party_id
    filing['filing']['conversion']['parties'][0]['mailingAddress']['streetAddress'] = 'New Name'
    filing['filing']['conversion']['parties'][0]['deliveryAddress']['streetAddress'] = 'New Name'

    del filing['filing']['conversion']['nameRequest']

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing, business_id=business.id)).id

    filing_msg = FilingMessage(filing_identifier=filing_id)

    # mock out the email sender and event publishing
    mocker.patch('business_filer.services.publish_event.PublishEvent.publish_email_message', return_value=None)
    mocker.patch('business_filer.services.publish_event.PublishEvent.publish_event', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.business_profile.update_business_profile',
                 return_value=None)
    mocker.patch('business_filer.services.AccountService.update_entity', return_value=None)

    # Test
    with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
        process_filing(filing_msg)

    # Check outcome
    business = Business.find_by_internal_id(business_id)
    party = business.party_roles.all()[0].party
    assert party.delivery_address.street ==\
        filing['filing']['conversion']['parties'][0]['deliveryAddress']['streetAddress']
    assert party.mailing_address.street == \
        filing['filing']['conversion']['parties'][0]['mailingAddress']['streetAddress']


