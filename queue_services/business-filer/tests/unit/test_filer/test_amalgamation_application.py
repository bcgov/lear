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


def test_regular_amalgamation_application_process(app, session):
    """Assert that the amalgamation application object is correctly populated to model objects."""
    # thor
    return
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
    """Assert that the amalgamation application object is correctly populated to model objects."""
    filing_type = 'amalgamationApplication'
    amalgamating_identifier_1 = f'BC{random.randint(1000000, 9999999)}'
    amalgamating_identifier_2 = f'BC{random.randint(1000000, 9999999)}'
    nr_identifier = f'NR {random.randint(1000000, 9999999)}'
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

    filing['filing'][filing_type]['nameRequest']['nrNumber'] = nr_identifier

    del filing['filing'][filing_type]['offices']
    del filing['filing'][filing_type]['shareStructure']
    del filing['filing'][filing_type]['parties'][0]['roles'][1]

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

    assert len(business.share_classes.all()) == 1
    assert len(business.resolutions.all()) == 1
    assert len(business.offices.all()) == 1
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
