# Copyright © 2019 Province of British Columbia
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

"""Tests to assure the PartyRole Model.

Test-Suite to ensure that the PartyRole Model is working as expected.
"""
import datetime
import json

from business_model.models import Filing, Party, PartyRole
from tests.models import factory_business


def test_party_member_save(session):
    """Assert that the party role saves correctly."""
    party_role = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None
    )

    party_role.save()
    assert party_role.id


def test_party_role_json(session):
    """Assert the json format of party role."""
    identifier = 'CP1234567'
    business = factory_business(identifier)
    member = Party(
        first_name='Michael',
        last_name='Crane',
        middle_initial='Joe',
        title='VP',
    )
    member.save()
    # sanity check
    assert member.id
    party_role = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None,
        party_id=member.id,
        business_id=business.id
    )
    party_role.save()

    party_role_json = {
        'appointmentDate': party_role.appointment_date.date().isoformat(),
        'cessationDate': party_role.cessation_date,
        'role': party_role.role,
        'officer': {
            'id': member.id,
            'firstName': member.first_name,
            'lastName': member.last_name,
            'middleInitial': member.middle_initial,
            'partyType': 'person',
            'email': None
        },
        'title': member.title
    }

    assert party_role.json == party_role_json


def test_find_party_by_name(session):
    """Assert the find_party_by_name method works as expected."""
    # setup
    identifier = 'CP1234567'
    business = factory_business(identifier)
    person = Party(
        first_name='Michael',
        last_name='Crane',
        middle_initial='Joe',
        title='VP',
    )
    person.save()
    no_middle_initial = Party(
        first_name='Testing',
        last_name='NoMiddleInitial',
        middle_initial='',
    )
    no_middle_initial.save()
    org = Party(
        organization_name='testOrg',
        party_type=Party.PartyTypes.ORGANIZATION.value
    )
    org.save()
    # sanity check
    assert person.id
    assert org.id
    director1 = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None,
        party_id=person.id,
        business_id=business.id
    )
    director1.save()
    director2 = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None,
        party_id=no_middle_initial.id,
        business_id=business.id
    )
    director2.save()
    completing_party = PartyRole(
        role=PartyRole.RoleTypes.COMPLETING_PARTY.value,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None,
        party_id=org.id,
        business_id=business.id
    )
    completing_party.save()
    # call method
    should_be_none = PartyRole.find_party_by_name(
        business_id=business.id,
        first_name='Test',
        last_name='Test',
        middle_initial='',
        org_name=''
    )
    should_not_find_michael = PartyRole.find_party_by_name(
        business_id=business.id,
        first_name='Michael',
        last_name='Crane',
        middle_initial='',
        org_name=''
    )
    should_find_michael = PartyRole.find_party_by_name(
        business_id=business.id,
        first_name='Michael',
        last_name='Crane',
        middle_initial='Joe',
        org_name=''
    )
    should_not_find_testing = PartyRole.find_party_by_name(
        business_id=business.id,
        first_name='Testing',
        last_name='NoMiddleInitial',
        middle_initial='T',
        org_name=''
    )
    should_find_testing = PartyRole.find_party_by_name(
        business_id=business.id,
        first_name='Testing',
        last_name='NoMiddleInitial',
        middle_initial='',
        org_name=''
    )
    should_find_testorg = PartyRole.find_party_by_name(
        business_id=business.id,
        first_name='',
        last_name='',
        middle_initial='',
        org_name='testorg'
    )
    # check values
    assert not should_be_none
    assert not should_not_find_michael
    assert not should_not_find_testing
    assert should_find_michael.id == person.id
    assert should_find_testing.id == no_middle_initial.id
    assert should_find_testorg.id == org.id


