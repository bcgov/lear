# Copyright © 2022 Province of British Columbia
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
"""The Unit Tests for the Correction filing."""
import copy
import random
from datetime import datetime
from typing import Final
from unittest.mock import patch

import pytest
from legal_api.models import Address, Business, Filing, PartyRole
from legal_api.services import NaicsService
from registry_schemas.example_data import (
    CHANGE_OF_REGISTRATION_TEMPLATE,
    CORRECTION_REGISTRATION,
    COURT_ORDER,
    REGISTRATION,
)

from entity_filer.worker import process_filing
from tests.unit import create_entity, create_office, create_office_address, create_party, create_party_role, \
    create_filing, factory_completed_filing

CONTACT_POINT = {
    'email': 'no_one@never.get',
    'phone': '123-456-7890'
}

CHANGE_OF_REGISTRATION_APPLICATION = copy.deepcopy(CHANGE_OF_REGISTRATION_TEMPLATE)

GP_CORRECTION = copy.deepcopy(CORRECTION_REGISTRATION)
GP_CORRECTION['filing']['correction']['parties'].append(REGISTRATION['parties'][1])
GP_CORRECTION['filing']['correction']['legalType'] = 'GP'

SP_CORRECTION = copy.deepcopy(CORRECTION_REGISTRATION)
SP_CORRECTION['filing']['business']['legalType'] = 'SP'
SP_CORRECTION['filing']['correction']['legalType'] = 'SP'
SP_CORRECTION['filing']['correction']['nameRequest']['legalType'] = 'SP'
SP_CORRECTION['filing']['correction']['parties'][0]['roles'] = [
    {
        'roleType': 'Completing Party',
        'appointmentDate': '2022-01-01'

    },
    {
        'roleType': 'Proprietor',
        'appointmentDate': '2022-01-01'

    }
]

