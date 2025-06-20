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

def _get_party_snapshot(party: Party) -> dict:
    """Takes a Party object and returns a 'snapshot' of its state."""
    # This queries for the roles at the moment the snapshot is taken
    roles = PartyRole.query.filter_by(party_id=party.id).all()
    return {
        'first_name': party.first_name,
        'last_name': party.last_name,
        'alternate_name': party.alternate_name if party.alternate_name else None,
        'middle_initial': party.middle_initial if party.middle_initial else None,
        'delivery_street': party.delivery_address.street if party.delivery_address else None,
        'delivery_city': party.delivery_address.city if party.delivery_address else None,
        'delivery_country': party.delivery_address.country if party.delivery_address else None,
        'delivery_code': party.delivery_address.postal_code if party.delivery_address else None,
        'delivery_region': party.delivery_address.region if party.delivery_address else None,
        'mailing_street': party.mailing_address.street if party.mailing_address else None,
        'mailing_city': party.mailing_address.city if party.mailing_address else None,
        'mailing_country': party.mailing_address.country if party.mailing_address else None,
        'mailing_code': party.mailing_address.postal_code if party.mailing_address else None,
        'mailing_region': party.mailing_address.region if party.mailing_address else None,
        'roles': {role.role: {
            'role': role.role,
            'appointment_date': role.appointment_date.date(), # Store as date object for clean comparison
            'cessation_date': role.cessation_date.date() if role.cessation_date else None,
            'class_type': role.party_class_type.name # Store the enum's name, e.g., 'OFFICER'
        } for role in roles}
    }

def _assert_party_state_unchanged(intial_state: dict, party: Party, ignored_keys: list[str] = []):
    """Asserts that a party's state is unchanged."""
    after_state = _get_party_snapshot(party)

    ignored_keys_set = set(ignored_keys)

    for key, initial_value in intial_state.items():
        if key in ignored_keys_set:
            continue
        
        new_value = after_state.get(key)
        assert new_value == initial_value

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

def _execute_process(session, business, filing_factory, payload):
    filing_rec = filing_factory(payload)
    change_of_officers.process(business, filing_rec, FilingMeta(application_date=effective_date))
    session.commit()

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

def test_new_parties(app, session, filing_factory, business):
    # assert initial
    result = PartyRole.get_party_roles_by_class_type(business.id, PartyClassType.OFFICER, effective_date.date())
    assert len(result) == 0

    # process
    _execute_process(session, business, filing_factory, CHANGE_OF_OFFICERS)

    # assert after
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


def test_new_and_existing_parties(app, session, existing_parties_setup, filing_factory, business):
    # setup
    carol = existing_parties_setup['carol']
    gail = existing_parties_setup['gail']

    initial_carol = _get_party_snapshot(carol)
    initial_gail = _get_party_snapshot(gail)

    # assert inital
    party_1 = Party.find_by_id(carol.id)
    party_2 = Party.find_by_id(gail.id)
    assert party_1
    assert party_2

    # process
    _execute_process(session, business, filing_factory, CHANGE_OF_OFFICERS)

    # assert existing parties unchanged
    _assert_party_state_unchanged(initial_carol, Party.find_by_id(carol.id), [])
    _assert_party_state_unchanged(initial_gail, Party.find_by_id(gail.id), [])

    # assert business now has 4 parties, 2 existing and 2 new
    total_parties = session.execute(select(PartyRole.party_id).where(PartyRole.business_id == business.id).distinct()).scalars().all()
    assert len(total_parties) == 4
    # assert business now has 6 party roles, 2 existing and 4 new
    total_roles = session.execute(select(PartyRole).where(PartyRole.business_id == business.id)).scalars().all()
    assert len(total_roles) == 6


def test_update_party_name(app, session, existing_parties_setup, filing_factory, business):
    # setup
    carol = existing_parties_setup['carol']
    gail = existing_parties_setup['gail']

    initial_carol = _get_party_snapshot(carol)
    initial_gail = _get_party_snapshot(gail)

    # assert inital
    party = Party.find_by_id(carol.id)
    assert party.first_name == 'CAROL'

    # process
    payload = _build_payload_from_party(carol, session)
    payload['entity']['givenName'] = 'CAROLINE'
    _execute_process(session, business, filing_factory, { 'relationships': [payload] })

    # assert after
    party = Party.find_by_id(carol.id)
    assert party.first_name == 'CAROLINE'

    # assert nothing changed except for first name and last name
    _assert_party_state_unchanged(initial_carol, party, ['first_name'])
    # assert other party unchanged
    _assert_party_state_unchanged(initial_gail, Party.find_by_id(gail.id), [])
    