def test_get_party_roles(session):
    """Assert that the get_party_roles works as expected."""
    identifier = 'CP1234567'
    business = factory_business(identifier)
    member = Party(
        first_name='Connor',
        last_name='Horton',
        middle_initial='',
        title='VP',
    )
    member.save()
    # sanity check
    assert member.id
    party_role_1 = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None,
        party_id=member.id,
        business_id=business.id
    )
    party_role_1.save()
    party_role_2 = PartyRole(
        role=PartyRole.RoleTypes.CUSTODIAN.value,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None,
        party_id=member.id,
        business_id=business.id
    )
    party_role_2.save()
    # Find by all party roles
    party_roles = PartyRole.get_party_roles(business.id, datetime.datetime.now())
    assert len(party_roles) == 2

    # Find by party role
    party_roles = PartyRole.get_party_roles(business.id, datetime.datetime.now(), PartyRole.RoleTypes.CUSTODIAN.value)
    assert len(party_roles) == 1


def test_get_party_roles_by_party_id(session):
    """Assert that the get_party_roles works as expected."""
    identifier = 'CP1234567'
    business = factory_business(identifier)
    member = Party(
        first_name='Connor',
        last_name='Horton',
        middle_initial='',
        title='VP',
    )
    member.save()
    # sanity check
    assert member.id
    party_role_1 = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None,
        party_id=member.id,
        business_id=business.id
    )
    party_role_1.save()
    party_role_2 = PartyRole(
        role=PartyRole.RoleTypes.CUSTODIAN.value,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None,
        party_id=member.id,
        business_id=business.id
    )
    party_role_2.save()
    # Find by all party roles
    party_roles = PartyRole.get_party_roles_by_party_id(business.id, member.id)
    assert len(party_roles) == 2

    party_roles = PartyRole.get_party_roles_by_party_id(business.id, 123)
    assert len(party_roles) == 0


def test_get_party_roles_by_filing(session):
    """Assert that the get_party_roles works as expected."""
    identifier = 'CP1234567'
    business = factory_business(identifier)
    member = Party(
        first_name='Connor',
        last_name='Horton',
        middle_initial='',
        title='VP',
    )
    member.save()
    # sanity check
    assert member.id
    party_role_1 = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None,
        party_id=member.id,
        business_id=business.id
    )
    party_role_1.save()

    data = {'filing': 'not a real filing, fail validation'}
    filing = Filing()
    filing.business_id = business.id
    filing.filing_date = datetime.datetime.utcnow()
    filing.filing_data = json.dumps(data)
    filing.save()
    assert filing.id is not None

    party_role_2 = PartyRole(
        role=PartyRole.RoleTypes.CUSTODIAN.value,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None,
        party_id=member.id,
        filing_id=filing.id
    )
    party_role_2.save()
    # Find
    party_roles = PartyRole.get_party_roles(business.id, datetime.datetime.utcnow())
    assert len(party_roles) == 1

    party_roles = PartyRole.get_party_roles_by_filing(filing.id, datetime.datetime.utcnow())
    assert len(party_roles) == 1


def test_get_party_roles_unsupported_list(session):
    """Assert that the get_party_roles works as expected."""
    identifier = 'CP1234567'
    business = factory_business(identifier)
    member = Party(
        first_name='Connor',
        last_name='Horton',
        middle_initial='',
        title='VP',
    )
    member.save()
    # sanity check
    assert member.id
    party_role_1 = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None,
        party_id=member.id,
        business_id=business.id
    )
    party_role_1.save()
    party_role_2 = PartyRole(
        role=PartyRole.RoleTypes.OFFICER.value,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None,
        party_id=member.id,
        business_id=business.id
    )
    party_role_2.save()
    party_role_3 = PartyRole(
        role=PartyRole.RoleTypes.RECEIVER.value,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None,
        party_id=member.id,
        business_id=business.id
    )
    party_role_3.save()
    party_role_4 = PartyRole(
        role=PartyRole.RoleTypes.LIQUIDATOR.value,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None,
        party_id=member.id,
        business_id=business.id
    )
    party_role_4.save()
    # Find by all party roles
    unsupported_list = ['officer', 'receiver', 'liquidator']

    party_roles = PartyRole.get_party_roles(business.id, datetime.datetime.now())
    assert len(party_roles) == 4 - len(unsupported_list)

    for role in party_roles:
        assert role.role not in unsupported_list

    # Find by party role
    for role in unsupported_list:
        party_roles = PartyRole.get_party_roles(business.id, datetime.datetime.now(), role)
        assert len(party_roles) == 1
