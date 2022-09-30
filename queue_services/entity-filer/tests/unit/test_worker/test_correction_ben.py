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
from dateutil.parser import parse

import pytest
from legal_api.models import Address, Business, Filing, PartyRole
from legal_api.services import NaicsService
from registry_schemas.example_data import (
    COURT_ORDER,
    REGISTRATION,
)

from entity_filer.worker import process_filing
from tests.unit import create_entity, create_filing, create_office, create_office_address, create_party, \
    create_party_role, factory_completed_filing

CONTACT_POINT = {
    'email': 'no_one@never.get',
    'phone': '123-456-7890'
}

BEN_CORRECTION = {
    'filing': {
        'header': {
            'name': 'correction',
            'availableOnPaperOnly': False,
            'certifiedBy': 'full name',
            'email': 'no_one@never.get',
            'date': '2020-02-18',
            'routingSlipNumber': '123456789'
        },
        'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08T00:00:00+00:00',
            'identifier': 'BC1234567',
            'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
            'lastPreBobFilingTimestamp': '2019-01-01T20:05:49.068272+00:00',
            'legalName': 'legal name - BC1234567',
            'legalType': 'BEN'
        },
        'correction': {
            'correctedFilingId': 2,
            'correctedFilingType': 'registration',
            'correctedFilingDate': '2022-04-08',
            'type': 'CLIENT',
            'comment': 'Test Description',
            'legalType': 'BEN',
            'business': {
                'naics': {
                    'naicsCode': '919110',
                    'naicsDescription': 'This Canadian industry comprises establishments of foreign \
               governments in Canada primarily engaged in governmental service activities.'
                },
                'taxId': '123456789',
                'identifier': 'BC1234567'
            },
            'offices': {
                'registeredOffice': {
                    'deliveryAddress': {
                        'streetAddress': 'delivery_address - address line one',
                        'addressCity': 'delivery_address city',
                        'addressCountry': 'Canada',
                        'postalCode': 'H0H0H0',
                        'addressRegion': 'BC'
                    },
                    'mailingAddress': {
                        'streetAddress': 'mailing_address - address line one',
                        'addressCity': 'mailing_address city',
                        'addressCountry': 'Canada',
                        'postalCode': 'H0H0H0',
                        'addressRegion': 'BC'
                    }
                }
            },
            'contactPoint': {
                'email': 'no_one@never.get',
                'phone': '(123) 456-7890'
            },
            'startDate': '2022-01-01',
            'nameRequest': {
                'nrNumber': 'NR 8798956',
                'legalName': 'HAULER MEDIA INC.',
                'legalType': 'BEN'
            },
            'parties': [
                {
                    'officer': {
                        'id': 1,
                        'firstName': 'Joe',
                        'lastName': 'Swanson',
                        'middleName': 'P',
                        'email': 'joe@email.com',
                        'organizationName': '',
                        'partyType': 'person'
                    },
                    'mailingAddress': {
                        'streetAddress': 'mailing_address - address line one',
                        'streetAddressAdditional': '',
                        'addressCity': 'mailing_address city',
                        'addressCountry': 'CA',
                        'postalCode': 'H0H0H0',
                        'addressRegion': 'BC'
                    },
                    'deliveryAddress': {
                        'streetAddress': 'delivery_address - address line one',
                        'streetAddressAdditional': '',
                        'addressCity': 'delivery_address city',
                        'addressCountry': 'CA',
                        'postalCode': 'H0H0H0',
                        'addressRegion': 'BC'
                    },
                    'roles': [
                        {
                            'roleType': 'Director',
                            'appointmentDate': '2022-01-01'
                        }
                    ]
                },
                {
                    'officer': {
                        'id': 2,
                        'firstName': 'Peter',
                        'lastName': 'Griffin',
                        'middleName': '',
                        'partyType': 'person'
                    },
                    'mailingAddress': {
                        'streetAddress': 'mailing_address - address line one',
                        'streetAddressAdditional': '',
                        'addressCity': 'mailing_address city',
                        'addressCountry': 'CA',
                        'postalCode': 'H0H0H0',
                        'addressRegion': 'BC'
                    },
                    'roles': [
                        {
                            'roleType': 'Completing Party',
                            'appointmentDate': '2022-01-01'
                        }
                    ]
                }
            ],
            'provisionsRemoved': False,
            'shareStructure': {
                'resolutionDates': [
                    '2022-07-01',
                    '2022-08-01'
                ],
                'shareClasses': [
                    {
                        'id': 1,
                        'name': 'Share Class 1',
                        'priority': 1,
                        'hasMaximumShares': True,
                        'maxNumberOfShares': 100,
                        'hasParValue': True,
                        'parValue': 10,
                        'currency': 'CAD',
                        'hasRightsOrRestrictions': False,
                        'series': [
                            {
                                'id': 1,
                                'name': 'Share Series 1',
                                'priority': 1,
                                'hasMaximumShares': True,
                                'maxNumberOfShares': 50,
                                'hasRightsOrRestrictions': False,
                            },
                            {
                                'id': 2,
                                'name': 'Share Series 2',
                                'priority': 2,
                                'hasMaximumShares': True,
                                'maxNumberOfShares': 100,
                                'hasRightsOrRestrictions': False,
                            }
                        ]
                    },
                    {
                        'id': 2,
                        'name': 'Share Class 2',
                        'priority': 1,
                        'hasMaximumShares': False,
                        'maxNumberOfShares': None,
                        'hasParValue': False,
                        'parValue': None,
                        'currency': None,
                        'hasRightsOrRestrictions': True,
                        'series': []
                    }
                ]
            }
        }
    }
}

