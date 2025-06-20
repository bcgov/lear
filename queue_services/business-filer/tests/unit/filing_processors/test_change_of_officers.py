# Copyright © 2025 Province of British Columbia
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
"""The Unit Tests for the Change of Officer filing."""
import copy
from datetime import datetime, timezone
from sqlalchemy import select

import pytest
import random
from business_model.models import PartyRole, Party, Address, Business, Filing
from business_model.models.types.party_class_type import PartyClassType
from registry_schemas.example_data import FILING_TEMPLATE

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import change_of_officers
from tests.unit import create_business, create_filing
from business_filer.filing_processors.filing_components import create_address

CHANGE_OF_OFFICERS = {
    'relationships': [
        {
            'entity': {
                'givenName': 'Phillip Tandy',
                'familyName': 'Miller',
                'alternateName': 'Phil Miller'
            },
            'deliveryAddress': {
                'streetAddress': 'delivery_address - address line one',
                'addressCity': 'delivery_address city',
                'addressCountry': 'CA',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
            },
            'mailingAddress': {
                'streetAddress': 'mailing_address - address line one',
                'addressCity': 'mailing_address city',
                'addressCountry': 'CA',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
            },
            'roles': [
                {
                    'appointmentDate': '2018-01-01',
                    'roleType': 'CEO',
                    'roleClass': 'OFFICER'
                },
                {
                    'appointmentDate': '2018-01-01',
                    'roleType': 'Chair',
                    'roleClass': 'OFFICER'
                }
            ]
        },
        {
            'entity': {
                'givenName': 'Phillip Stacy',
                'familyName': 'Miller',
                'alternateName': 'Phil Miller'
            },
            'deliveryAddress': {
                'streetAddress': 'delivery_address - address line one',
                'addressCity': 'delivery_address city',
                'addressCountry': 'CA',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
            },
            'mailingAddress': {
                'streetAddress': 'mailing_address - address line one',
                'addressCity': 'mailing_address city',
                'addressCountry': 'CA',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
            },
            'roles': [
                {
                    'appointmentDate': '2018-01-01',
                    'roleType': 'President',
                    'roleClass': 'OFFICER'
                },
                {
                    'appointmentDate': '2018-01-01',
                    'roleType': 'CEO',
                    'roleClass': 'OFFICER'
                }
            ]
        }
    ]
}

effective_date = datetime(2023, 10, 10, 10, 0, 0, tzinfo=timezone.utc)

def _build_payload_from_party(party: Party, session) -> dict:
    # get all party roles
    stmt = select(PartyRole).where(PartyRole.party_id == party.id)
    roles_for_party = session.execute(stmt).scalars().all()

    roles_list = [
        {
            'roleType': role.role.title(),
            'appointmentDate': role.appointment_date.isoformat(),
            'cessationDate': role.cessation_date.isoformat() if role.cessation_date else None
        }
        for role in roles_for_party
    ]

    payload = {
        'entity': {
            'identifier': str(party.id),
            'givenName': party.first_name,
            'familyName': party.last_name
        },
        'deliveryAddress': {
            'streetAddress': party.delivery_address.street,
            'addressCity': party.delivery_address.city,
            'addressCountry': party.delivery_address.country,
            'postalCode': party.delivery_address.postal_code,
            'addressRegion': party.delivery_address.region
        } if party.delivery_address else None,
        'mailingAddress': {
            'streetAddress': party.mailing_address.street,
            'addressCity': party.mailing_address.city,
            'addressCountry': party.mailing_address.country,
            'postalCode': party.mailing_address.postal_code,
            'addressRegion': party.mailing_address.region
        } if party.mailing_address else None,
        'roles': roles_list
    }

    if party.alternate_name:
        payload['entity']['alternateName'] = party.alternate_name

    return payload

@pytest.fixture
def business(session):
    identifier = f'BC{random.randint(1000000, 9999999)}'
    b = create_business(identifier)
    return b

@pytest.fixture
def filing_factory(session, business: Business):
    def _factory(payload: dict) -> Filing:
        filing = copy.deepcopy(FILING_TEMPLATE)
        filing['filing']['header']['name'] = 'changeOfOfficers'
        filing['filing']['header']['effectiveDate'] = effective_date.isoformat()
        filing['filing']['business']['identifier'] = business.identifier
        filing['filing']['business']['legalType'] = 'BC'
        filing['filing']['changeOfOfficers'] = payload

        filing_rec = create_filing('123', filing, business.id)
        filing_rec.effective_date = effective_date
        filing_rec.save()

        return filing_rec
    return _factory