def test_cease_party_role(app, session, existing_parties_setup, filing_factory, business):
    # setup
    carol = existing_parties_setup['carol']
    gail = existing_parties_setup['gail']

    initial_carol = _get_party_snapshot(carol)
    initial_gail = _get_party_snapshot(gail)
    initial_role = existing_parties_setup['carol_ceo_role']

    # assert initial
    assert initial_role.cessation_date is None

    # process
    payload = _build_payload_from_party(carol, session)
    payload['roles'] = [{
        'appointmentDate': '2020-01-01',
        'cessationDate': '2021-01-01',
        'roleType': 'CEO',
        'roleClass': 'OFFICER'
    }]
    _execute_process(session, business, filing_factory, { 'relationships': [payload] })
    
    # assert after
    session.refresh(initial_role)

    assert initial_role.cessation_date is not None
    assert initial_role.cessation_date.date() == effective_date.date()

    # assert role not found active
    active_roles_after = PartyRole.get_party_roles_by_class_type(business.id, PartyClassType.OFFICER, effective_date.date())
    role_ids_after = {role.id for role in active_roles_after}
    
    assert initial_role.id not in role_ids_after

    # assert nothing changed except for roles
    _assert_party_state_unchanged(initial_carol, Party.find_by_id(carol.id), ['roles'])
    # assert other party unchanged
    _assert_party_state_unchanged(initial_gail, Party.find_by_id(gail.id), [])

def test_add_new_role_to_existing_party(app, session, existing_parties_setup, filing_factory, business):
    # setup
    carol = existing_parties_setup['carol']
    gail = existing_parties_setup['gail']

    initial_carol = _get_party_snapshot(carol)
    initial_gail = _get_party_snapshot(gail)
    
    # assert initial
    stmt = select(PartyRole).where(PartyRole.party_id == carol.id)
    initial_roles = session.execute(stmt).scalars().all()
    assert len(initial_roles) == 1
    assert initial_roles[0].role == 'ceo'

    # process
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
    _execute_process(session, business, filing_factory, { 'relationships': [payload] })

    # assert after
    stmt = select(PartyRole).where(PartyRole.party_id == carol.id)
    final_roles = session.execute(stmt).scalars().all()

    assert len(final_roles) == 2

    current_role_types = {role.role for role in final_roles}
    expected_role_types = {'ceo', 'president'}
    assert current_role_types == expected_role_types
    # assert nothing changed except for roles
    _assert_party_state_unchanged(initial_carol, Party.find_by_id(carol.id), ['roles'])
    # assert other party unchanged
    _assert_party_state_unchanged(initial_gail, Party.find_by_id(gail.id), [])


def test_edit_existing_address(app, session, existing_parties_setup, filing_factory, business):
    # setup
    carol = existing_parties_setup['carol']
    gail = existing_parties_setup['gail']

    initial_carol = _get_party_snapshot(carol)
    initial_gail = _get_party_snapshot(gail)
    
    # assert initial
    initial_street = carol.delivery_address.street
    assert initial_street == 'Old Street'
    assert carol.mailing_address == None

    # process
    payload = _build_payload_from_party(carol, session)
    payload['deliveryAddress']['streetAddress'] = 'NEW STREET'
    _execute_process(session, business, filing_factory, { 'relationships': [payload] })
    
    # assert after
    party = Party.find_by_id(carol.id)

    assert party.delivery_address.street == 'NEW STREET'
    # assert nothing changed except for delivery street
    _assert_party_state_unchanged(initial_carol, Party.find_by_id(carol.id), ['delivery_street'])
    # assert other party unchanged
    _assert_party_state_unchanged(initial_gail, Party.find_by_id(gail.id), [])


def test_add_new_address_to_existing_party(app, session, existing_parties_setup, filing_factory, business):
    # setup
    carol = existing_parties_setup['carol']
    gail = existing_parties_setup['gail']

    initial_carol = _get_party_snapshot(carol)
    initial_gail = _get_party_snapshot(gail)
    
    # assert initial
    initial_mailing = carol.mailing_address
    assert initial_mailing == None

    # process
    payload = _build_payload_from_party(carol, session)
    payload['mailingAddress'] = {
        'streetAddress': 'NEW STREET',
        'addressCity': 'NEW CITY',
        'addressCountry': 'CA',
        'postalCode': 'H0H0H0',
        'addressRegion': 'BC'
    }
    _execute_process(session, business, filing_factory, { 'relationships': [payload] })
    
    # assert after
    party = Party.find_by_id(carol.id)
    assert party.mailing_address.street == 'NEW STREET'
    # assert nothing changed except for mailing address
    _assert_party_state_unchanged(initial_carol, Party.find_by_id(carol.id), [
        'mailing_street',
        'mailing_city',
        'mailing_country',
        'mailing_code',
        'mailing_region'
    ])
    # assert other party unchanged
    _assert_party_state_unchanged(initial_gail, Party.find_by_id(gail.id), [])


