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

"""Tests to assure the Party Model.

Test-Suite to ensure that the Party Model is working as expected.
"""
from http import HTTPStatus

import pytest

from business_model.exceptions import BusinessException
from business_model import Party, LegalEntity, ColinEntity


def test_party_json(session):
    """Assert the json format of party member."""
    person = LegalEntity(
        entity_type=LegalEntity.EntityTypes.PERSON.value,
        first_name="Michael",
        last_name="Crane",
        middle_initial="Joe",
        title="VP",
    )
    person.save()
    person_json = {
        "officer": {
            "id": person.id,
            "partyType": LegalEntity.EntityTypes.PERSON.value,
            "firstName": person.first_name,
            "lastName": person.last_name,
            "middleInitial": person.middle_initial,
            "email": None,
        },
        "title": person.title,
    }
    organization = ColinEntity(organization_name="organization", identifier="BC1234567")
    organization.save()
    organization_json = {
        "officer": {
            "id": organization.id,
            "organizationName": organization.organization_name,
            "identifier": "BC1234567",
            "email": None,
        },
    }

    assert person.party_json == person_json
    assert organization.json == organization_json


def test_party_save(session):
    """Assert that the party member saves correctly."""
    member1 = LegalEntity(
        entity_type=LegalEntity.EntityTypes.PERSON.value,
        first_name="Michael",
        last_name="Crane",
        middle_initial="Joe",
        title="VP",
    )
    member2 = ColinEntity(organization_name="organization", identifier="BC1234567")

    member1.save()
    member2.save()
    assert member1.id
    assert member2.id


def test_invalid_org_party_type(session):
    """Assert the party model validates the party type correctly."""
    member1 = LegalEntity(
        entity_type=LegalEntity.EntityTypes.BCOMP.value,
        first_name="invalid",
        last_name="name",
        middle_initial="test",
        title="INV",
    )
    member2 = LegalEntity(
        entity_type=LegalEntity.EntityTypes.PERSON.value, _legal_name="BC1234567 LTD"
    )
    with pytest.raises(BusinessException) as party_type_err1:
        member1.save()
    session.rollback()
    with pytest.raises(BusinessException) as party_type_err2:
        member2.save()
        print("herhe")

    assert party_type_err1 and party_type_err2
    assert party_type_err1.value.status_code == HTTPStatus.BAD_REQUEST
    assert party_type_err2.value.status_code == HTTPStatus.BAD_REQUEST