@pytest.fixture
def existing_parties_setup(session, business: Business):
    # create party
    carol = Party(first_name='CAROL', last_name='PILBASIAN')
    carol.delivery_address = create_address(
        {
            'streetAddress': 'Old Street',
            'addressCity': 'Old City',
            'addressCountry': 'CA',
            'postalCode': 'H0H0H0',
            'addressRegion': 'BC'
        }, Address.DELIVERY)
    carol.save()
    carol_ceo_role = PartyRole(role='ceo', appointment_date=datetime(2020, 1, 1), party_id=carol.id, business_id=business.id, party_class_type=PartyClassType.OFFICER)
    carol_ceo_role.save()

    # create second party
    gail = Party(first_name='GAIL', last_name='KLOSTERMAN')
    gail.save()
    gail_cfo_role = PartyRole(role='cfo', appointment_date=datetime(2021, 1, 1), party_id=gail.id, business_id=business.id, party_class_type=PartyClassType.OFFICER)
    gail_cfo_role.save()

    session.commit()

    yield {
        'carol': carol,
        'gail': gail,
        'carol_ceo_role': carol_ceo_role
    }

def test_change_of_officers_process_new_parties(app, session, filing_factory, business):
    """Assert that the Officers are updated."""
    # setup
    filing_rec = filing_factory(CHANGE_OF_OFFICERS)

    # test
    # no roles initially
    result = PartyRole.get_party_roles_by_class_type(business.id, PartyClassType.OFFICER, effective_date.date())
    assert len(result) == 0

    # process filing and commit db updates
    change_of_officers.process(business, filing_rec, FilingMeta(application_date=effective_date))
    session.commit()

    # query for all roles
    all_roles = PartyRole.get_party_roles_by_class_type(business.id, PartyClassType.OFFICER, effective_date.date())
    assert len(all_roles) == 4

    # should have 4 roles created
    assert len(all_roles) == 4

    # should have only 2 parties
    party_ids = {role.party_id for role in all_roles}
    assert len(party_ids) == 2

    # assert 2 parties created
    party_1 = session.execute(select(Party).where(Party.first_name == 'PHILLIP TANDY')).scalar_one_or_none()
    party_2 = session.execute(select(Party).where(Party.first_name == 'PHILLIP STACY')).scalar_one_or_none()

    assert party_1 is not None
    assert party_2 is not None

    # group created roles by party id
    roles_by_party_id = {}
    for role in all_roles:
        if role.party_id not in roles_by_party_id:
            roles_by_party_id[role.party_id] = []
        roles_by_party_id[role.party_id].append(role)
        
        assert role.appointment_date.date() == effective_date.date()
        assert role.cessation_date is None

    # assert roles for party_1
    party_1_roles = {role.role for role in roles_by_party_id[party_1.id]}
    expected_roles = {'ceo', 'chair'}
    assert party_1_roles == expected_roles
    
    # assert roles for party_2
    party_2_roles = {role.role for role in roles_by_party_id[party_2.id]}
    expected_roles = {'president', 'ceo'}
    assert party_2_roles == expected_roles    


def test_change_of_officers_process_update_party_name(app, session, existing_parties_setup, filing_factory, business):
    """Assert that the Officers are updated."""
    # setup
    carol = existing_parties_setup['carol']

    initial_street_address = carol.delivery_address.street
    initial_role = existing_parties_setup['carol_ceo_role']

    payload = _build_payload_from_party(carol, session)
    payload['entity']['givenName'] = 'CAROLINE'

    filing_rec = filing_factory({ 'relationships': [payload] })
    
    # test initial name
    party = Party.find_by_id(carol.id)
    assert party.first_name == 'CAROL'
    assert party.last_name == 'PILBASIAN'
    assert party.alternate_name == None

    # process filing and commit db updates
    change_of_officers.process(business, filing_rec, FilingMeta(application_date=effective_date))
    session.commit()

    # test new name
    party = Party.find_by_id(carol.id)
    assert party.first_name == 'CAROLINE'
    assert party.last_name == 'PILBASIAN'
    assert party.alternate_name == ''

    # assert address wasnt changed
    assert party.mailing_address_id is None
    assert party.delivery_address.street == initial_street_address

    current_roles = PartyRole.get_party_roles_by_party_id(business.id, party.id)

    assert current_roles[0] == initial_role

def test_change_of_officers_process_update_cease_party_role(app, session, existing_parties_setup, filing_factory, business):
    """Assert that the Officers are updated."""
    # setup
    carol = existing_parties_setup['carol']
    initial_role = existing_parties_setup['carol_ceo_role']
    initial_street_address = carol.delivery_address.street

    payload = _build_payload_from_party(carol, session)
    payload['roles'] = [{
        'appointmentDate': '2020-01-01',
        'cessationDate': '2021-01-01',
        'roleType': 'CEO',
        'roleClass': 'OFFICER'
    }]

    filing_rec = filing_factory({ 'relationships': [payload] })
    
    assert initial_role.cessation_date is None

    # process filing and commit db updates
    change_of_officers.process(business, filing_rec, FilingMeta(application_date=effective_date))
    session.commit()

    session.refresh(initial_role)

    assert initial_role.cessation_date is not None
    assert initial_role.cessation_date.date() == effective_date.date()

    # assert role not found active
    active_roles_after = PartyRole.get_party_roles_by_class_type(business.id, PartyClassType.OFFICER, effective_date.date())
    role_ids_after = {role.id for role in active_roles_after}
    
    assert initial_role.id not in role_ids_after

    # assert other fields not changed
    party = Party.find_by_id(carol.id)
    assert party.first_name == 'CAROL'
    assert party.last_name == 'PILBASIAN'

    # assert address wasnt changed
    assert party.mailing_address_id is None
    assert party.delivery_address.street == initial_street_address