BEN_CORRECTION_APPLICATION = BEN_CORRECTION

naics_response = {
    'code': REGISTRATION['business']['naics']['naicsCode'],
    'naicsKey': 'a4667c26-d639-42fa-8af3-7ec73e392569'
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'test_name, legal_name, new_legal_name, legal_type, filing_template',
    [
        ('name_change', 'Test Firm', 'New Name', 'BEN', BEN_CORRECTION),
        ('no_change', 'Test Firm', None, 'BEN', BEN_CORRECTION)
    ]
)
async def test_correction_name_start_date(app, session, mocker, test_name, legal_name, new_legal_name,
                                                 legal_type, filing_template):
    """Assert the worker process calls the legal name change correctly."""

    identifier = 'BC1234567'
    business = create_entity(identifier, legal_type, legal_name)
    business.save()
    business_id = business.id

    filing = copy.deepcopy(filing_template)

    corrected_filing_id = factory_completed_filing(business, BEN_CORRECTION_APPLICATION).id
    filing['filing']['correction']['correctedFilingId'] = corrected_filing_id

    if test_name == 'name_change':
        filing['filing']['correction']['nameRequest']['legalName'] = new_legal_name
        filing['filing']['business']['legalName'] = new_legal_name
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

    corrected_filing = Filing.find_by_id(corrected_filing_id)
    filing_comments = final_filing.comments.all()
    assert len(filing_comments) == 1
    assert filing_comments[0].comment == filing['filing']['correction']['comment']
    assert len(corrected_filing.comments.all()) == 1
    assert business.start_date.isoformat() == '2022-01-01T08:00:00+00:00'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'test_name, legal_type, legal_name, filing_template',
    [
        ('ben_address_change', 'BEN', 'Test Firm', BEN_CORRECTION)
    ]
)
async def test_correction_business_address(app, session, mocker, test_name, legal_type, legal_name,
                                                       filing_template):
    """Assert the worker process calls the business address change correctly."""
    identifier = 'BC1234567'
    business = create_entity(identifier, legal_type, legal_name)
    business.save()
    business_id = business.id

    office = create_office(business, 'registeredOffice')

    office_delivery_address = create_office_address(business, office, 'delivery')
    office_mailing_address = create_office_address(business, office, 'mailing')

    office_delivery_address_id = office_delivery_address.id
    office_mailing_address_id = office_mailing_address.id

    filing = copy.deepcopy(filing_template)

    corrected_filing_id = factory_completed_filing(business, BEN_CORRECTION_APPLICATION).id
    filing['filing']['correction']['correctedFilingId'] = corrected_filing_id

    del filing['filing']['correction']['nameRequest']

    filing['filing']['correction']['offices']['registeredOffice']['deliveryAddress'] = \
        Address.find_by_id(office_delivery_address_id).json
    filing['filing']['correction']['offices']['registeredOffice']['mailingAddress'] = \
        Address.find_by_id(office_mailing_address_id).json

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
    changed_delivery_address = Address.find_by_id(office_delivery_address_id)
    print('changed_delivery_address: ', changed_delivery_address)
    for key in ['streetAddress', 'postalCode', 'addressCity', 'addressRegion']:
        assert changed_delivery_address.json[key] == \
               filing['filing']['correction']['offices']['registeredOffice']['deliveryAddress'][key]
    changed_mailing_address = Address.find_by_id(office_mailing_address_id)
    print('changed_mailing_address: ', changed_mailing_address)
    for key in ['streetAddress', 'postalCode', 'addressCity', 'addressRegion']:
        assert changed_mailing_address.json[key] == \
               filing['filing']['correction']['offices']['registeredOffice']['mailingAddress'][key]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'test_name, legal_type, filing_template',
    [
        ('ben_court_order', 'BEN', BEN_CORRECTION),
    ]
)
async def test_worker_correction_court_order(app, session, mocker, test_name, legal_type, filing_template):
    """Assert the worker process process the court order correctly."""
    identifier = 'BC1234567'
    business = create_entity(identifier, legal_type, 'Test Entity')

    filing = copy.deepcopy(filing_template)

    corrected_filing = factory_completed_filing(business, BEN_CORRECTION_APPLICATION)
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
    identifier = 'BC1234567'
    business = create_entity(identifier, 'BEN', 'Test Entity')
    business_id = business.id

    party = create_party(BEN_CORRECTION['filing']['correction']['parties'][0])
    party_id = party.id

    create_party_role(business, party, ['proprietor'], datetime.utcnow())

    filing = copy.deepcopy(BEN_CORRECTION)

    corrected_filing = factory_completed_filing(business, BEN_CORRECTION_APPLICATION)
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
        'ben_add_partner',
        'ben_edit_partner_name_and_address',
        'ben_delete_partner',
    ]
)
async def test_worker_partner_name_and_address_change(app, session, mocker, test_name):
    """Assert the worker processes the court order correctly."""
    identifier = 'BC1234567'
    business = create_entity(identifier, 'BEN', 'Test Entity')
    business_id = business.id

    party1 = create_party(BEN_CORRECTION['filing']['correction']['parties'][0])
    party_id_1 = party1.id
    party2 = create_party(BEN_CORRECTION['filing']['correction']['parties'][1])
    party_id_2 = party2.id

    create_party_role(business, party1, ['partner'], datetime.utcnow())
    create_party_role(business, party2, ['partner'], datetime.utcnow())

    filing = copy.deepcopy(BEN_CORRECTION)

    corrected_filing = factory_completed_filing(business, BEN_CORRECTION_APPLICATION)
    filing['filing']['correction']['correctedFilingId'] = corrected_filing.id

    filing['filing']['correction']['contactPoint'] = CONTACT_POINT

    if test_name == 'ben_add_partner':
        filing['filing']['correction']['parties'][0]['officer']['id'] = party_id_1
        filing['filing']['correction']['parties'][1]['officer']['id'] = party_id_2
        new_party_json = BEN_CORRECTION['filing']['correction']['parties'][1]
        del new_party_json['officer']['id']
        new_party_json['officer']['firstName'] = 'New Name'
        filing['filing']['correction']['parties'].append(new_party_json)

    if test_name == 'ben_edit_partner_name_and_address':
        filing['filing']['correction']['parties'][0]['officer']['id'] = party_id_1
        filing['filing']['correction']['parties'][0]['officer']['firstName'] = 'New Name a'
        filing['filing']['correction']['parties'][0]['officer']['middleInitial'] = 'New Name a'
        filing['filing']['correction']['parties'][0]['mailingAddress']['streetAddress'] = 'New Name'
        filing['filing']['correction']['parties'][0]['deliveryAddress']['streetAddress'] = 'New Name'
        filing['filing']['correction']['parties'][1]['officer']['id'] = party_id_2

    if test_name == 'ben_delete_partner':
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

    if test_name == 'ben_edit_partner_name_and_address':
        party = business.party_roles.all()[0].party
        assert party.first_name == \
               filing['filing']['correction']['parties'][0]['officer']['firstName'].upper()
        assert party.delivery_address.street == \
               filing['filing']['correction']['parties'][0]['deliveryAddress']['streetAddress']
        assert party.mailing_address.street == \
               filing['filing']['correction']['parties'][0]['mailingAddress']['streetAddress']
        assert business.party_roles.all()[0].cessation_date is None
        assert business.party_roles.all()[1].cessation_date is None

    if test_name == 'ben_delete_partner':
        deleted_role = PartyRole.get_party_roles_by_party_id(business_id, party_id_2)[0]
        assert deleted_role.cessation_date is not None

    if test_name == 'ben_add_partner':
        assert len(PartyRole.get_parties_by_role(business_id, 'partner')) == 2
        assert len(business.party_roles.all()) == 2
        for party_role in business.party_roles.all():
            assert party_role.cessation_date is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'test_name',
    [
        'ben_add_resolution_dates',
        'ben_update_existing_resolution_dates',
        'ben_update_with_new_resolution_dates',
        'ben_delete_resolution_dates',
    ]
)
async def test_worker_resolution_dates_change(app, session, mocker, test_name):
    """Assert the worker processes the court order correctly."""
    identifier = 'BC1234567'
    business = create_entity(identifier, 'BEN', 'Test Entity')
    business_id = business.id

    resolution_dates_json1 = BEN_CORRECTION['filing']['correction']['shareStructure']['resolutionDates'][0]
    resolution_dates_json2 = BEN_CORRECTION['filing']['correction']['shareStructure']['resolutionDates'][1]

    filing = copy.deepcopy(BEN_CORRECTION)

    corrected_filing = factory_completed_filing(business, BEN_CORRECTION_APPLICATION)
    filing['filing']['correction']['correctedFilingId'] = corrected_filing.id

    filing['filing']['correction']['contactPoint'] = CONTACT_POINT

    if test_name == 'ben_add_resolution_dates':
        new_resolution_dates = '2022-09-01'
        filing['filing']['correction']['shareStructure']['resolutionDates'].append(new_resolution_dates)

    if test_name == 'ben_delete_resolution_dates':
        del filing['filing']['correction']['shareStructure']['resolutionDates'][0]

    del filing['filing']['correction']['nameRequest']

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing, business_id=business.id)).id

    if test_name == 'ben_update_existing_resolution_dates' or test_name == 'ben_update_with_new_resolution_dates':
        updated_resolution_dates = '2022-09-01'
        if test_name == 'ben_update_existing_resolution_dates':
            filing['filing']['correction']['shareStructure']['resolutionDates'][1] = updated_resolution_dates
        else:
            filing['filing']['correction']['shareStructure']['resolutionDates'] = [updated_resolution_dates]
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

    resolution_dates = [res.resolution_date for res in business.resolutions.all()]
    if test_name == 'ben_add_resolution_dates':
        assert len(business.resolutions.all()) == 3
        assert resolution_dates[0] == parse(resolution_dates_json1).date()
        assert resolution_dates[1] == parse(resolution_dates_json2).date()
        assert resolution_dates[2] == parse(new_resolution_dates).date()

    if test_name == 'ben_update_existing_resolution_dates':
        assert len(business.share_classes.all()) == 2
        assert parse(resolution_dates_json1).date() in resolution_dates
        assert parse(updated_resolution_dates).date() in resolution_dates
        assert parse(resolution_dates_json2).date() not in resolution_dates

    if test_name == 'ben_update_with_new_resolution_dates':
        assert len(business.resolutions.all()) == 1
        assert parse(updated_resolution_dates).date() in resolution_dates
        assert parse(resolution_dates_json1).date() not in resolution_dates
        assert parse(resolution_dates_json2).date() not in resolution_dates

    if test_name == 'ben_delete_resolution_dates':
        assert len(business.resolutions.all()) == 1
        assert resolution_dates[0] == parse(resolution_dates_json2).date()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'test_name',
    [
        'ben_add_share_class',
        'ben_update_existing_share_class',
        'ben_update_with_new_share_class',
        'ben_delete_share_class',
    ]
)
async def test_worker_share_class_and_series_change(app, session, mocker, test_name):
    """Assert the worker processes the court order correctly."""
    identifier = 'BC1234567'
    business = create_entity(identifier, 'BEN', 'Test Entity')
    business_id = business.id

    share_class_json1 = BEN_CORRECTION['filing']['correction']['shareStructure']['shareClasses'][0]
    share_class_json2 = BEN_CORRECTION['filing']['correction']['shareStructure']['shareClasses'][1]

    filing = copy.deepcopy(BEN_CORRECTION)

    corrected_filing = factory_completed_filing(business, BEN_CORRECTION_APPLICATION)
    filing['filing']['correction']['correctedFilingId'] = corrected_filing.id

    filing['filing']['correction']['contactPoint'] = CONTACT_POINT

    if test_name == 'ben_add_share_class':
        new_share_class_json = BEN_CORRECTION['filing']['correction']['shareStructure']['shareClasses'][1]
        new_share_class_json['id'] = 3
        new_share_class_json['name'] = 'New Share Class'
        filing['filing']['correction']['shareStructure']['shareClasses'].append(new_share_class_json)

    if test_name == 'ben_delete_share_class':
        del filing['filing']['correction']['shareStructure']['shareClasses'][0]

    del filing['filing']['correction']['nameRequest']

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing, business_id=business.id)).id

    if test_name == 'ben_update_existing_share_class' or test_name == 'ben_update_with_new_share_class':
        updated_share_series = [
            {
                'id': 1,
                'name': 'Updated Series 1',
                'priority': 1,
                'hasMaximumShares': True,
                'maxNumberOfShares': 100,
                'hasRightsOrRestrictions': False,
            },
            {
                'id': 2,
                'name': 'Updated Series 2',
                'priority': 2,
                'hasMaximumShares': True,
                'maxNumberOfShares': 200,
                'hasRightsOrRestrictions': False,
            }
        ]
        updated_share_class = {
            'id': share_class_json1['id'],
            'name': 'Updated Share Class',
            'priority': 1,
            'hasMaximumShares': True,
            'maxNumberOfShares': 200,
            'hasParValue': True,
            'parValue': 20,
            'currency': 'CAD',
            'hasRightsOrRestrictions': False,
            'series': updated_share_series
        }
        if test_name == 'ben_update_existing_share_class':
            filing['filing']['correction']['shareStructure']['shareClasses'][0] = updated_share_class
        else:
            filing['filing']['correction']['shareStructure']['shareClasses'] = [updated_share_class]
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

    if test_name == 'ben_add_share_class':
        assert len(business.share_classes.all()) == 3
        assert business.share_classes.all()[0].name == 'Share Class 1'
        assert business.share_classes.all()[1].name == 'Share Class 2'
        assert business.share_classes.all()[2].name == 'New Share Class'

    if test_name == 'ben_update_existing_share_class':
        assert len(business.share_classes.all()) == 2
        assert business.share_classes.all()[0].name == updated_share_class['name']
        assert business.share_classes.all()[0].special_rights_flag == updated_share_class['hasRightsOrRestrictions']
        assert business.share_classes.all()[1].name == share_class_json2['name']
        assert [item.json for item in business.share_classes.all()[1].series] == share_class_json2['series']

    if test_name == 'ben_update_with_new_share_class':
        assert len(business.share_classes.all()) == 1
        assert business.share_classes.all()[0].name == updated_share_class['name']
        assert business.share_classes.all()[0].par_value_flag == updated_share_class['hasParValue']
        assert business.share_classes.all()[0].special_rights_flag == updated_share_class['hasRightsOrRestrictions']
        share_series = [item.json for item in business.share_classes.all()[0].series]
        for key in share_series[0].keys():
            if key != 'id':
                assert share_series[0][key] == updated_share_class['series'][0][key]
                assert share_series[1][key] == updated_share_class['series'][1][key]

    if test_name == 'ben_delete_share_class':
        assert len(business.share_classes.all()) == 1
        assert business.share_classes.all()[0].name == share_class_json2['name']
        assert business.share_classes.all()[0].priority == share_class_json2['priority']
        assert business.share_classes.all()[0].max_shares == share_class_json2['maxNumberOfShares']
        assert business.share_classes.all()[0].par_value == share_class_json2['parValue']
        assert business.share_classes.all()[0].currency == share_class_json2['currency']
        assert [item.json for item in business.share_classes.all()[0].series] == share_class_json2['series']