def test_edit_multiple_parties_and_fields(app, session, existing_parties_setup, filing_factory, business):
    # setup
    carol = existing_parties_setup['carol']
    gail = existing_parties_setup['gail']
    initial_carol_role = existing_parties_setup['carol_ceo_role']

    initial_carol = _get_party_snapshot(carol)
    initial_gail = _get_party_snapshot(gail)
    
    # assert initial
    assert initial_carol_role.cessation_date is None
    assert carol.delivery_address.street == 'Old Street'
    assert gail.first_name == 'GAIL'
    assert gail.alternate_name is None

    # process
    carol_payload = _build_payload_from_party(carol, session)
    gail_payload = _build_payload_from_party(gail, session)
    carol_payload['roles'] = [{ # cease carol role
        'appointmentDate': '2020-01-01',
        'cessationDate': '2021-01-01',
        'roleType': 'CEO',
        'roleClass': 'OFFICER'
    }]
    carol_payload['deliveryAddress']['streetAddress'] = 'NEW STREET' # update carol street address
    gail_payload['entity']['givenName'] = 'NEW NAME' # update gail name
    gail_payload['entity']['alternateName'] = 'NEW ALTERNATE NAME' # update gail name
    _execute_process(session, business, filing_factory, { 'relationships': [carol_payload, gail_payload] })
    
    # assert after
    session.refresh(initial_carol_role)
    # assert carol role ceased
    assert initial_carol_role.cessation_date.date() == effective_date.date()
    carol_party = Party.find_by_id(carol.id)
    assert carol_party.delivery_address.street == 'NEW STREET'

    # assert gail name change
    gail_party = Party.find_by_id(gail.id)
    assert gail_party.first_name == 'NEW NAME'
    assert gail_party.alternate_name == 'NEW ALTERNATE NAME'

    # assert nothing else changed
    _assert_party_state_unchanged(initial_carol, carol_party, ['delivery_street', 'roles'])
    _assert_party_state_unchanged(initial_gail, gail_party, ['first_name', 'alternate_name'])


def test_new_role_with_cessation_date_is_ignored(app, session, existing_parties_setup, filing_factory, business):
    # setup
    carol = existing_parties_setup['carol']
    gail = existing_parties_setup['gail']

    initial_carol = _get_party_snapshot(carol)
    initial_gail = _get_party_snapshot(gail)
    
    # assert initial
    carol_roles = session.execute(select(PartyRole).where(PartyRole.party_id == carol.id)).scalars().all()
    assert len(carol_roles) == 1

    # process
    payload = _build_payload_from_party(carol, session)
    payload['roles'] = [{ # new role with cessation date should be ignored
        'appointmentDate': '2020-01-01',
        'cessationDate': '2021-01-01',
        'roleType': 'CFO',
        'roleClass': 'OFFICER'
    }]
    _execute_process(session, business, filing_factory, { 'relationships': [payload] })

    # assert after
    carol_roles = session.execute(select(PartyRole).where(PartyRole.party_id == carol.id)).scalars().all()
    assert len(carol_roles) == 1

    carol_party = Party.find_by_id(carol.id)
    gail_party = Party.find_by_id(gail.id)

    # assert nothing else changed
    _assert_party_state_unchanged(initial_carol, carol_party, [])
    _assert_party_state_unchanged(initial_gail, gail_party, [])


def test_entity_with_id_not_found_is_ignored(app, session, filing_factory, business):
    # setup
    CHANGE_OF_OFFICERS['relationships'][0]['entity']['identifier'] = '1000'
    CHANGE_OF_OFFICERS['relationships'][1]['entity']['identifier'] = '10000'
    
    # assert initial
    result = PartyRole.get_party_roles_by_class_type(business.id, PartyClassType.OFFICER, effective_date.date())
    assert len(result) == 0

    # process
    _execute_process(session, business, filing_factory, CHANGE_OF_OFFICERS)

    # assert after
    result = PartyRole.get_party_roles_by_class_type(business.id, PartyClassType.OFFICER, effective_date.date())
    assert len(result) == 0

def test_rejects_update_for_party_from_another_business(app, session, existing_parties_setup, filing_factory):
    # setup
    carol = existing_parties_setup['carol']
    gail = existing_parties_setup['gail']

    initial_carol = _get_party_snapshot(carol)
    initial_gail = _get_party_snapshot(gail)

    # new business to submit against
    identifier = f'BC{random.randint(1000000, 9999999)}'
    other_business = create_business(identifier)

    # assert initial
    other_business_party_roles = other_business.party_roles.all()
    assert len(other_business_party_roles) == 0

    # process
    carol_payload = _build_payload_from_party(carol, session)
    gail_payload = _build_payload_from_party(gail, session)
    carol_payload['entity']['givenName'] = 'NEW CAROL' # update carol name
    gail_payload['entity']['givenName'] = 'NEW GAIL' # update gail name

    _execute_process(session, other_business, filing_factory, { 'relationships': [carol_payload, gail_payload] })

    # assert after
    session.refresh(other_business)
    other_business_party_roles = other_business.party_roles.all()
    assert len(other_business_party_roles) == 0

    carol_party = Party.find_by_id(carol.id)
    gail_party = Party.find_by_id(gail.id)

    # assert nothing changed
    _assert_party_state_unchanged(initial_carol, carol_party, [])
    _assert_party_state_unchanged(initial_gail, gail_party, [])