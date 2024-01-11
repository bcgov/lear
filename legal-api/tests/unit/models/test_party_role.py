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

from legal_api.models import (
    ColinEntity,
    EntityRole,
    Filing,
    LegalEntity,
    Party,
    PartyRole,
)
from tests.unit.models import factory_legal_entity


def test_party_member_save(session):
    """Assert that the party role saves correctly."""
    identifier = "CP1234567"
    legal_entity = factory_legal_entity(identifier)

    party_role = EntityRole(
        role_type=EntityRole.RoleTypes.director,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None,
        legal_entity_id=legal_entity.id,
    )

    party_role.save()
    assert party_role.id


def test_party_role_json(session):
    """Assert the json format of party role."""
    identifier = "CP1234567"
    legal_entity = factory_legal_entity(identifier)
    member = LegalEntity(
        entity_type=LegalEntity.EntityTypes.PERSON.value,
        first_name="Michael",
        last_name="Crane",
        middle_initial="Joe",
        title="VP",
    )
    member.save()
    # sanity check
    assert member.id
    party_role = EntityRole(
        role_type=EntityRole.RoleTypes.director,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None,
        related_entity_id=member.id,
        legal_entity_id=legal_entity.id,
    )
    party_role.save()

    party_role_json = {
        "appointmentDate": party_role.appointment_date.date().isoformat(),
        "cessationDate": party_role.cessation_date,
        "role": party_role.role_type.name,
        "officer": {
            "id": member.id,
            "firstName": member.first_name,
            "lastName": member.last_name,
            "middleInitial": member.middle_initial,
            "partyType": "person",
            "email": None,
        },
        "title": member.title,
    }

    assert party_role.json == party_role_json