naics_response = {
    'code': REGISTRATION['business']['naics']['naicsCode'],
    'naicsKey': 'a4667c26-d639-42fa-8af3-7ec73e392569'
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'test_name, legal_name, new_legal_name,legal_type, filing_template',
    [
        ('name_change', 'Test Firm', 'New Name', 'GP', GP_CORRECTION),
        ('no_change', 'Test Firm', None, 'GP', GP_CORRECTION),
        ('name_change', 'Test Firm', 'New Name', 'SP', SP_CORRECTION),
        ('no_change', 'Test Firm', None, 'SP', SP_CORRECTION)
    ]
)
async def test_correction_name_start_date(app, session, mocker, test_name, legal_name, new_legal_name,
                                                 legal_type, filing_template):
    """Assert the worker process calls the legal name change correctly."""

    identifier = 'FM1234567'
    business = create_entity(identifier, legal_type, legal_name)
    business.save()
    business_id = business.id

    filing = copy.deepcopy(filing_template)

    corrected_filing = factory_completed_filing(business, CHANGE_OF_REGISTRATION_APPLICATION)
    filing['filing']['correction']['correctedFilingId'] = corrected_filing.id

    if test_name == 'name_change':
        filing['filing']['correction']['nameRequest']['legalName'] = new_legal_name
    else:
        del filing['filing']['correction']['nameRequest']

    payment_id = str(random.SystemRandom().getrandbits(0x58))

    filing_id = (create_filing(payment_id, filing, business_id=business_id)).id
    filing_msg = {'filing': {'id': filing_id}}

    # mock out the email sender and event publishing
    mocker.patch('entity_filer.worker.publish_email_message', return_value=None)
    mocker.patch('entity_filer.worker.publish_event', return_value=None)
    mocker.patch('entity_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)
    mocker.patch('entity_filer.filing_processors.filing_components.business_profile.update_business_profile',
                 return_value=None)
    mocker.patch('legal_api.services.bootstrap.AccountService.update_entity', return_value=None)

    # Test
    with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
        await process_filing(filing_msg, app)

    # Check outcome
    final_filing = Filing.find_by_id(filing_id)
    correction = final_filing.meta_data.get('correction', {})
    business = Business.find_by_internal_id(business_id)

    if new_legal_name:
        assert business.legal_name == new_legal_name
        assert correction.get('toLegalName') == new_legal_name
        assert correction.get('fromLegalName') == legal_name
    else:
        assert business.legal_name == legal_name
        assert correction.get('toLegalName') is None
        assert correction.get('fromLegalName') is None

    corrected_filing = Filing.find_by_id(corrected_filing.id)
    filing_comments = final_filing.comments.all()
    assert len(filing_comments) == 1
    assert filing_comments[0].comment == filing['filing']['correction']['comment']
    assert len(corrected_filing.comments.all()) == 1
    assert business.founding_date.isoformat() == '2022-01-01T08:00:00+00:00'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'test_name,legal_type, legal_name, filing_template',
    [
        ('sp_address_change', 'SP', 'Test Firm', SP_CORRECTION),
        ('gp_address_change', 'GP', 'Test Firm', GP_CORRECTION)
    ]
)
async def test_correction_business_address(app, session, mocker, test_name, legal_type, legal_name,
                                                       filing_template):
    """Assert the worker process calls the business address change correctly."""
    identifier = 'FM1234567'
    business = create_entity(identifier, legal_type, legal_name)
    business.save()
    business_id = business.id

    office = create_office(business, 'registeredOffice')

    business_delivery_address = create_office_address(business, office, 'delivery')
    business_mailing_address = create_office_address(business, office, 'mailing')

    business_delivery_address_id = business_delivery_address.id
    business_mailing_address_id = business_mailing_address.id

    filing = copy.deepcopy(filing_template)

    corrected_filing = factory_completed_filing(business, CHANGE_OF_REGISTRATION_APPLICATION)
    filing['filing']['correction']['correctedFilingId'] = corrected_filing.id

    del filing['filing']['correction']['nameRequest']

    filing['filing']['correction']['offices']['businessOffice']['deliveryAddress']['id'] = \
        business_delivery_address_id
    filing['filing']['correction']['offices']['businessOffice']['mailingAddress']['id'] = \
        business_mailing_address_id

    payment_id = str(random.SystemRandom().getrandbits(0x58))

    filing_id = (create_filing(payment_id, filing, business_id=business_id)).id
    filing_msg = {'filing': {'id': filing_id}}

    ret_filing = Filing.find_by_id(filing_id)
    print(ret_filing.json)

    # mock out the email sender and event publishing
    mocker.patch('entity_filer.worker.publish_email_message', return_value=None)
    mocker.patch('entity_filer.worker.publish_event', return_value=None)
    mocker.patch('entity_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)
    mocker.patch('entity_filer.filing_processors.filing_components.business_profile.update_business_profile',
                 return_value=None)
    mocker.patch('legal_api.services.bootstrap.AccountService.update_entity', return_value=None)

    # Test
    with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
        await process_filing(filing_msg, app)

    # Check outcome
    changed_delivery_address = Address.find_by_id(business_delivery_address_id)
    for key in ['streetAddress', 'postalCode', 'addressCity', 'addressRegion']:
        assert changed_delivery_address.json[key] == \
               filing['filing']['correction']['offices']['businessOffice']['deliveryAddress'][key]
    changed_mailing_address = Address.find_by_id(business_mailing_address_id)
    for key in ['streetAddress', 'postalCode', 'addressCity', 'addressRegion']:
        assert changed_mailing_address.json[key] == \
               filing['filing']['correction']['offices']['businessOffice']['mailingAddress'][key]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'test_name, legal_type, filing_template',
    [
        ('gp_court_order', 'GP', GP_CORRECTION),
        ('sp_court_order', 'SP', SP_CORRECTION)
    ]
)
async def test_worker_correction_court_order(app, session, mocker, test_name, legal_type, filing_template):
    """Assert the worker process process the court order correctly."""
    identifier = 'FM1234567'
    business = create_entity(identifier, legal_type, 'Test Entity')

    filing = copy.deepcopy(filing_template)

    corrected_filing = factory_completed_filing(business, CHANGE_OF_REGISTRATION_APPLICATION)
    filing['filing']['correction']['correctedFilingId'] = corrected_filing.id

    file_number: Final = '#1234-5678/90'
    order_date: Final = '2021-01-30T09:56:01+08:00'
    effect_of_order: Final = 'hasPlan'

    filing['filing']['correction']['contactPoint'] = CONTACT_POINT

    filing['filing']['correction']['courtOrder'] = COURT_ORDER
    filing['filing']['correction']['courtOrder']['effectOfOrder'] = effect_of_order

    del filing['filing']['correction']['nameRequest']

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
    with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
        await process_filing(filing_msg, app)

    # Check outcome
    final_filing = Filing.find_by_id(filing_id)
    assert file_number == final_filing.court_order_file_number
    assert datetime.fromisoformat(order_date) == final_filing.court_order_date
    assert effect_of_order == final_filing.court_order_effect_of_order


