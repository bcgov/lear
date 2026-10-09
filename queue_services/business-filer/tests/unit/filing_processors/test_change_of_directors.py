# Copyright © 2026 Province of British Columbia
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
"""The Unit Tests for the Change of Directors filing."""
import copy
import random
from datetime import datetime, timezone

import pytest
from business_model.models import Address, Business, Filing, Party, PartyRole
from registry_schemas.example_data import FILING_TEMPLATE

from business_filer.exceptions import QueueException
from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import change_of_directors
from business_filer.filing_processors.filing_components import create_address
from tests.unit import create_business, create_filing

effective_date = datetime(2023, 10, 10, 10, 0, 0, tzinfo=timezone.utc)

DELIVERY_ADDRESS = {
    'streetAddress': 'delivery_address - address line one',
    'addressCity': 'delivery_address city',
    'addressCountry': 'CA',
    'postalCode': 'H0H0H0',
    'addressRegion': 'BC'
}

MAILING_ADDRESS = {
    'streetAddress': 'mailing_address - address line one',
    'addressCity': 'mailing_address city',
    'addressCountry': 'CA',
    'postalCode': 'H0H0H0',
    'addressRegion': 'BC'
}


def _relationship(first_name, last_name, identifier=None, actions=None,
                  appointment_date='2023-01-01', cessation_date=None):
    relationship = {
        'entity': {
            'givenName': first_name,
            'familyName': last_name
        },
        'deliveryAddress': copy.deepcopy(DELIVERY_ADDRESS),
        'mailingAddress': copy.deepcopy(MAILING_ADDRESS),
        'roles': [
            {
                'roleType': 'Director',
                'appointmentDate': appointment_date,
                'cessationDate': cessation_date
            }
        ]
    }
    if identifier:
        relationship['entity']['identifier'] = str(identifier)
    if actions is not None:
        relationship['actions'] = actions
    return relationship


def _active_directors(business_id):
    return [role for role in PartyRole.get_parties_by_role(business_id, PartyRole.RoleTypes.DIRECTOR.value)
            if role.cessation_date is None]


@pytest.fixture
def business(session):
    identifier = f'BC{random.randint(1000000, 9999999)}'
    return create_business(identifier, legal_type='BEN')


@pytest.fixture
def filing_factory(session, business: Business):
    def _factory(payload: dict) -> Filing:
        filing = copy.deepcopy(FILING_TEMPLATE)
        filing['filing']['header']['name'] = 'changeOfDirectors'
        filing['filing']['header']['effectiveDate'] = effective_date.isoformat()
        filing['filing']['business']['identifier'] = business.identifier
        filing['filing']['business']['legalType'] = business.legal_type
        filing['filing']['changeOfDirectors'] = payload

        filing_rec = create_filing('123', filing, business.id)
        filing_rec.effective_date = effective_date
        filing_rec.save()
        return filing_rec
    return _factory


@pytest.fixture
def existing_director(session, business: Business):
    party = Party(first_name='CAROL', last_name='PILBASIAN')
    party.delivery_address = create_address(
        {
            'streetAddress': 'Old Street',
            'addressCity': 'Old City',
            'addressCountry': 'CA',
            'postalCode': 'H0H0H0',
            'addressRegion': 'BC'
        }, Address.DELIVERY)
    party.save()
    role = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        appointment_date=datetime(2020, 1, 1),
        party_id=party.id,
        business_id=business.id
    )
    role.save()
    session.commit()
    return party


def _process(session, business, filing_factory, payload) -> Filing:
    filing_rec = filing_factory(payload)
    change_of_directors.process(business, filing_rec, FilingMeta(application_date=effective_date))
    session.commit()
    return filing_rec


def test_relationships_added(app, session, business, filing_factory):
    payload = {'relationships': [_relationship('Glenn', 'Quagmire', actions=['ADDED'])]}

    _process(session, business, filing_factory, payload)

    directors = _active_directors(business.id)
    assert len(directors) == 1
    assert directors[0].party.first_name == 'GLENN'
    assert directors[0].party.last_name == 'QUAGMIRE'
    assert directors[0].appointment_date.date() == datetime(2023, 1, 1).date()
    assert directors[0].party.delivery_address.street == DELIVERY_ADDRESS['streetAddress']
    assert business.last_cod_date == effective_date


def test_relationships_removed(app, session, business, filing_factory, existing_director):
    payload = {'relationships': [
        _relationship('Carol', 'Pilbasian', identifier=existing_director.id,
                      actions=['REMOVED'], cessation_date='2023-05-01')
    ]}

    _process(session, business, filing_factory, payload)

    assert _active_directors(business.id) == []
    roles = PartyRole.get_parties_by_role(business.id, PartyRole.RoleTypes.DIRECTOR.value)
    assert len(roles) == 1
    assert roles[0].cessation_date is not None


