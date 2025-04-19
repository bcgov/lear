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
"""The Unit Tests for the Change of Registration filing."""
import copy
import random
from datetime import datetime
from typing import Final
from unittest.mock import patch

import pytest
from business_model.models import Address, Business, Filing, PartyRole
# from legal_api.services import NaicsService
from registry_schemas.example_data import (
    CHANGE_OF_REGISTRATION_TEMPLATE,
    COURT_ORDER,
    REGISTRATION,
)

from business_filer.services.filer import process_filing
from tests.unit import create_entity, create_office, create_office_address, create_party, create_party_role, \
    create_filing


CONTACT_POINT = {
    'email': 'no_one@never.get',
    'phone': '123-456-7890'
}

GP_CHANGE_OF_REGISTRATION = copy.deepcopy(CHANGE_OF_REGISTRATION_TEMPLATE)
GP_CHANGE_OF_REGISTRATION['filing']['changeOfRegistration']['parties'].append(REGISTRATION['parties'][1])

SP_CHANGE_OF_REGISTRATION = copy.deepcopy(CHANGE_OF_REGISTRATION_TEMPLATE)
SP_CHANGE_OF_REGISTRATION['filing']['business']['legalType'] = 'SP'
SP_CHANGE_OF_REGISTRATION['filing']['changeOfRegistration']['nameRequest']['legalType'] = 'SP'
SP_CHANGE_OF_REGISTRATION['filing']['changeOfRegistration']['parties'][0]['roles'] = [
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


@pytest.mark.parametrize(
    'test_name, legal_name, new_legal_name,legal_type, filing_template',
    [
        ('name_change', 'Test Firm', 'New Name', 'GP', GP_CHANGE_OF_REGISTRATION),
        ('no_change', 'Test Firm', None, 'GP', GP_CHANGE_OF_REGISTRATION),
        ('name_change', 'Test Firm', 'New Name', 'SP', SP_CHANGE_OF_REGISTRATION),
        ('no_change', 'Test Firm', None, 'SP', SP_CHANGE_OF_REGISTRATION)
    ]
)
async def test_change_of_registration_legal_name(app, session, mocker, test_name, legal_name, new_legal_name,
                                                 legal_type, filing_template):
    """Assert the worker process calls the legal name change correctly."""

    identifier = 'FM1234567'
    business = create_entity(identifier, legal_type, legal_name)
    business.save()
    business_id = business.id
    filing = copy.deepcopy(filing_template)
    if test_name == 'name_change':
        filing['filing']['changeOfRegistration']['nameRequest']['legalName'] = new_legal_name
    else:
        del filing['filing']['changeOfRegistration']['nameRequest']

    payment_id = str(random.SystemRandom().getrandbits(0x58))

    filing_id = (create_filing(payment_id, filing, business_id=business_id)).id
    filing_msg = {'filing': {'id': filing_id}}

    # mock out the email sender and event publishing
    mocker.patch('business_filer.services.filer.publish_email_message', return_value=None)
    mocker.patch('business_filer.services.filer.publish_event', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.business_profile.update_business_profile',
                 return_value=None)
    mocker.patch('business_filer.services.AccountService.update_entity', return_value=None)

    # Test
    # TODO: Fix this
    # with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
    #     await process_filing(filing_msg, app)

    # Check outcome
    final_filing = Filing.find_by_id(filing_id)
    change_of_registration = final_filing.meta_data.get('changeOfRegistration', {})
    business = Business.find_by_internal_id(business_id)

    if new_legal_name:
        assert business.legal_name == new_legal_name
        assert change_of_registration.get('toLegalName') == new_legal_name
        assert change_of_registration.get('fromLegalName') == legal_name
    else:
        assert business.legal_name == legal_name
        assert change_of_registration.get('toLegalName') is None
        assert change_of_registration.get('fromLegalName') is None


@pytest.mark.parametrize(
    'test_name,legal_type, legal_name, filing_template',
    [
        ('sp_address_change', 'Test Firm', 'SP', SP_CHANGE_OF_REGISTRATION),
        ('gp_address_change', 'Test Firm', 'GP', GP_CHANGE_OF_REGISTRATION)
    ]
)
async def test_change_of_registration_business_address(app, session, mocker, test_name, legal_type, legal_name,
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

    del filing['filing']['changeOfRegistration']['nameRequest']

    filing['filing']['changeOfRegistration']['offices']['businessOffice']['deliveryAddress']['id'] = \
        business_delivery_address_id
    filing['filing']['changeOfRegistration']['offices']['businessOffice']['mailingAddress']['id'] = \
        business_mailing_address_id

    payment_id = str(random.SystemRandom().getrandbits(0x58))

    filing_id = (create_filing(payment_id, filing, business_id=business_id)).id
    filing_msg = {'filing': {'id': filing_id}}

    # mock out the email sender and event publishing
    mocker.patch('business_filer.services.filer.publish_email_message', return_value=None)
    mocker.patch('business_filer.services.filer.publish_event', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.business_profile.update_business_profile',
                 return_value=None)
    mocker.patch('business_filer.services.AccountService.update_entity', return_value=None)

    # Test
    # TODO: Fix this
    # with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
    #     await process_filing(filing_msg, app)

    # Check outcome
    changed_delivery_address = Address.find_by_id(business_delivery_address_id)
    for key in ['streetAddress', 'postalCode', 'addressCity', 'addressRegion']:
        assert changed_delivery_address.json[key] == \
            filing['filing']['changeOfRegistration']['offices']['businessOffice']['deliveryAddress'][key]
    changed_mailing_address = Address.find_by_id(business_mailing_address_id)
    for key in ['streetAddress', 'postalCode', 'addressCity', 'addressRegion']:
        assert changed_mailing_address.json[key] == \
            filing['filing']['changeOfRegistration']['offices']['businessOffice']['mailingAddress'][key]


@pytest.mark.parametrize(
    'test_name, legal_type, filing_template',
    [
        ('gp_court_order', 'GP', GP_CHANGE_OF_REGISTRATION),
        ('sp_court_order', 'SP', SP_CHANGE_OF_REGISTRATION)
    ]
)
def tests_filer_change_of_registration_court_order(app, session, mocker, test_name, legal_type, filing_template):
    """Assert the worker process the court order correctly."""
    identifier = 'FM1234567'
    business = create_entity(identifier, legal_type, 'Test Entity')

    filing = copy.deepcopy(filing_template)

    file_number: Final = '#1234-5678/90'
    order_date: Final = '2021-01-30T09:56:01+08:00'
    effect_of_order: Final = 'hasPlan'

    filing['filing']['changeOfRegistration']['contactPoint'] = CONTACT_POINT

    filing['filing']['changeOfRegistration']['courtOrder'] = COURT_ORDER
    filing['filing']['changeOfRegistration']['courtOrder']['effectOfOrder'] = effect_of_order

    del filing['filing']['changeOfRegistration']['nameRequest']

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing, business_id=business.id)).id

    filing_msg = {'filing': {'id': filing_id}}

    # mock out the email sender and event publishing
    mocker.patch('business_filer.services.filer.publish_email_message', return_value=None)
    mocker.patch('business_filer.services.filer.publish_event', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.business_profile.update_business_profile',
                 return_value=None)
    mocker.patch('business_filer.services.AccountService.update_entity', return_value=None)

    # Test
    # TODO: Fix this
    # with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
    #     await process_filing(filing_msg, app)

    # Check outcome
    final_filing = Filing.find_by_id(filing_id)
    assert file_number == final_filing.court_order_file_number
    assert datetime.fromisoformat(order_date) == final_filing.court_order_date
    assert effect_of_order == final_filing.court_order_effect_of_order