@pytest.mark.asyncio
async def test_worker_proprietor_name_and_address_change(app, session, mocker):
    """Assert the worker process process the court order correctly."""
    identifier = 'FM1234567'
    business = create_entity(identifier, 'SP', 'Test Entity')
    business_id = business.id

    party = create_party(SP_CORRECTION['filing']['correction']['parties'][0])
    party_id = party.id

    create_party_role(business, party, ['proprietor'], datetime.utcnow())

    filing = copy.deepcopy(SP_CORRECTION)

    corrected_filing = factory_completed_filing(business, CHANGE_OF_REGISTRATION_APPLICATION)
    filing['filing']['correction']['correctedFilingId'] = corrected_filing.id

    filing['filing']['correction']['contactPoint'] = CONTACT_POINT
    filing['filing']['correction']['parties'][0]['officer']['id'] = party_id
    filing['filing']['correction']['parties'][0]['officer']['firstName'] = 'New Name'
    filing['filing']['correction']['parties'][0]['officer']['middleInitial'] = 'New Name'
    filing['filing']['correction']['parties'][0]['mailingAddress']['streetAddress'] = 'New Name'
    filing['filing']['correction']['parties'][0]['deliveryAddress']['streetAddress'] = 'New Name'

    del filing['filing']['correction']['nameRequest']

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
    with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
        await process_filing(filing_msg, app)

    # Check outcome
    business = Business.find_by_internal_id(business_id)
    party = business.party_roles.all()[0].party
    assert party.first_name == filing['filing']['correction']['parties'][0]['officer']['firstName'].upper()
    assert party.delivery_address.street == \
           filing['filing']['correction']['parties'][0]['deliveryAddress']['streetAddress']
    assert party.mailing_address.street == \
           filing['filing']['correction']['parties'][0]['mailingAddress']['streetAddress']


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'test_name',
    [
        'gp_add_partner',
        'gp_edit_partner_name_and_address',
        'gp_delete_partner',
    ]
)
async def test_worker_partner_name_and_address_change(app, session, mocker, test_name):
    """Assert the worker processes the court order correctly."""
    identifier = 'FM1234567'
    business = create_entity(identifier, 'GP', 'Test Entity')
    business_id = business.id

    party1 = create_party(GP_CORRECTION['filing']['correction']['parties'][0])
    party_id_1 = party1.id
    party2 = create_party(GP_CORRECTION['filing']['correction']['parties'][1])
    party_id_2 = party2.id

    create_party_role(business, party1, ['partner'], datetime.utcnow())
    create_party_role(business, party2, ['partner'], datetime.utcnow())

    filing = copy.deepcopy(GP_CORRECTION)

    corrected_filing = factory_completed_filing(business, CHANGE_OF_REGISTRATION_APPLICATION)
    filing['filing']['correction']['correctedFilingId'] = corrected_filing.id

    filing['filing']['correction']['contactPoint'] = CONTACT_POINT

    if test_name == 'gp_add_partner':
        filing['filing']['correction']['parties'][0]['officer']['id'] = party_id_1
        filing['filing']['correction']['parties'][1]['officer']['id'] = party_id_2
        new_party_json = GP_CORRECTION['filing']['correction']['parties'][1]
        del new_party_json['officer']['id']
        new_party_json['officer']['firstName'] = 'New Name'
        filing['filing']['correction']['parties'].append(new_party_json)

    if test_name == 'gp_edit_partner_name_and_address':
        filing['filing']['correction']['parties'][0]['officer']['id'] = party_id_1
        filing['filing']['correction']['parties'][0]['officer']['firstName'] = 'New Name a'
        filing['filing']['correction']['parties'][0]['officer']['middleInitial'] = 'New Name a'
        filing['filing']['correction']['parties'][0]['mailingAddress']['streetAddress'] = 'New Name'
        filing['filing']['correction']['parties'][0]['deliveryAddress']['streetAddress'] = 'New Name'
        filing['filing']['correction']['parties'][1]['officer']['id'] = party_id_2

    if test_name == 'gp_delete_partner':
        del filing['filing']['correction']['parties'][1]

    del filing['filing']['correction']['nameRequest']

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
    with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
        await process_filing(filing_msg, app)

    # Check outcome
    business = Business.find_by_internal_id(business_id)

    if test_name == 'gp_edit_partner_name_and_address':
        party = business.party_roles.all()[0].party
        assert party.first_name == \
               filing['filing']['correction']['parties'][0]['officer']['firstName'].upper()
        assert party.delivery_address.street == \
               filing['filing']['correction']['parties'][0]['deliveryAddress']['streetAddress']
        assert party.mailing_address.street == \
               filing['filing']['correction']['parties'][0]['mailingAddress']['streetAddress']
        assert business.party_roles.all()[0].cessation_date is None
        assert business.party_roles.all()[1].cessation_date is None

    if test_name == 'gp_delete_partner':
        deleted_role = PartyRole.get_party_roles_by_party_id(business_id, party_id_2)[0]
        assert deleted_role.cessation_date is not None

    if test_name == 'gp_add_partner':
        assert len(PartyRole.get_parties_by_role(business_id, 'partner')) == 3
        assert len(business.party_roles.all()) == 3
        for party_role in business.party_roles.all():
            assert party_role.cessation_date is None
