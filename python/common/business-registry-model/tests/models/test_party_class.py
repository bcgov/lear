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

"""Tests to assure the PartyClass Model.

Test-Suite to ensure that the PartyClass Model is working as expected.
"""
import datetime
import json
import pytest

from sqlalchemy import select
from sqlalchemy.orm import Session

from business_model.models import PartyClass
from business_model.models import PartyRole
from tests.models import factory_business
from business_model.models.types.party_class_type import PartyClassType

party_class_data = [
    {"class_type": PartyClassType.DIRECTOR, "short_description": "Director Desc", "full_description": "Full Desc 1"},
    {"class_type": PartyClassType.AGENT, "short_description": "Agent Desc", "full_description": "Full Desc 2"},
    {"class_type": PartyClassType.OFFICER, "short_description": "Officer Desc", "full_description": "Full Desc 3"},
    {"class_type": PartyClassType.ATTORNEY, "short_description": "Attorney Desc", "full_description": "Full Desc 4"},
]

def test_party_class_save(session: Session):
    """Assert that the party class saves correctly."""
    party_class = PartyClass(
        class_type=PartyClassType.DIRECTOR,
        short_description="Short Description",
        full_description="Full Description"
    )

    party_class.save()

    assert party_class.id


def test_party_class_json(session: Session):
    """Assert the json format of party class."""
    party_class = PartyClass(
        class_type=PartyClassType.DIRECTOR,
        short_description="Short Description",
        full_description="Full Description"
    )

    session.add(party_class)
    session.flush()

    party_class_json = {
        'id': 1,
        'classType': 'director',
        'shortDescription': 'Short Description',
        'fullDescription': 'Full Description',
    }

    assert party_class.json == party_class_json


def test_party_class_find_by_internal_id(session: Session):
    """Assert the party class can be found by id."""
    # load 1 of each class type into db
    for data in party_class_data:
        party_class = PartyClass(
            class_type=data['class_type'],
            short_description=data['short_description'],
            full_description=data['full_description']
        )
        session.add(party_class)

    session.flush()

    # assert 4 items can be found by id
    for i in range(len(party_class_data)):
        target_id = i + 1
        found = PartyClass.find_by_internal_id(target_id)

        assert found is not None
        assert found.id == target_id

    # id 5 should not exist
    assert PartyClass.find_by_internal_id(5) == None


def test_party_class_find_by_class_type(session: Session):
    """Assert the party class can be found by its class type."""
    # load 1 of each class type into db
    for data in party_class_data:
        party_class = PartyClass(
            class_type=data['class_type'],
            short_description=data['short_description'],
            full_description=data['full_description']
        )
        session.add(party_class)

    session.flush()

    # assert 4 items can be found by class type
    for data in party_class_data:
        target_class = data["class_type"]
        found = PartyClass.find_by_class_type(target_class)

        assert found is not None
        assert found.class_type == target_class


def test_party_class_party_role_relationship(session: Session):
    """Assert the relationship between PartyClass and PartyRole"""
    party_class = PartyClass(
        class_type=PartyClassType.OFFICER,
        short_description="Short Desc",
        full_description="Full Desc"
    )

    role_1 = PartyRole(
        role=PartyRole.RoleTypes.CEO.value,
        appointment_date=datetime.datetime(2022, 5, 17),
        cessation_date=None,
        party_class_type=party_class.class_type
    )

    role_2 = PartyRole(
        role=PartyRole.RoleTypes.CHAIR.value,
        appointment_date=datetime.datetime(2022, 5, 17),
        cessation_date=None,
        party_class_type=party_class.class_type
    )

    session.add_all([party_class, role_1, role_2])
    session.flush()

    assert party_class.id

    parent = session.execute(select(PartyClass).where(PartyClass.id == party_class.id)).scalar_one_or_none()

    assert parent.id

    assert len(parent.party_roles) == 2
