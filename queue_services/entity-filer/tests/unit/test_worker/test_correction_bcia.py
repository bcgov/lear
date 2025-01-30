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
from legal_api.models import Address, Alias, Business, Filing, PartyRole
from legal_api.services import NaicsService
from registry_schemas.example_data import (
    COURT_ORDER,
    REGISTRATION,
)

from entity_filer.worker import process_filing
from tests.unit import create_alias, create_entity, create_filing, create_office, create_office_address, create_party, \
    create_party_role, create_share_class, factory_completed_filing

CONTACT_POINT = {
    'email': 'no_one@never.get',
    'phone': '123-456-7890'
}

BC_CORRECTION = {
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
            'nameRequest': {
                'nrNumber': 'NR 8798956',
                'legalName': 'HAULER MEDIA INC.',
                'legalType': 'BEN'
            },
            'nameTranslations': [
                {'id': '1', 'name': 'ABCD Ltd.'},  # Modified translation
                {'name': 'Financire de lOdet'}  # New translation
            ],
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

BC_CORRECTION_SHORT = {
    'filing': {
        'header': {
            'name': 'correction',
            'date': '2025-01-01',
            'certifiedBy': 'system'
        },
        'business': {
            'identifier': 'BC1234567',
            'legalType': 'BC'
        },
        'correction': {
            'details': 'First correction',
            'correctedFilingId': '123456',
            'correctedFilingType': 'incorporationApplication',
            'comment': 'Correction for Incorporation Application filed on 2025-01-01 by system'
        }
    }
}

BC_CORRECTION_APPLICATION = BC_CORRECTION

naics_response = {
    'code': REGISTRATION['business']['naics']['naicsCode'],
    'naicsKey': 'a4667c26-d639-42fa-8af3-7ec73e392569'
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'test_name, legal_name, new_legal_name, legal_type, filing_template',
    [
        ('name_change', 'Test Firm', 'New Name', 'BC', BC_CORRECTION),
        ('no_change', 'Test Firm', None, 'BC', BC_CORRECTION),
        ('name_change', 'Test Firm', 'New Name', 'BEN', BC_CORRECTION),
        ('no_change', 'Test Firm', None, 'BEN', BC_CORRECTION),
        ('name_change', 'Test Firm', 'New Name', 'CC', BC_CORRECTION),
        ('no_change', 'Test Firm', None, 'CC', BC_CORRECTION),
        ('name_change', 'Test Firm', 'New Name', 'ULC', BC_CORRECTION),
        ('no_change', 'Test Firm', None, 'ULC', BC_CORRECTION),
    ]
)
async def test_correction_name_change(app, session, mocker, test_name, legal_name, new_legal_name,
                                      legal_type, filing_template):
    """Assert the worker process calls the legal name change correctly."""

    identifier = 'BC1234567'
    business = create_entity(identifier, legal_type, legal_name)
    business.save()
    business_id = business.id

    filing = copy.deepcopy(filing_template)

    corrected_filing_id = factory_completed_filing(business, BC_CORRECTION_APPLICATION).id
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'test_name, legal_type',
    [
        ('bc_name_translation_change', 'BC'),
        ('ben_name_translation_change', 'BEN'),
        ('cc_name_translation_change', 'CC'),
        ('ulc_name_translation_change', 'ULC'),
    ]
)
async def test_correction_name_translation(app, session, mocker, test_name, legal_type):
    """Assert the worker process calls the business address change correctly."""
    identifier = 'BC1234567'
    business = create_entity(identifier, legal_type, 'HAULER MEDIA INC.')
    business.save()
    business_id = business.id

    filing = copy.deepcopy(BC_CORRECTION)

    alias = create_alias(business, 'ABCD')
    filing['filing']['correction']['nameTranslations'][0]['id'] = str(alias.id)

    corrected_filing_id = factory_completed_filing(business, BC_CORRECTION_APPLICATION).id
    filing['filing']['correction']['correctedFilingId'] = corrected_filing_id
    filing['filing']['correction']['correctedFilingType'] = 'incorporationApplication'

    del filing['filing']['correction']['nameRequest']
    del filing['filing']['correction']['business']
    del filing['filing']['correction']['offices']
    del filing['filing']['correction']['shareStructure']

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

    await process_filing(filing_msg, app)

    aliases = Alias.find_by_type(business.id, Alias.AliasType.TRANSLATION.value)
    assert len(aliases) == 2
    assert all(x for x in aliases if x.alias in [
        filing['filing']['correction']['nameTranslations'][0]['name'],
        filing['filing']['correction']['nameTranslations'][1]['name']
    ])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'test_name, legal_type, legal_name, filing_template',
    [
        ('bc_address_change', 'BC', 'Test Firm', BC_CORRECTION),
        ('ben_address_change', 'BEN', 'Test Firm', BC_CORRECTION),
        ('cc_address_change', 'CC', 'Test Firm', BC_CORRECTION),
        ('ulc_address_change', 'ULC', 'Test Firm', BC_CORRECTION),
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

    corrected_filing_id = factory_completed_filing(business, BC_CORRECTION_APPLICATION).id
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
    for key in ['streetAddress', 'postalCode', 'addressCity', 'addressRegion']:
        assert changed_delivery_address.json[key] == \
            filing['filing']['correction']['offices']['registeredOffice']['deliveryAddress'][key]
    changed_mailing_address = Address.find_by_id(office_mailing_address_id)
    for key in ['streetAddress', 'postalCode', 'addressCity', 'addressRegion']:
        assert changed_mailing_address.json[key] == \
            filing['filing']['correction']['offices']['registeredOffice']['mailingAddress'][key]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'test_name, legal_type, filing_template',
    [
        ('bc_court_order', 'BC', BC_CORRECTION),
        ('ben_court_order', 'BEN', BC_CORRECTION),
        ('cc_court_order', 'CC', BC_CORRECTION),
        ('ulc_court_order', 'ULC', BC_CORRECTION),
    ]
)
async def test_worker_correction_court_order(app, session, mocker, test_name, legal_type, filing_template):
    """Assert the worker process process the court order correctly."""
    identifier = 'BC1234567'
    business = create_entity(identifier, legal_type, 'Test Entity')

    filing = copy.deepcopy(filing_template)

    corrected_filing = factory_completed_filing(business, BC_CORRECTION_APPLICATION)
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
@pytest.mark.parametrize(
    'test_name, legal_type',
    [
        ('bc_add_director', 'BC'),
        ('bc_edit_director_name_and_address', 'BC'),
        ('bc_delete_director', 'BC'),
        ('ben_add_director', 'BEN'),
        ('ben_edit_director_name_and_address', 'BEN'),
        ('ben_delete_director', 'BEN'),
        ('cc_add_director', 'CC'),
        ('cc_edit_director_name_and_address', 'CC'),
        ('cc_delete_director', 'CC'),
        ('ulc_add_director', 'ULC'),
        ('ulc_edit_director_name_and_address', 'ULC'),
        ('ulc_delete_director', 'ULC'),
    ]
)
async def test_worker_director_name_and_address_change(app, session, mocker, test_name, legal_type):
    """Assert the worker processes the court order correctly."""
    identifier = 'BC1234567'
    business = create_entity(identifier, legal_type, 'Test Entity')
    business_id = business.id

    party1 = create_party(BC_CORRECTION['filing']['correction']['parties'][0])
    party_id_1 = party1.id
    party2 = create_party(BC_CORRECTION['filing']['correction']['parties'][1])
    party_id_2 = party2.id

    create_party_role(business, party1, ['director'], datetime.utcnow())
    create_party_role(business, party2, ['director'], datetime.utcnow())

    filing = copy.deepcopy(BC_CORRECTION)

    corrected_filing = factory_completed_filing(business, BC_CORRECTION_APPLICATION)
    filing['filing']['correction']['correctedFilingId'] = corrected_filing.id

    filing['filing']['correction']['contactPoint'] = CONTACT_POINT

    if 'add_director' in test_name:
        filing['filing']['correction']['parties'][0]['officer']['id'] = party_id_1
        filing['filing']['correction']['parties'][1]['officer']['id'] = party_id_2
        new_party_json = copy.deepcopy(BC_CORRECTION['filing']['correction']['parties'][1])
        del new_party_json['officer']['id']
        new_party_json['officer']['firstName'] = 'New Name'
        filing['filing']['correction']['parties'].append(new_party_json)

    if 'edit_director_name_and_address' in test_name:
        filing['filing']['correction']['parties'][0]['officer']['id'] = party_id_1
        filing['filing']['correction']['parties'][0]['officer']['firstName'] = 'New Name a'
        filing['filing']['correction']['parties'][0]['officer']['middleInitial'] = 'New Name a'
        filing['filing']['correction']['parties'][0]['mailingAddress']['streetAddress'] = 'New Name'
        filing['filing']['correction']['parties'][0]['deliveryAddress']['streetAddress'] = 'New Name'
        filing['filing']['correction']['parties'][1]['officer']['id'] = party_id_2

    if 'delete_director' in test_name:
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

    if 'add_director' in test_name:
        assert len(PartyRole.get_parties_by_role(business_id, 'director')) == 2
        assert len(business.party_roles.all()) == 2
        for party_role in business.party_roles.all():
            assert party_role.cessation_date is None

    if 'edit_director_name_and_address' in test_name:
        party = business.party_roles.all()[0].party
        assert party.first_name == \
            filing['filing']['correction']['parties'][0]['officer']['firstName'].upper()
        assert party.delivery_address.street == \
            filing['filing']['correction']['parties'][0]['deliveryAddress']['streetAddress']
        assert party.mailing_address.street == \
            filing['filing']['correction']['parties'][0]['mailingAddress']['streetAddress']
        assert business.party_roles.all()[0].cessation_date is None
        assert business.party_roles.all()[1].cessation_date is None

    if 'delete_director' in test_name:
        deleted_role = PartyRole.get_party_roles_by_party_id(business_id, party_id_2)[0]
        assert deleted_role.cessation_date is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'test_name, legal_type',
    [
        ('bc_add_resolution_dates', 'BC'),
        ('bc_update_existing_resolution_dates', 'BC'),
        ('bc_update_with_new_resolution_dates', 'BC'),
        ('bc_delete_resolution_dates', 'BC'),
        ('bc_delete_all_resolution_dates', 'BC'),
        ('ben_add_resolution_dates', 'BEN'),
        ('ben_update_existing_resolution_dates', 'BEN'),
        ('ben_update_with_new_resolution_dates', 'BEN'),
        ('ben_delete_resolution_dates', 'BEN'),
        ('ben_delete_all_resolution_dates', 'BEN'),
        ('cc_add_resolution_dates', 'CC'),
        ('cc_update_existing_resolution_dates', 'CC'),
        ('cc_update_with_new_resolution_dates', 'CC'),
        ('cc_delete_resolution_dates', 'CC'),
        ('cc_delete_all_resolution_dates', 'CC'),
        ('ulc_add_resolution_dates', 'ULC'),
        ('ulc_update_existing_resolution_dates', 'ULC'),
        ('ulc_update_with_new_resolution_dates', 'ULC'),
        ('ulc_delete_resolution_dates', 'ULC'),
        ('ulc_delete_all_resolution_dates', 'ULC'),
    ]
)
async def test_worker_resolution_dates_change(app, session, mocker, test_name, legal_type):
    """Assert the worker processes the court order correctly."""
    identifier = 'BC1234567'
    business = create_entity(identifier, legal_type, 'Test Entity')
    create_share_class(business, include_resolution_date=True)
    business_id = business.id

    resolution_dates_json1 = BC_CORRECTION['filing']['correction']['shareStructure']['resolutionDates'][0]
    resolution_dates_json2 = BC_CORRECTION['filing']['correction']['shareStructure']['resolutionDates'][1]

    filing = copy.deepcopy(BC_CORRECTION)

    corrected_filing = factory_completed_filing(business, BC_CORRECTION_APPLICATION)
    filing['filing']['correction']['correctedFilingId'] = corrected_filing.id

    filing['filing']['correction']['contactPoint'] = CONTACT_POINT

    existing_resolution_date = business.resolutions[0].resolution_date.strftime('%Y-%m-%d')
    filing['filing']['correction']['shareStructure']['resolutionDates'].insert(0, existing_resolution_date)

    if 'add_resolution_dates' in test_name:
        new_resolution_dates = '2022-09-01'
        filing['filing']['correction']['shareStructure']['resolutionDates'].append(new_resolution_dates)
    elif 'delete_resolution_dates' in test_name:
        del filing['filing']['correction']['shareStructure']['resolutionDates'][0]
    elif 'delete_all_resolution_dates' in test_name:
        filing['filing']['correction']['shareStructure']['resolutionDates'] = []

    del filing['filing']['correction']['nameRequest']

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing, business_id=business.id)).id

    if 'update_existing_resolution_dates' in test_name or 'update_with_new_resolution_dates' in test_name:
        updated_resolution_dates = '2022-09-01'
        if 'update_existing_resolution_dates' in test_name:
            filing['filing']['correction']['shareStructure']['resolutionDates'][0] = updated_resolution_dates
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
    if 'add_resolution_dates' in test_name:
        assert len(resolution_dates) == 4
        assert parse(existing_resolution_date).date() in resolution_dates
        assert parse(resolution_dates_json1).date() in resolution_dates
        assert parse(resolution_dates_json2).date() in resolution_dates
        assert parse(new_resolution_dates).date() in resolution_dates

    elif 'update_existing_resolution_dates' in test_name:
        assert len(resolution_dates) == 3
        assert parse(resolution_dates_json1).date() in resolution_dates
        assert parse(updated_resolution_dates).date() in resolution_dates
        assert parse(existing_resolution_date).date() not in resolution_dates

    elif 'update_with_new_resolution_dates' in test_name:
        assert len(resolution_dates) == 1
        assert parse(updated_resolution_dates).date() in resolution_dates
        assert parse(resolution_dates_json1).date() not in resolution_dates
        assert parse(resolution_dates_json2).date() not in resolution_dates

    elif 'delete_resolution_dates' in test_name:
        assert len(resolution_dates) == 2
        assert parse(resolution_dates_json1).date() in resolution_dates
        assert parse(resolution_dates_json2).date() in resolution_dates

    elif 'delete_all_resolution_dates' in test_name:
        assert len(resolution_dates) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'test_name, legal_type',
    [
        ('bc_add_share_class', 'BC'),
        ('bc_update_existing_share_class', 'BC'),
        ('bc_update_with_new_share_class', 'BC'),
        ('bc_delete_share_class', 'BC'),
        ('ben_add_share_class', 'BEN'),
        ('ben_update_existing_share_class', 'BEN'),
        ('ben_update_with_new_share_class', 'BEN'),
        ('ben_delete_share_class', 'BEN'),
        ('cc_add_share_class', 'CC'),
        ('cc_update_existing_share_class', 'CC'),
        ('cc_update_with_new_share_class', 'CC'),
        ('cc_delete_share_class', 'CC'),
        ('ulc_add_share_class', 'ULC'),
        ('ulc_update_existing_share_class', 'ULC'),
        ('ulc_update_with_new_share_class', 'ULC'),
        ('ulc_delete_share_class', 'ULC'),
    ]
)
async def test_worker_share_class_and_series_change(app, session, mocker, test_name, legal_type):
    """Assert the worker processes the court order correctly."""
    identifier = 'BC1234567'
    business = create_entity(identifier, legal_type, 'Test Entity')
    create_share_class(business)
    business_id = business.id

    share_class_json1 = BC_CORRECTION['filing']['correction']['shareStructure']['shareClasses'][0]
    share_class_json2 = BC_CORRECTION['filing']['correction']['shareStructure']['shareClasses'][1]

    filing = copy.deepcopy(BC_CORRECTION)
    del filing['filing']['correction']['shareStructure']['shareClasses'][0]['id']
    existing_share_class = business.share_classes[0]
    filing['filing']['correction']['shareStructure']['shareClasses'].insert(0, existing_share_class.json)

    corrected_filing = factory_completed_filing(business, BC_CORRECTION_APPLICATION)
    filing['filing']['correction']['correctedFilingId'] = corrected_filing.id

    filing['filing']['correction']['contactPoint'] = CONTACT_POINT

    if 'add_share_class' in test_name:
        new_share_class_json = copy.deepcopy(BC_CORRECTION['filing']['correction']['shareStructure']['shareClasses'][1])
        del new_share_class_json['id']
        new_share_class_json['name'] = 'New Share Class'
        filing['filing']['correction']['shareStructure']['shareClasses'].append(new_share_class_json)

    if 'delete_share_class' in test_name:
        del filing['filing']['correction']['shareStructure']['shareClasses'][0]
        del filing['filing']['correction']['shareStructure']['shareClasses'][0]

    del filing['filing']['correction']['nameRequest']

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing, business_id=business.id)).id

    if 'update_existing_share_class' in test_name or 'update_with_new_share_class' in test_name:
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
            'id': existing_share_class.id,
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
        if 'update_existing_share_class' in test_name:
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

    if 'add_share_class' in test_name:
        assert len(business.share_classes.all()) == 4
        assert business.share_classes.all()[1].name == 'Share Class 1'
        assert business.share_classes.all()[2].name == 'Share Class 2'
        assert business.share_classes.all()[3].name == 'New Share Class'

    if 'update_existing_share_class' in test_name:
        assert len(business.share_classes.all()) == 3
        assert business.share_classes.all()[0].name == updated_share_class['name']
        assert business.share_classes.all()[0].special_rights_flag == updated_share_class['hasRightsOrRestrictions']
        assert business.share_classes.all()[1].name == share_class_json1['name']
        assert business.share_classes.all()[2].name == share_class_json2['name']

    if 'update_with_new_share_class' in test_name:
        assert len(business.share_classes.all()) == 1
        assert business.share_classes.all()[0].name == updated_share_class['name']
        assert business.share_classes.all()[0].par_value_flag == updated_share_class['hasParValue']
        assert business.share_classes.all()[0].special_rights_flag == updated_share_class['hasRightsOrRestrictions']
        share_series = [item.json for item in business.share_classes.all()[0].series]
        for key in share_series[0].keys():
            if key != 'id':
                assert share_series[0][key] == updated_share_class['series'][0][key]
                assert share_series[1][key] == updated_share_class['series'][1][key]

    if 'delete_share_class' in test_name:
        assert len(business.share_classes.all()) == 1
        assert business.share_classes.all()[0].name == share_class_json2['name']
        assert business.share_classes.all()[0].priority == share_class_json2['priority']
        assert business.share_classes.all()[0].max_shares == share_class_json2['maxNumberOfShares']
        assert business.share_classes.all()[0].par_value == share_class_json2['parValue']
        assert business.share_classes.all()[0].currency == share_class_json2['currency']
        assert [item.json for item in business.share_classes.all()[0].series] == share_class_json2['series']
        

