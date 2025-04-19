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
"""The Unit Tests for the Incorporation filing."""
import copy
import random
from datetime import datetime
from typing import Final

import pytest
from business_model.models import Business, Filing, Document
from business_model.models.document import DocumentType
# from legal_api.services.minio import MinioService
from registry_schemas.example_data import (
    ALTERATION,
    ALTERATION_FILING_TEMPLATE,
    BUSINESS,
    COURT_ORDER,
    FILING_HEADER,
)

from business_filer.common.filing_message import FilingMessage
from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import alteration
from business_filer.services.filer import process_filing
from tests.unit import create_business, create_filing
# from tests.utils import upload_file, assert_pdf_contains_text


CONTACT_POINT = {
    'email': 'no_one@never.get',
    'phone': '123-456-7890'
}


@pytest.mark.parametrize(
    'orig_legal_type, new_legal_type',
    [
        (Business.LegalTypes.COMP.value, Business.LegalTypes.BCOMP.value),
        (Business.LegalTypes.BCOMP.value, Business.LegalTypes.COMP.value)
    ]
)
def test_alteration_process(app, session, orig_legal_type, new_legal_type):
    """Assert that the business legal type is altered."""
    # setup
    identifier = 'BC1234567'
    business = create_business(identifier)
    business.legal_type = orig_legal_type

    alteration_filing = copy.deepcopy(FILING_HEADER)
    alteration_filing['filing']['business']['legalType'] = orig_legal_type
    alteration_filing['filing']['alteration'] = copy.deepcopy(ALTERATION)
    alteration_filing['filing']['alteration']['business']['legalType'] = new_legal_type
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_submission = create_filing(payment_id, alteration_filing, business_id=business.id)

    filing_meta = FilingMeta()

    # test
    alteration.process(business=business,
                       filing_submission=filing_submission,
                       filing=alteration_filing['filing'],
                       filing_meta=filing_meta)

    # validate
    assert business.legal_type == new_legal_type


@pytest.mark.parametrize(
    'orig_legal_type, new_legal_type',
    [
        (Business.LegalTypes.COMP.value, Business.LegalTypes.BCOMP.value),
        (Business.LegalTypes.BCOMP.value, Business.LegalTypes.COMP.value)
    ]
)
def tests_filer_alteration(app, session, mocker, orig_legal_type, new_legal_type):
    """Assert the worker process calls the alteration correctly."""
    identifier = 'BC1234567'
    business = create_business(identifier, legal_type=orig_legal_type)
    business.restriction_ind = True
    business.save()

    filing = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    filing['filing']['business']['legalType'] = orig_legal_type
    filing['filing']['alteration']['business']['legalType'] = new_legal_type
    filing['filing']['alteration']['provisionsRemoved'] = True

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing, business_id=business.id)).id

    filing_msg = FilingMessage(filing_identifier=filing_id)

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
    business = Business.find_by_internal_id(business.id)
    assert business.legal_type == new_legal_type
    assert not business.restriction_ind


@pytest.mark.parametrize(
    'test_name, legal_name, new_legal_name',
    [
        ('numbered_to_name', '1234567 B.C. LTD.', 'New Name'),
        ('name_to_numbered', 'Old Name', '1234567 B.C. LTD.'),
        ('no_change', '1234567 B.C. LTD.', None),  # No change in name
    ]
)
def test_alteration_legal_name(app, session, mocker, test_name, legal_name, new_legal_name):
    """Assert the worker process calls the alteration correctly."""
    identifier = 'BC1234567'
    business = create_business(identifier)
    business.legal_name = legal_name
    business.save()
    filing = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    if test_name == 'numbered_to_name':
        filing['filing']['alteration']['nameRequest']['legalName'] = new_legal_name
    elif test_name == 'name_to_numbered':
        del filing['filing']['alteration']['nameRequest']['nrNumber']
        del filing['filing']['alteration']['nameRequest']['legalName']
    else:
        del filing['filing']['alteration']['nameRequest']

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing, business_id=business.id)).id

    filing_msg = FilingMessage(filing_identifier=filing_id)

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
    business = Business.find_by_internal_id(business.id)
    final_filing = Filing.find_by_id(filing_id)
    alteration = final_filing.meta_data.get('alteration', {})
    if new_legal_name:
        assert business.legal_name == new_legal_name
        assert alteration.get('toLegalName') == new_legal_name
        assert alteration.get('fromLegalName') == legal_name
    else:
        assert business.legal_name == legal_name
        assert alteration.get('toLegalName') is None
        assert alteration.get('fromLegalName') is None


def tests_filer_alteration_court_order(app, session, mocker):
    """Assert the worker process calls the alteration correctly."""
    identifier = f'BC{random.randint(1000000, 9999999)}'
    business = create_business(identifier, legal_type='BC')

    file_number: Final = '#1234-5678/90'
    order_date: Final = '2021-01-30T09:56:01+08:00'
    effect_of_order: Final = 'hasPlan'

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['alteration'] = {}
    filing['filing']['alteration']['business'] = BUSINESS
    filing['filing']['alteration']['contactPoint'] = CONTACT_POINT

    filing['filing']['alteration']['courtOrder'] = COURT_ORDER
    filing['filing']['alteration']['courtOrder']['effectOfOrder'] = effect_of_order

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing, business_id=business.id)).id

    filing_msg = FilingMessage(filing_identifier=filing_id)

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
    final_filing = Filing.find_by_id(filing_id)
    assert file_number == final_filing.court_order_file_number
    assert datetime.fromisoformat(order_date) == final_filing.court_order_date
    assert effect_of_order == final_filing.court_order_effect_of_order


@pytest.mark.parametrize('new_association_type', [
    (Business.AssociationTypes.CP_HOUSING_COOPERATIVE.value),
    (Business.AssociationTypes.CP_COMMUNITY_SERVICE_COOPERATIVE.value)
])
def test_alteration_coop_association_type(app, session, new_association_type):
    """Assert that the coop association type is altered."""
    # setup
    identifier = f'CP{random.randint(1000000, 9999999)}'
    business = create_business(identifier)
    business.legal_type = Business.LegalTypes.COOP.value

    alteration_filing = copy.deepcopy(FILING_HEADER)
    alteration_filing['filing']['business']['legalType'] = Business.LegalTypes.COOP.value
    alteration_filing['filing']['alteration'] = copy.deepcopy(ALTERATION)
    alteration_filing['filing']['alteration']['cooperativeAssociationType'] = new_association_type
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_submission = create_filing(payment_id, alteration_filing, business_id=business.id)

    filing_meta = FilingMeta()

    # test
    alteration.process(business=business,
                       filing_submission=filing_submission,
                       filing=alteration_filing['filing'],
                       filing_meta=filing_meta)

    # validate
    assert business.association_type == new_association_type