def test_find_party_by_name(session):
    """Assert the find_party_by_name method works as expected."""
    # setup
    identifier = "CP1234567"
    legal_entity = factory_legal_entity(identifier)
    person = LegalEntity(
        entity_type=LegalEntity.EntityTypes.PERSON.value,
        first_name="Michael",
        last_name="Crane",
        middle_initial="Joe",
        title="VP",
    )
    person.save()
    no_middle_initial = LegalEntity(
        entity_type=LegalEntity.EntityTypes.PERSON.value,
        first_name="Testing",
        last_name="NoMiddleInitial",
        middle_initial="",
    )
    no_middle_initial.save()
    org = ColinEntity(organization_name="testOrg", identifier="BC1234567")
    org.save()
    # sanity check
    assert person.id
    assert org.id
    director1 = EntityRole(
        role_type=EntityRole.RoleTypes.director,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None,
        related_entity_id=person.id,
        legal_entity_id=legal_entity.id,
    )
    director1.save()
    director2 = EntityRole(
        role_type=EntityRole.RoleTypes.director,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None,
        related_entity_id=no_middle_initial.id,
        legal_entity_id=legal_entity.id,
    )
    director2.save()
    completing_party = EntityRole(
        role_type=EntityRole.RoleTypes.completing_party,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None,
        related_colin_entity_id=org.id,
        legal_entity_id=legal_entity.id,
    )
    completing_party.save()
    # call method
    should_be_none = EntityRole.find_party_by_name(
        legal_entity_id=legal_entity.id, first_name="Test", last_name="Test", middle_initial="", org_name=""
    )
    should_not_find_michael = EntityRole.find_party_by_name(
        legal_entity_id=legal_entity.id, first_name="Michael", last_name="Crane", middle_initial="", org_name=""
    )
    should_find_michael = EntityRole.find_party_by_name(
        legal_entity_id=legal_entity.id, first_name="Michael", last_name="Crane", middle_initial="Joe", org_name=""
    )
    should_not_find_testing = EntityRole.find_party_by_name(
        legal_entity_id=legal_entity.id,
        first_name="Testing",
        last_name="NoMiddleInitial",
        middle_initial="T",
        org_name="",
    )
    should_find_testing = EntityRole.find_party_by_name(
        legal_entity_id=legal_entity.id,
        first_name="Testing",
        last_name="NoMiddleInitial",
        middle_initial="",
        org_name="",
    )
    should_find_testorg = EntityRole.find_party_by_name(
        legal_entity_id=legal_entity.id, first_name="", last_name="", middle_initial="", org_name="testorg"
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
    identifier = "CP1234567"
    legal_entity = factory_legal_entity(identifier)
    member = LegalEntity(
        entity_type=LegalEntity.EntityTypes.PERSON.value,
        first_name="Connor",
        last_name="Horton",
        middle_initial="",
        title="VP",
    )
    member.save()
    # sanity check
    assert member.id
    party_role_1 = EntityRole(
        role_type=EntityRole.RoleTypes.director,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None,
        related_entity_id=member.id,
        legal_entity_id=legal_entity.id,
    )
    party_role_1.save()
    party_role_2 = EntityRole(
        role_type=EntityRole.RoleTypes.custodian,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None,
        related_entity_id=member.id,
        legal_entity_id=legal_entity.id,
    )
    party_role_2.save()
    # Find by all party roles
    party_roles = EntityRole.get_entity_roles(legal_entity.id, datetime.datetime.now())
    assert len(party_roles) == 2

    # Find by party role
    party_roles = EntityRole.get_entity_roles(
        legal_entity.id, datetime.datetime.now(), EntityRole.RoleTypes.custodian.name
    )
    assert len(party_roles) == 1


def test_get_party_roles_by_related_entity_id(session):
    """Assert that the get_party_roles works as expected."""
    identifier = "CP1234567"
    legal_entity = factory_legal_entity(identifier)
    member = LegalEntity(
        entity_type=LegalEntity.EntityTypes.PERSON.value,
        first_name="Connor",
        last_name="Horton",
        middle_initial="",
        title="VP",
    )
    member.save()
    # sanity check
    assert member.id
    party_role_1 = EntityRole(
        role_type=EntityRole.RoleTypes.director,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None,
        related_entity_id=member.id,
        legal_entity_id=legal_entity.id,
    )
    party_role_1.save()
    party_role_2 = EntityRole(
        role_type=EntityRole.RoleTypes.custodian,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None,
        related_entity_id=member.id,
        legal_entity_id=legal_entity.id,
    )
    party_role_2.save()
    # Find by all party roles
    party_roles = EntityRole.get_entity_roles_by_party_id(legal_entity.id, member.id)
    assert len(party_roles) == 2

    party_roles = EntityRole.get_entity_roles_by_party_id(legal_entity.id, 123)
    assert len(party_roles) == 0


def test_get_party_roles_by_filing(session):
    """Assert that the get_party_roles works as expected."""
    identifier = "CP1234567"
    legal_entity = factory_legal_entity(identifier)
    member = LegalEntity(
        entity_type=LegalEntity.EntityTypes.PERSON.value,
        first_name="Connor",
        last_name="Horton",
        middle_initial="",
        title="VP",
    )
    member.save()
    # sanity check
    assert member.id
    party_role_1 = EntityRole(
        role_type=EntityRole.RoleTypes.director,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None,
        related_entity_id=member.id,
        legal_entity_id=legal_entity.id,
    )
    party_role_1.save()

    data = {"filing": "not a real filing, fail validation"}
    filing = Filing()
    filing.legal_entity_id = legal_entity.id
    filing.filing_date = datetime.datetime.utcnow()
    filing.filing_data = json.dumps(data)
    filing.save()
    assert filing.id is not None

    party_role_2 = EntityRole(
        role_type=EntityRole.RoleTypes.custodian,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None,
        legal_entity_id=member.id,
        filing_id=filing.id,
    )
    party_role_2.save()
    # Find
    party_roles = EntityRole.get_entity_roles(legal_entity.id, datetime.datetime.utcnow())
    assert len(party_roles) == 1

    party_roles = EntityRole.get_entity_roles_by_filing(filing.id, datetime.datetime.utcnow())
    assert len(party_roles) == 1
