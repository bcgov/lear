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

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from business_model.models import PartyClass, PartyRole
from business_model.models.types.party_class_type import PartyClassType


@pytest.mark.skip('All PartyClassTypes already set in bulk_insert migration file')
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
    party_class = PartyClass.find_by_class_type(PartyClassType.DIRECTOR)

    json = party_class.json
    
    assert json["id"]
    assert json["classType"] == 'DIRECTOR'
    assert isinstance(json["shortDescription"], str)
    assert len(json["shortDescription"]) > 0

    assert isinstance(json["fullDescription"], str)
    assert len(json["fullDescription"]) > 0


def test_party_class_find_by_internal_id(session: Session):
    """Assert the party class can be found by id."""
    # ONLY 4 PARTYCLASSES
    # assert 4 items can be found by id
    for i in range(4):
        target_id = i + 1
        found = PartyClass.find_by_internal_id(target_id)

        assert found is not None
        assert found.id == target_id

    # id 5 should not exist
    assert PartyClass.find_by_internal_id(5) == None


def test_party_class_find_by_class_type(session: Session):
    """Assert the party class can be found by its class type."""
    # ONLY 4 PARTYCLASSES
    # assert 4 items can be found by class type
    party_class_types = [PartyClassType.DIRECTOR, PartyClassType.AGENT, PartyClassType.ATTORNEY, PartyClassType.OFFICER]

    for type in party_class_types:
        found = PartyClass.find_by_class_type(type)

        assert found is not None
        assert found.class_type == type


def test_party_class_party_role_relationship(session: Session):
    """Assert the relationship between PartyClass and PartyRole"""
    role_1 = PartyRole(
        role=PartyRole.RoleTypes.CEO.value,
        appointment_date=datetime.datetime(2022, 5, 17),
        cessation_date=None,
        party_class_type=PartyClassType.OFFICER
    )

    role_2 = PartyRole(
        role=PartyRole.RoleTypes.CHAIR.value,
        appointment_date=datetime.datetime(2022, 5, 17),
        cessation_date=None,
        party_class_type=PartyClassType.OFFICER
    )

    session.add_all([role_1, role_2])
    session.flush()

    parent = PartyClass.find_by_class_type(PartyClassType.OFFICER)

    assert parent.id

    assert len(parent.party_roles) == 2