def tests_filer_proprietor_name_and_address_change(app, session, mocker):
    """Assert the worker process the name and address change correctly."""
    identifier = 'FM1234567'
    business = create_entity(identifier, 'SP', 'Test Entity')
    business_id = business.id

    party = create_party(SP_CHANGE_OF_REGISTRATION['filing']['changeOfRegistration']['parties'][0])
    party_id = party.id

    create_party_role(business, party, ['proprietor'], datetime.utcnow())

    filing = copy.deepcopy(SP_CHANGE_OF_REGISTRATION)
    filing['filing']['changeOfRegistration']['contactPoint'] = CONTACT_POINT
    filing['filing']['changeOfRegistration']['parties'][0]['officer']['id'] = party_id
    filing['filing']['changeOfRegistration']['parties'][0]['officer']['firstName'] = 'New Name'
    filing['filing']['changeOfRegistration']['parties'][0]['officer']['middleInitial'] = 'New Name'
    filing['filing']['changeOfRegistration']['parties'][0]['mailingAddress']['streetAddress'] = 'New Name'
    filing['filing']['changeOfRegistration']['parties'][0]['deliveryAddress']['streetAddress'] = 'New Name'

    del filing['filing']['changeOfRegistration']['nameRequest']

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing, business_id=business.id)).id

    filing_msg = {'filing': {'id': filing_id}}

    # mock out the email sender and event publishing
    mocker.patch('business_filer.services.filer.publish_email_message', return_value=None)
    mocker.patch('business_filer.services.filer.publish_event', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.business_profile.update_business_profile',
                 return_value=None)
    mocker.patch('business_filer.services.AccountService.update_entity', return_value=None)

    # Test
    # TODO: Fix this
    # with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
    #     await process_filing(filing_msg, app)

    # Check outcome
    business = Business.find_by_internal_id(business_id)
    party = business.party_roles.all()[0].party
    assert party.first_name == filing['filing']['changeOfRegistration']['parties'][0]['officer']['firstName'].upper()
    assert party.delivery_address.street ==\
        filing['filing']['changeOfRegistration']['parties'][0]['deliveryAddress']['streetAddress']
    assert party.mailing_address.street == \
        filing['filing']['changeOfRegistration']['parties'][0]['mailingAddress']['streetAddress']