def test_relationships_edit_actions(app, session, business, filing_factory, existing_director):
    payload = {'relationships': [
        _relationship('Carole', 'Pilbasian-Miller', identifier=existing_director.id,
                      actions=['NAME_CHANGED', 'ADDRESS_CHANGED'])
    ]}

    _process(session, business, filing_factory, payload)

    directors = _active_directors(business.id)
    assert len(directors) == 1
    assert directors[0].party_id == existing_director.id
    assert directors[0].party.first_name == 'CAROLE'
    assert directors[0].party.last_name == 'PILBASIAN-MILLER'
    assert directors[0].party.delivery_address.street == DELIVERY_ADDRESS['streetAddress']


def test_relationships_changed_action(app, session, business, filing_factory, existing_director):
    payload = {'relationships': [
        _relationship('Caroline', 'Pilbasian', identifier=existing_director.id, actions=['CHANGED'])
    ]}

    _process(session, business, filing_factory, payload)

    directors = _active_directors(business.id)
    assert len(directors) == 1
    assert directors[0].party.first_name == 'CAROLINE'


def test_relationships_derived_actions(app, session, business, filing_factory, existing_director):
    ceased_party = Party(first_name='PETER', last_name='GRIFFIN')
    ceased_party.save()
    PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        appointment_date=datetime(2020, 1, 1),
        party_id=ceased_party.id,
        business_id=business.id
    ).save()
    session.commit()

    payload = {'relationships': [
        # no identifier -> derived appointed
        _relationship('Glenn', 'Quagmire'),
        # cessation date -> derived ceased
        _relationship('Peter', 'Griffin', identifier=ceased_party.id, cessation_date='2023-05-01'),
        # identifier only -> edit
        _relationship('Carole', 'Pilbasian', identifier=existing_director.id)
    ]}

    _process(session, business, filing_factory, payload)

    directors = _active_directors(business.id)
    assert len(directors) == 2
    names = {director.party.first_name for director in directors}
    assert names == {'GLENN', 'CAROLE'}
    ceased_role = next(role for role in PartyRole.get_parties_by_role(
        business.id, PartyRole.RoleTypes.DIRECTOR.value) if role.party_id == ceased_party.id)
    assert ceased_role.cessation_date is not None


def test_relationships_unknown_id_raises(app, session, business, filing_factory):
    payload = {'relationships': [
        _relationship('Nobody', 'Home', identifier=999999, actions=['NAME_CHANGED'])
    ]}
    filing_rec = filing_factory(payload)

    with pytest.raises(QueueException):
        change_of_directors.process(business, filing_rec, FilingMeta(application_date=effective_date))


def test_relationships_stored_filing_json_unchanged(app, session, business, filing_factory):
    payload = {'relationships': [_relationship('Glenn', 'Quagmire', actions=['ADDED'])]}

    filing_rec = _process(session, business, filing_factory, payload)

    stored = Filing.find_by_id(filing_rec.id).filing_json['filing']['changeOfDirectors']
    assert 'relationships' in stored
    assert 'directors' not in stored


def test_legacy_directors(app, session, business, filing_factory, existing_director):
    payload = {'directors': [
        {
            'officer': {'firstName': 'Glenn', 'lastName': 'Quagmire'},
            'deliveryAddress': copy.deepcopy(DELIVERY_ADDRESS),
            'mailingAddress': copy.deepcopy(MAILING_ADDRESS),
            'appointmentDate': '2023-01-01',
            'cessationDate': None,
            'actions': ['appointed']
        },
        {
            'officer': {'firstName': 'Carol', 'lastName': 'Pilbasian', 'id': existing_director.id},
            'deliveryAddress': copy.deepcopy(DELIVERY_ADDRESS),
            'mailingAddress': copy.deepcopy(MAILING_ADDRESS),
            'appointmentDate': '2020-01-01',
            'cessationDate': '2023-05-01',
            'actions': ['ceased']
        }
    ]}

    _process(session, business, filing_factory, payload)

    directors = _active_directors(business.id)
    assert len(directors) == 1
    assert directors[0].party.first_name == 'GLENN'
    assert business.last_cod_date == effective_date


def test_legacy_directors_empty_actions_noop(app, session, business, filing_factory, existing_director):
    payload = {'directors': [
        {
            'officer': {'firstName': 'Should Not', 'lastName': 'Apply', 'id': existing_director.id},
            'deliveryAddress': copy.deepcopy(DELIVERY_ADDRESS),
            'mailingAddress': copy.deepcopy(MAILING_ADDRESS),
            'appointmentDate': '2020-01-01',
            'cessationDate': None,
            'actions': []
        }
    ]}

    _process(session, business, filing_factory, payload)

    directors = _active_directors(business.id)
    assert len(directors) == 1
    assert directors[0].party.first_name == 'CAROL'
    assert directors[0].party.delivery_address.street == 'Old Street'
