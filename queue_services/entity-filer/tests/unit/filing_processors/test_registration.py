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
"""The Unit Tests for the Registration filing."""

import copy
from datetime import datetime
from http import HTTPStatus
from unittest.mock import patch, call

import pytest
from business_model import LegalEntity, Filing, RegistrationBootstrap
# from legal_api.services import NaicsService
from registry_schemas.example_data import (
    FILING_HEADER,
    REGISTRATION
)

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors import registration
from tests.unit import create_filing, nested_session

from entity_filer.filing_processors.filing_components.legal_entity_info import NaicsService

now = '2023-01-08'

GP_REGISTRATION = copy.deepcopy(FILING_HEADER)
GP_REGISTRATION['filing']['header']['name'] = 'registration'
GP_REGISTRATION['filing']['registration'] = copy.deepcopy(REGISTRATION)
GP_REGISTRATION['filing']['registration']['startDate'] = now

SP_REGISTRATION = copy.deepcopy(FILING_HEADER)
SP_REGISTRATION['filing']['header']['name'] = 'registration'
SP_REGISTRATION['filing']['registration'] = copy.deepcopy(REGISTRATION)
SP_REGISTRATION['filing']['registration']['startDate'] = now
SP_REGISTRATION['filing']['registration']['nameRequest']['legalType'] = 'SP'
SP_REGISTRATION['filing']['registration']['businessType'] = 'SP'
SP_REGISTRATION['filing']['registration']['parties'][0]['roles'] = [
    {
        'roleType': 'Completing Party',
        'appointmentDate': '2022-01-01'

    },
    {
        'roleType': 'Proprietor',
        'appointmentDate': '2022-01-01'

    }
]
del SP_REGISTRATION['filing']['registration']['parties'][1]


@pytest.mark.parametrize('legal_type,filing', [
    # ('SP', copy.deepcopy(SP_REGISTRATION)),
    ('GP', copy.deepcopy(GP_REGISTRATION)),
])
def test_registration_process(app, session, legal_type, filing):
    """Assert that the registration object is correctly populated to model objects."""
    # setup
    with nested_session(session):
        identifier = 'NR 1234567'
        filing['filing']['registration']['nameRequest']['nrNumber'] = identifier
        filing['filing']['registration']['nameRequest']['legalName'] = 'Test'

        create_filing('123', filing)

        effective_date = datetime.utcnow()
        filing_rec = Filing(effective_date=effective_date, filing_json=filing)
        filing_meta = FilingMeta(application_date=effective_date)

        naics_response = {
            'code': REGISTRATION['business']['naics']['naicsCode'],
            'naicsKey': 'a4667c26-d639-42fa-8af3-7ec73e392569'
        }

        # test
        with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
            business, filing_rec, filing_meta = registration.process(None, filing, filing_rec, filing_meta)

        # Assertions
        # Legal Entity
        assert business.identifier.startswith('FM')
        assert business.founding_date == effective_date
        assert business.start_date == datetime.fromisoformat(f'{now}T08:00:00+00:00')
        assert business.entity_type == filing['filing']['registration']['nameRequest']['legalType']
        assert business.tax_id == REGISTRATION['business']['taxId']
        assert business.state == LegalEntity.State.ACTIVE
        assert len(filing_rec.filing_entity_roles.all()) == 3
        assert len(business.entity_roles.all()) == 0
        assert len(business.offices.all()) == 1
        assert business.offices[0].office_type == 'businessOffice'
        # TODO Check if deisplay and sorting are the same, or should be differnet here
        assert business.legal_name == 'Griffin Peter, Swanson Joe P'.upper()

        # NAICS
        assert business.naics_code == REGISTRATION['business']['naics']['naicsCode']
        assert business.naics_description == REGISTRATION['business']['naics']['naicsDescription']

        # AlternateNames
        assert len(business.alternate_names.all()) > 0
        alternate_name = business.alternate_names[0]
        assert alternate_name.identifier.startswith('FM')
        assert alternate_name.name == filing['filing']['registration']['nameRequest']['legalName']


@pytest.mark.parametrize('legal_type,filing', [
    ('SP', copy.deepcopy(SP_REGISTRATION)),
])
def test_sp_registration_process(app, session, legal_type, filing):
    """Assert that the registration object is correctly populated to model objects."""
    # setup
    with nested_session(session):
        nr_num = 'NR 1234567'
        filing['filing']['registration']['nameRequest']['nrNumber'] = nr_num
        filing['filing']['registration']['nameRequest']['legalName'] = 'Test'
        if legal_type == 'SP':
            del SP_REGISTRATION['filing']['registration']['parties'][0]['officer']['id']

        create_filing('123', filing)

        effective_date = datetime.utcnow()
        filing_rec = Filing(effective_date=effective_date, filing_json=filing)
        filing_meta = FilingMeta(application_date=effective_date)

        naics_response = {
            'code': REGISTRATION['business']['naics']['naicsCode'],
            'naicsKey': 'a4667c26-d639-42fa-8af3-7ec73e392569'
        }

        # test
        with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
            business, filing_rec, filing_meta = registration.process(None, filing, filing_rec, filing_meta)

        # Assertions
        # assert business.founding_date.replace(tzinfo=None) == effective_date
        assert business.entity_type == LegalEntity.EntityTypes.PERSON
        assert business.identifier.startswith('P')

        alternate_name = business.alternate_names.all()[0]
        assert alternate_name.start_date == datetime.fromisoformat(f'{now}T08:00:00+00:00')
        assert alternate_name.identifier.startswith('FM')

        assert alternate_name.name == filing['filing']['registration']['nameRequest']['legalName']
        # TODO I don't think it makes sens to be changing or setting
        # a natural person's NAICS codes. Maybe this is an Alias/DBA thing
        # assert business.naics_code == REGISTRATION['business']['naics']['naicsCode']
        # assert business.naics_description == REGISTRATION['business']['naics']['naicsDescription']
        # assert business.naics_key == naics_response['naicsKey']
        assert business.tax_id == REGISTRATION['business']['taxId']
        assert business.state == LegalEntity.State.ACTIVE
        
        
        if legal_type == 'SP':
            assert len(filing_rec.filing_entity_roles.all()) == 1
            assert len(business.entity_roles.all()) == 0
        if legal_type == 'GP':
            assert len(filing_rec.filing_entity_roles.all()) == 3
            assert len(business.entity_roles.all()) == 0
