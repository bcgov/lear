# Copyright © 2023 Province of British Columbia
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

"""Tests to assure the AlternateName Model.

Test-Suite to ensure that the AlternateName Model is working as expected.
"""
from datetime import datetime

import pytest

from legal_api.models import AlternateName
from tests.unit import nested_session
from tests.unit.models import factory_alternate_name, factory_legal_entity


def test_valid_alternate_name_save(session):
    """Assert that a valid alias can be saved."""
    identifier = "BC1234567"
    legal_entity = factory_legal_entity(identifier)

    alternate_name_1 = AlternateName(
        identifier=identifier,
        name_type=AlternateName.NameType.DBA,
        name="XYZ Test BC LTD",
        bn15="111111100BC1111",
        start_date=datetime.utcnow(),
        legal_entity_id=legal_entity.id,
    )
    alternate_name_1.save()

    alternate_name_2 = AlternateName(
        identifier=identifier,
        name_type=AlternateName.NameType.DBA,
        name="ABC Test BC LTD",
        bn15="222222200BC2222",
        start_date=datetime.utcnow(),
        legal_entity_id=legal_entity.id,
    )
    alternate_name_2.save()

    # verify
    assert alternate_name_1.id
    assert alternate_name_2.id
    alternate_names = legal_entity.alternate_names.all()
    assert len(alternate_names) == 2
    assert all(alternate_name.name_type == AlternateName.NameType.DBA for alternate_name in alternate_names)
    assert any(alternate_name.name == "XYZ Test BC LTD" for alternate_name in alternate_names)
    assert any(alternate_name.name == "ABC Test BC LTD" for alternate_name in alternate_names)


@pytest.mark.parametrize(
    "entity_type, operating_name, expected_business_name",
    [
        ("SP", "SP Test XYZ", "SP Test XYZ"),
        ("GP", "GP Test XYZ", "GP Test XYZ"),
    ],
)
def test_business_name(session, entity_type, operating_name, expected_business_name):
    """Assert that correct business name is returned."""
    with nested_session(session):
        identifier = "BC1234567"
        legal_entity = factory_legal_entity(identifier=identifier, entity_type=entity_type)

        alternate_name = factory_alternate_name(
            identifier=identifier,
            name=operating_name,
            name_type=AlternateName.NameType.DBA,
            bn15="111111100BC1111",
            start_date=datetime.utcnow(),
            legal_entity_id=legal_entity.id,
        )

        legal_entity.alternate_names.append(alternate_name)
        legal_entity.skip_party_listener = True

        assert alternate_name.business_name == expected_business_name


def test_alternate_name_alias_json(session):
    """Assert the json format for alternate name alias(translation)"""
    with nested_session(session):
        identifier = "BC1234567"
        legal_entity = factory_legal_entity(identifier=identifier)

        alternate_name = factory_alternate_name(
            name="NAME TRANSLATION",
            name_type=AlternateName.NameType.TRANSLATION,
            start_date=datetime.utcnow(),
            legal_entity_id=legal_entity.id,
        )

        assert alternate_name.alias_json
        assert alternate_name.alias_json["name"] == "NAME TRANSLATION"
        assert alternate_name.alias_json["type"] == "TRANSLATION"


def test_find_by_name_type(session):
    """Assert that the method returns correct value."""
    with nested_session(session):
        identifier = "BC1234567"
        legal_entity = factory_legal_entity(identifier=identifier)

        alternate_name = factory_alternate_name(
            name="ABC Ltd.",
            name_type=AlternateName.NameType.DBA,
            start_date=datetime.utcnow(),
            legal_entity_id=legal_entity.id,
        )

        alternate_name2 = factory_alternate_name(
            name="NAME TRANSLATION 1",
            name_type=AlternateName.NameType.TRANSLATION,
            start_date=datetime.utcnow(),
            legal_entity_id=legal_entity.id,
        )

        alternate_name3 = factory_alternate_name(
            name="NAME TRANSLATION 2",
            name_type=AlternateName.NameType.TRANSLATION,
            start_date=datetime.utcnow(),
            legal_entity_id=legal_entity.id,
        )

        res = AlternateName.find_by_name_type(legal_entity.id, "TRANSLATION")

        assert res
        assert len(res) == 2
        assert res[0].name == "NAME TRANSLATION 1"
        assert res[1].name == "NAME TRANSLATION 2"
