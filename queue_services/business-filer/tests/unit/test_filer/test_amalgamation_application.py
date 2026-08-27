# Copyright © 2024 Province of British Columbia
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
"""The Unit Tests for the Amalgamation application filing."""

import copy
import random
from datetime import datetime, timezone, timezone
from http import HTTPStatus
from unittest.mock import patch

import pytest
from business_model.models import AmalgamatingBusiness, Amalgamation, Business, Filing
from registry_schemas.example_data import AMALGAMATION_APPLICATION

from business_filer.common.filing_message import FilingMessage
from business_filer.exceptions import QueueException
from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import amalgamation_application
from business_filer.filing_processors.filing_components import business_info, business_profile
from business_filer.services.filer import process_filing
from tests.unit import (
    create_entity,
    create_filing,
    create_office,
    create_office_address,
    create_party,
    create_party_role,
    create_share_class,
)


def test_regular_amalgamation_application_process(app, session, set_publish_mocks):
    """Assert that the amalgamation application object is correctly populated to model objects."""
    filing_type = 'amalgamationApplication'
    amalgamating_identifier_1 = f'BC{random.randint(1000000, 9999999)}'
    amalgamating_identifier_2 = f'BC{random.randint(1000000, 9999999)}'
    nr_identifier = f'NR {random.randint(1000000, 9999999)}'
    next_corp_num = f'BC{random.randint(1000000, 9999999)}'

    amalgamating_business_1_id = create_entity(amalgamating_identifier_1, 'BC', 'amalgamating business 1').id
    amalgamating_business_2_id = create_entity(amalgamating_identifier_2, 'BC', 'amalgamating business 2').id

    filing = {'filing': {}}
    filing['filing']['header'] = {'name': filing_type, 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing'][filing_type] = copy.deepcopy(AMALGAMATION_APPLICATION)
    del filing['filing'][filing_type]['amalgamatingBusinesses'][0]
    filing['filing'][filing_type]['amalgamatingBusinesses'] = [
        {
            'role': AmalgamatingBusiness.Role.amalgamating.name,
            'identifier': amalgamating_identifier_1
        },
        {
            'role': AmalgamatingBusiness.Role.amalgamating.name,
            'identifier': amalgamating_identifier_2
        }
    ]

    filing['filing'][filing_type]['nameRequest']['nrNumber'] = nr_identifier

    filing_rec = create_filing('123', filing)
    effective_date = datetime.now(timezone.utc)
    filing_rec.effective_date = effective_date
    filing_rec.save()

    # test
    filing_msg = FilingMessage(filing_identifier=filing_rec.id)
    # mocker.patch('business_filer.services.publish_event.PublishEvent.publish_mras_email', return_value=None)
    # mocker.patch('business_filer.services.publish_event.PublishEvent.publish_email_message', return_value=None)
    with patch.object(business_info, 'get_next_corp_num', return_value=next_corp_num):
        with patch.object(business_profile, 'update_business_profile', return_value=HTTPStatus.OK):
            process_filing(filing_msg)

    # Assertions
    filing_rec = Filing.find_by_id(filing_rec.id)
    business = Business.find_by_identifier(next_corp_num)

    court_order_obj = filing_rec.court_orders[0]
    court_order = filing['filing'][filing_type]['courtOrder']
    assert business.id == court_order_obj.business_id
    assert court_order['orderDetails'] == court_order_obj.order_details
    assert court_order['fileNumber'] == court_order_obj.file_number
    assert court_order['effectOfOrder'] == court_order_obj.effect_of_order
    assert filing_rec.meta_data.get('courtOrder')['fileNumber'] == court_order_obj.file_number
    assert filing_rec.meta_data.get('courtOrder')['effectOfOrder'] == court_order_obj.effect_of_order

    assert filing_rec.business_id == business.id
    assert filing_rec.status == Filing.Status.COMPLETED.value
    assert business.identifier
    assert business.founding_date == effective_date
    assert business.legal_type == filing['filing'][filing_type]['nameRequest']['legalType']
    assert business.legal_name == filing['filing'][filing_type]['nameRequest']['legalName']
    assert business.state == Business.State.ACTIVE

    assert len(business.share_classes.all()) == len(filing['filing'][filing_type]['shareStructure']['shareClasses'])
    assert len(business.offices.all()) == len(filing['filing'][filing_type]['offices'])
    assert len(business.aliases.all()) == len(filing['filing'][filing_type]['nameTranslations'])
    assert business.party_roles[0].role == 'director'
    assert filing_rec.filing_party_roles[0].role == 'completing_party'

    assert business.amalgamation
    amalgamation: Amalgamation = business.amalgamation[0]
    assert amalgamation.amalgamation_date == effective_date
    assert amalgamation.filing_id == filing_rec.id
    assert amalgamation.amalgamation_type.name == filing['filing'][filing_type]['type']
    assert amalgamation.court_approval == filing['filing'][filing_type]['courtApproval']

    for amalgamating_business in amalgamation.amalgamating_businesses:
        assert amalgamating_business.role.name == AmalgamatingBusiness.Role.amalgamating.name
        if amalgamating_business.business_id:
            assert amalgamating_business.business_id in [amalgamating_business_1_id, amalgamating_business_2_id]
            dissolved_business = Business.find_by_internal_id(amalgamating_business.business_id)
            assert dissolved_business.state == Business.State.HISTORICAL
            assert dissolved_business.state_filing_id == filing_rec.id
            assert dissolved_business.dissolution_date == effective_date
        else:
            assert amalgamating_business.foreign_jurisdiction
            assert amalgamating_business.foreign_jurisdiction_region
            assert amalgamating_business.foreign_name
            assert amalgamating_business.foreign_identifier

    return next_corp_num


@pytest.mark.parametrize(
    'amalgamation_type, amalgamating_role',
    [
        (Amalgamation.AmalgamationTypes.horizontal.name, AmalgamatingBusiness.Role.primary.name),
        (Amalgamation.AmalgamationTypes.vertical.name, AmalgamatingBusiness.Role.holding.name)
    ]
)
def test_short_form_amalgamation_application_process(app, session, amalgamation_type, amalgamating_role):
    """Assert a short-form amalgamation is applied from the filing json, not the primary/holding DB rows."""
    filing_type = 'amalgamationApplication'
    amalgamating_identifier_1 = f'BC{random.randint(1000000, 9999999)}'
    amalgamating_identifier_2 = f'BC{random.randint(1000000, 9999999)}'
    next_corp_num = f'BC{random.randint(1000000, 9999999)}'
    primary_or_holding_business_name = f'{amalgamating_role} business 1'

    amalgamating_business_1 = create_entity(amalgamating_identifier_1, 'BC', primary_or_holding_business_name)

    office = create_office(amalgamating_business_1, 'registeredOffice')
    office_delivery_address = create_office_address(amalgamating_business_1, office, 'delivery')
    office_mailing_address = create_office_address(amalgamating_business_1, office, 'mailing')

    create_share_class(amalgamating_business_1, include_resolution_date=True)

    party = create_party({
        'officer': {
            'firstName': f'{amalgamating_business_1.identifier} first_name',
            'lastName': 'Director',
            'middleName': 'P',
        },
        'mailingAddress': {
            'streetAddress': f'{amalgamating_business_1.identifier} mailing_address',
            'addressCity': 'mailing_address city',
            'addressCountry': 'CA',
            'postalCode': 'H0H0H0',
            'addressRegion': 'BC'
        },
        'deliveryAddress': {
            'streetAddress': f'{amalgamating_business_1.identifier} delivery_address',
            'addressCity': 'delivery_address city',
            'addressCountry': 'CA',
            'postalCode': 'H0H0H0',
            'addressRegion': 'BC'
        }
    })
    create_party_role(amalgamating_business_1, party, ['director'], datetime.now(timezone.utc))

    amalgamating_business_1_id = amalgamating_business_1.id
    amalgamating_business_2_id = create_entity(amalgamating_identifier_2, 'BC', 'amalgamating business 2').id

    filing = {'filing': {}}
    filing['filing']['header'] = {'name': filing_type, 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing'][filing_type] = copy.deepcopy(AMALGAMATION_APPLICATION)
    filing['filing'][filing_type]['type'] = amalgamation_type
    del filing['filing'][filing_type]['amalgamatingBusinesses'][0]
    filing['filing'][filing_type]['amalgamatingBusinesses'] = [
        {
            'role': amalgamating_role,
            'identifier': amalgamating_identifier_1
        },
        {
            'role': AmalgamatingBusiness.Role.amalgamating.name,
            'identifier': amalgamating_identifier_2
        }
    ]

    # the template's offices/parties/shareStructure differ from the DB
    # to prove the primary/holding business is read from the filing json
    filing['filing'][filing_type]['nameRequest']['legalName'] = primary_or_holding_business_name
    filing['filing'][filing_type]['shareStructure']['resolutionDates'] = ['2020-05-13']

    filing_rec = create_filing('123', filing)
    effective_date = datetime.now(timezone.utc)
    filing_rec.effective_date = effective_date
    filing_rec.save()

    # test
    filing_msg = FilingMessage(filing_identifier=filing_rec.id)
    with patch.object(business_info, 'get_next_corp_num', return_value=next_corp_num):
        with patch.object(business_profile, 'update_business_profile', return_value=HTTPStatus.OK):
            process_filing(filing_msg)

    # Assertions
    filing_rec = Filing.find_by_id(filing_rec.id)
    business = Business.find_by_identifier(next_corp_num)

    assert filing_rec.business_id == business.id
    assert filing_rec.status == Filing.Status.COMPLETED.value
    assert business.identifier
    assert business.founding_date == effective_date
    assert business.legal_type == filing['filing'][filing_type]['nameRequest']['legalType']
    assert business.legal_name == primary_or_holding_business_name
    assert business.state == Business.State.ACTIVE

    # applied from the filing json (2 template share classes / 2 template offices),
    # not copied from the primary/holding business's rows (1 share class / 1 office)
    assert len(business.share_classes.all()) == len(filing['filing'][filing_type]['shareStructure']['shareClasses'])
    assert len(business.resolutions.all()) == 1
    assert len(business.offices.all()) == len(filing['filing'][filing_type]['offices'])
    assert len(business.aliases.all()) == len(filing['filing'][filing_type]['nameTranslations'])
    assert business.party_roles[0].role == 'director'
    assert filing_rec.filing_party_roles[0].role == 'completing_party'

    assert business.amalgamation
    amalgamation: Amalgamation = business.amalgamation[0]
    assert amalgamation.amalgamation_date == effective_date
    assert amalgamation.filing_id == filing_rec.id
    assert amalgamation.amalgamation_type.name == filing['filing'][filing_type]['type']
    assert amalgamation.court_approval == filing['filing'][filing_type]['courtApproval']

    for amalgamating_business in amalgamation.amalgamating_businesses:
        assert amalgamating_business.role.name in [amalgamating_role, AmalgamatingBusiness.Role.amalgamating.name]
        if amalgamating_business.business_id:
            assert amalgamating_business.business_id in [amalgamating_business_1_id, amalgamating_business_2_id]
            dissolved_business = Business.find_by_internal_id(amalgamating_business.business_id)
            assert dissolved_business.state == Business.State.HISTORICAL
            assert dissolved_business.state_filing_id == filing_rec.id
            assert dissolved_business.dissolution_date == effective_date
        else:
            assert amalgamating_business.foreign_jurisdiction
            assert amalgamating_business.foreign_jurisdiction_region
            assert amalgamating_business.foreign_name
            assert amalgamating_business.foreign_identifier


def _short_form_filing(amalgamating_businesses: list) -> dict:
    """Return a vertical amalgamation filing carrying the template's adopted data sections."""
    filing_type = 'amalgamationApplication'
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': filing_type, 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing'][filing_type] = copy.deepcopy(AMALGAMATION_APPLICATION)
    filing['filing'][filing_type]['type'] = Amalgamation.AmalgamationTypes.vertical.name
    filing['filing'][filing_type]['amalgamatingBusinesses'] = amalgamating_businesses
    return filing


@pytest.mark.parametrize('missing_section', ['offices', 'parties', 'shareStructure', 'legalName'])
def test_short_form_amalgamation_missing_sections(app, session, missing_section):
    """Assert a short-form filing without the adopted data sections fails loudly."""
    filing_type = 'amalgamationApplication'
    holding_identifier = f'BC{random.randint(1000000, 9999999)}'
    amalgamating_identifier = f'BC{random.randint(1000000, 9999999)}'
    next_corp_num = f'BC{random.randint(1000000, 9999999)}'

    create_entity(holding_identifier, 'BC', 'holding business')
    create_entity(amalgamating_identifier, 'BC', 'amalgamating business')

    filing = _short_form_filing([
        {'role': AmalgamatingBusiness.Role.holding.name, 'identifier': holding_identifier},
        {'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': amalgamating_identifier}
    ])
    if missing_section == 'legalName':
        del filing['filing'][filing_type]['nameRequest']['legalName']
    else:
        del filing['filing'][filing_type][missing_section]

    filing_rec = create_filing('123', filing)
    filing_rec.effective_date = datetime.now(timezone.utc)
    filing_rec.save()

    with patch.object(business_info, 'get_next_corp_num', return_value=next_corp_num):
        with pytest.raises(QueueException) as excinfo:
            amalgamation_application.process(None, filing, filing_rec, FilingMeta())
    assert 'short-form filing missing' in excinfo.value.error


@pytest.mark.parametrize('colin_identifier_prefix', [
    'BC',  # a BC corp in COLIN not yet loaded in LEAR
    'A',  # an extraprovincial company (identifier-only entry, same path)
])
def test_colin_amalgamating_business(app, session, colin_identifier_prefix):
    """Assert a COLIN business (not loaded in LEAR) is persisted by identifier and not dissolved."""
    filing_type = 'amalgamationApplication'
    amalgamating_identifier = f'BC{random.randint(1000000, 9999999)}'
    colin_identifier = f'{colin_identifier_prefix}{random.randint(1000000, 9999999)}'
    next_corp_num = f'BC{random.randint(1000000, 9999999)}'

    amalgamating_business_id = create_entity(amalgamating_identifier, 'BC', 'amalgamating business').id

    filing = {'filing': {}}
    filing['filing']['header'] = {'name': filing_type, 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing'][filing_type] = copy.deepcopy(AMALGAMATION_APPLICATION)
    filing['filing'][filing_type]['amalgamatingBusinesses'] = [
        {'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': amalgamating_identifier},
        {'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': colin_identifier}
    ]

    filing_rec = create_filing('123', filing)
    effective_date = datetime.now(timezone.utc)
    filing_rec.effective_date = effective_date
    filing_rec.save()

    filing_msg = FilingMessage(filing_identifier=filing_rec.id)
    with patch.object(business_info, 'get_next_corp_num', return_value=next_corp_num):
        with patch.object(business_profile, 'update_business_profile', return_value=HTTPStatus.OK):
            process_filing(filing_msg)

    filing_rec = Filing.find_by_id(filing_rec.id)
    business = Business.find_by_identifier(next_corp_num)
    assert filing_rec.status == Filing.Status.COMPLETED.value
    assert business

    amalgamation: Amalgamation = business.amalgamation[0]
    colin_row = next(x for x in amalgamation.amalgamating_businesses if x.colin_identifier)
    assert colin_row.colin_identifier == colin_identifier
    assert colin_row.business_id is None
    assert colin_row.foreign_identifier is None
    assert colin_row.foreign_jurisdiction is None
    assert colin_row.foreign_name is None

    lear_row = next(x for x in amalgamation.amalgamating_businesses if x.business_id)
    assert lear_row.business_id == amalgamating_business_id
    dissolved_business = Business.find_by_internal_id(amalgamating_business_id)
    assert dissolved_business.state == Business.State.HISTORICAL


def test_colin_holding_short_form_amalgamation(app, session):
    """Assert a short-form amalgamation with a COLIN holding business processes from the filing json."""
    filing_type = 'amalgamationApplication'
    colin_holding_identifier = f'BC{random.randint(1000000, 9999999)}'
    amalgamating_identifier = f'BC{random.randint(1000000, 9999999)}'
    next_corp_num = f'BC{random.randint(1000000, 9999999)}'
    adopted_name = 'Colin Holding Business Ltd.'

    create_entity(amalgamating_identifier, 'BC', 'amalgamating business')

    filing = _short_form_filing([
        {'role': AmalgamatingBusiness.Role.holding.name, 'identifier': colin_holding_identifier},
        {'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': amalgamating_identifier}
    ])
    filing['filing'][filing_type]['nameRequest']['legalName'] = adopted_name

    filing_rec = create_filing('123', filing)
    filing_rec.effective_date = datetime.now(timezone.utc)
    filing_rec.save()

    filing_msg = FilingMessage(filing_identifier=filing_rec.id)
    with patch.object(business_info, 'get_next_corp_num', return_value=next_corp_num):
        with patch.object(business_profile, 'update_business_profile', return_value=HTTPStatus.OK):
            process_filing(filing_msg)

    filing_rec = Filing.find_by_id(filing_rec.id)
    business = Business.find_by_identifier(next_corp_num)
    assert filing_rec.status == Filing.Status.COMPLETED.value
    assert business.legal_name == adopted_name
    assert len(business.share_classes.all()) == len(filing['filing'][filing_type]['shareStructure']['shareClasses'])
    assert len(business.offices.all()) == len(filing['filing'][filing_type]['offices'])

    amalgamation: Amalgamation = business.amalgamation[0]
    holding_row = next(x for x in amalgamation.amalgamating_businesses
                       if x.role.name == AmalgamatingBusiness.Role.holding.name)
    assert holding_row.colin_identifier == colin_holding_identifier
    assert holding_row.business_id is None


def test_amalgamating_business_without_identifier(app, session):
    """Assert an amalgamating business with no identifier and no foreign jurisdiction fails loudly."""
    filing_type = 'amalgamationApplication'
    next_corp_num = f'BC{random.randint(1000000, 9999999)}'

    filing = {'filing': {}}
    filing['filing']['header'] = {'name': filing_type, 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing'][filing_type] = copy.deepcopy(AMALGAMATION_APPLICATION)
    filing['filing'][filing_type]['amalgamatingBusinesses'] = [
        {'role': AmalgamatingBusiness.Role.amalgamating.name}
    ]

    filing_rec = create_filing('123', filing)
    filing_rec.effective_date = datetime.now(timezone.utc)
    filing_rec.save()

    with patch.object(business_info, 'get_next_corp_num', return_value=next_corp_num):
        with pytest.raises(QueueException) as excinfo:
            amalgamation_application.process(None, filing, filing_rec, FilingMeta())
    assert 'no identifier' in excinfo.value.error
