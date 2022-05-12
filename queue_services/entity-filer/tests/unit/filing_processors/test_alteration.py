# Copyright © 2020 Province of British Columbia
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
"""The Unit Tests for the Incorporation filing."""
import copy
import random
from datetime import datetime
from typing import Final

import pytest
from legal_api.models import Business, Filing
from registry_schemas.example_data import (
    ALTERATION,
    ALTERATION_FILING_TEMPLATE,
    BUSINESS,
    COURT_ORDER,
    FILING_HEADER,
)

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors import alteration
from entity_filer.worker import process_filing
from tests.unit import create_business, create_filing


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
async def test_worker_alteration(app, session, mocker, orig_legal_type, new_legal_type):
    """Assert the worker process calls the alteration correctly."""
    identifier = 'BC1234567'
    business = create_business(identifier, legal_type=orig_legal_type)
    filing = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    filing['filing']['business']['legalType'] = orig_legal_type
    filing['filing']['alteration']['business']['legalType'] = new_legal_type

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing, business_id=business.id)).id

    filing_msg = {'filing': {'id': filing_id}}

    # mock out the email sender and event publishing
    mocker.patch('entity_filer.worker.publish_email_message', return_value=None)
    mocker.patch('entity_filer.worker.publish_event', return_value=None)
    mocker.patch('entity_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)
    mocker.patch('entity_filer.filing_processors.filing_components.business_profile.update_business_profile',
                 return_value=None)
    mocker.patch('legal_api.services.bootstrap.AccountService.update_entity', return_value=None)

    # Test
    await process_filing(filing_msg, app)

    # Check outcome
    business = Business.find_by_internal_id(business.id)
    assert business.legal_type == new_legal_type


@pytest.mark.parametrize(
    'test_name, legal_name, new_legal_name',
    [
        ('numbered_to_name', '1234567 B.C. LTD.', 'New Name'),
        ('name_to_numbered', 'Old Name', '1234567 B.C. LTD.'),
        ('no_change', '1234567 B.C. LTD.', None),  # No change in name
    ]
)
async def test_alteration_legal_name(app, session, mocker, test_name, legal_name, new_legal_name):
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

    filing_msg = {'filing': {'id': filing_id}}

    # mock out the email sender and event publishing
    mocker.patch('entity_filer.worker.publish_email_message', return_value=None)
    mocker.patch('entity_filer.worker.publish_event', return_value=None)
    mocker.patch('entity_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)
    mocker.patch('entity_filer.filing_processors.filing_components.business_profile.update_business_profile',
                 return_value=None)
    mocker.patch('legal_api.services.bootstrap.AccountService.update_entity', return_value=None)

    # Test
    await process_filing(filing_msg, app)

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


async def test_worker_alteration_court_order(app, session, mocker):
    """Assert the worker process calls the alteration correctly."""
    identifier = 'BC1234567'
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

    filing_msg = {'filing': {'id': filing_id}}

    # mock out the email sender and event publishing
    mocker.patch('entity_filer.worker.publish_email_message', return_value=None)
    mocker.patch('entity_filer.worker.publish_event', return_value=None)
    mocker.patch('entity_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)
    mocker.patch('entity_filer.filing_processors.filing_components.business_profile.update_business_profile',
                 return_value=None)
    mocker.patch('legal_api.services.bootstrap.AccountService.update_entity', return_value=None)

    # Test
    await process_filing(filing_msg, app)

    # Check outcome
    final_filing = Filing.find_by_id(filing_id)
    assert file_number == final_filing.court_order_file_number
    assert datetime.fromisoformat(order_date) == final_filing.court_order_date
    assert effect_of_order == final_filing.court_order_effect_of_order