async def test_correction_ben_statement(app, session, mocker):
    """Assert the worker process calls the BEN correction statement correctly."""
    
    identifier = 'BC1234567'
    business = create_entity(identifier, 'BEN', 'ABC test inc.')
    business.save()
    business_id = business.id

    filing = copy.deepcopy(BC_CORRECTION_SHORT)
    
    corrected_filing_id = factory_completed_filing(business, BC_CORRECTION_SHORT).id
    filing['filing']['correction']['correctedFilingId'] = corrected_filing_id
    
    payment_id = str(random.SystemRandom().getrandbits(0x58))

    filing_id = (create_filing(payment_id, filing, business_id=business_id)).id
    filing_msg = {'filing': {'id': filing_id}}
    
    # mock out the email sender and event publishing
    mocker.patch('entity_filer.worker.publish_event', return_value=None)
    mocker.patch('entity_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)
    mocker.patch('entity_filer.filing_processors.filing_components.business_profile.update_business_profile',
                 return_value=None)
    mocker.patch('legal_api.services.bootstrap.AccountService.update_entity', return_value=None)

    await process_filing(filing_msg, app)
    
    final_filing = Filing.find_by_id(filing_id)

    filing_comments = final_filing.comments.all()
    assert len(filing_comments) == 1
    assert filing_comments[0].comment == filing['filing']['correction']['comment']