def test_change_of_officers_process_add_new_role_to_existing_party(app, session, existing_parties_setup, filing_factory, business):
    """Asserts that a new role can be added to an existing party."""
    # setup
    carol = existing_parties_setup['carol']
    
    stmt = select(PartyRole).where(PartyRole.party_id == carol.id)
    initial_roles = session.execute(stmt).scalars().all()
    assert len(initial_roles) == 1
    assert initial_roles[0].role == 'ceo'


    payload = _build_payload_from_party(carol, session)
    payload['roles'] = [
        {
            'roleType': 'CEO', # existing role
            'roleClass': 'OFFICER',
            'appointmentDate': '2020-01-01',
        },
        {
            'roleType': 'President', # new role
            'roleClass': 'OFFICER',
            'appointmentDate': '2025-01-01',
        }
    ]
    filing_rec = filing_factory({ 'relationships': [payload] })
    
    change_of_officers.process(business, filing_rec, FilingMeta(application_date=effective_date))
    session.commit()

    stmt = select(PartyRole).where(PartyRole.party_id == carol.id)
    final_roles = session.execute(stmt).scalars().all()

    assert len(final_roles) == 2

    current_role_types = {role.role for role in final_roles}
    expected_role_types = {'ceo', 'president'}
    assert current_role_types == expected_role_types    

def test_change_of_officers_process_edit_existing_address(app, session, existing_parties_setup, filing_factory, business):
    """Asserts that a new role can be added to an existing party."""
    # setup
    carol = existing_parties_setup['carol']
    
    initial_street = carol.delivery_address.street
    assert initial_street == 'Old Street'
    assert carol.mailing_address == None


    payload = _build_payload_from_party(carol, session)
    payload['deliveryAddress']['streetAddress'] = 'NEW STREET'

    filing_rec = filing_factory({ 'relationships': [payload] })
    
    change_of_officers.process(business, filing_rec, FilingMeta(application_date=effective_date))
    session.commit()

    party = Party.find_by_id(carol.id)

    assert party.delivery_address.street == 'NEW STREET'

def test_change_of_officers_process_add_new_address(app, session, existing_parties_setup, filing_factory, business):
    """Asserts that a new role can be added to an existing party."""
    # setup
    carol = existing_parties_setup['carol']
    
    initial_mailing = carol.mailing_address
    assert initial_mailing == None


    payload = _build_payload_from_party(carol, session)
    payload['mailingAddress'] = {
        'streetAddress': 'NEW STREET',
        'addressCity': 'NEW CITY',
        'addressCountry': 'CA',
        'postalCode': 'H0H0H0',
        'addressRegion': 'BC'
    }

    filing_rec = filing_factory({ 'relationships': [payload] })
    
    change_of_officers.process(business, filing_rec, FilingMeta(application_date=effective_date))
    session.commit()

    party = Party.find_by_id(carol.id)

    assert party.mailing_address.street == 'NEW STREET'

def test_change_of_officers_process_edit_multiple_parties(app, session, existing_parties_setup, filing_factory, business):
    """Asserts that a new role can be added to an existing party."""
    # setup
    carol = existing_parties_setup['carol']
    initial_carol_role = existing_parties_setup['carol_ceo_role']
    gail = existing_parties_setup['gail']
    
    carol_payload = _build_payload_from_party(carol, session)
    gail_payload = _build_payload_from_party(gail, session)

    assert initial_carol_role.cessation_date is None

    # cease carol role
    carol_payload['roles'] = [{
        'appointmentDate': '2020-01-01',
        'cessationDate': '2021-01-01',
        'roleType': 'CEO',
        'roleClass': 'OFFICER'
    }]

    # update gail name
    gail_payload['entity']['givenName'] = 'NEW NAME'

    filing_rec = filing_factory({ 'relationships': [carol_payload, gail_payload] })
    
    change_of_officers.process(business, filing_rec, FilingMeta(application_date=effective_date))
    session.commit()
    session.refresh(initial_carol_role)

    assert initial_carol_role.cessation_date.date() == effective_date.date()

    # assert gail name change
    gail_party = Party.find_by_id(gail.id)
    assert gail_party.first_name == 'NEW NAME'