@pytest.mark.parametrize(
    'test_name',
    [
        'gp_add_partner',
        'gp_edit_partner_name_and_address',
        'gp_delete_partner',
    ]
)
def tests_filer_partner_name_and_address_change(app, session, mocker, test_name):
    """Assert the worker process the partner name and address change correctly."""
    identifier = 'FM1234567'
    business = create_entity(identifier, 'GP', 'Test Entity')
    business_id = business.id

    party1 = create_party(GP_CHANGE_OF_REGISTRATION['filing']['changeOfRegistration']['parties'][0])
    party_id_1 = party1.id
    party2 = create_party(GP_CHANGE_OF_REGISTRATION['filing']['changeOfRegistration']['parties'][1])
    party_id_2 = party2.id

    create_party_role(business, party1, ['partner'], datetime.utcnow())
    create_party_role(business, party2, ['partner'], datetime.utcnow())

    filing = copy.deepcopy(GP_CHANGE_OF_REGISTRATION)
    filing['filing']['changeOfRegistration']['contactPoint'] = CONTACT_POINT

    if test_name == 'gp_add_partner':
        filing['filing']['changeOfRegistration']['parties'][0]['officer']['id'] = party_id_1
        filing['filing']['changeOfRegistration']['parties'][1]['officer']['id'] = party_id_2
        new_party_json = GP_CHANGE_OF_REGISTRATION['filing']['changeOfRegistration']['parties'][1]
        del new_party_json['officer']['id']
        new_party_json['officer']['firstName'] = 'New Name'
        filing['filing']['changeOfRegistration']['parties'].append(new_party_json)

    if test_name == 'gp_edit_partner_name_and_address':
        filing['filing']['changeOfRegistration']['parties'][0]['officer']['id'] = party_id_1
        filing['filing']['changeOfRegistration']['parties'][0]['officer']['firstName'] = 'New Name a'
        filing['filing']['changeOfRegistration']['parties'][0]['officer']['middleInitial'] = 'New Name a'
        filing['filing']['changeOfRegistration']['parties'][0]['mailingAddress']['streetAddress'] = 'New Name'
        filing['filing']['changeOfRegistration']['parties'][0]['deliveryAddress']['streetAddress'] = 'New Name'
        filing['filing']['changeOfRegistration']['parties'][1]['officer']['id'] = party_id_2

    if test_name == 'gp_delete_partner':
        del filing['filing']['changeOfRegistration']['parties'][1]

    del filing['filing']['changeOfRegistration']['nameRequest']

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing, business_id=business.id)).id

    filing_msg = {'filing': {'id': filing_id}}

    # mock out the email sender and event publishing
    mocker.patch('business_filer.services.filer.publish_email_message', return_value=None)
    mocker.patch('business_filer.services.filer.publish_event', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.business_profile.update_business_profile',
                 return_value=None)
    mocker.patch('business_filer.services.AccountService.update_entity', return_value=None)

    # Test
    # TODO: Fix this
    # with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
    #     await process_filing(filing_msg, app)

    # Check outcome
    business = Business.find_by_internal_id(business_id)

    if test_name == 'gp_edit_partner_name_and_address':
        party = business.party_roles.all()[0].party
        assert party.first_name == \
            filing['filing']['changeOfRegistration']['parties'][0]['officer']['firstName'].upper()
        assert party.delivery_address.street == \
            filing['filing']['changeOfRegistration']['parties'][0]['deliveryAddress']['streetAddress']
        assert party.mailing_address.street == \
            filing['filing']['changeOfRegistration']['parties'][0]['mailingAddress']['streetAddress']
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
