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

from legal_api.exceptions import BusinessException
from legal_api.models import Party


def test_party_json(session):
    """Assert the json format of party member."""
    person = Party(
        party_type=Party.PartyTypes.PERSON.value,
        first_name='Michael',
        last_name='Crane',
        middle_initial='Joe',
        alternate_name='Mike J Crane',
        title='VP'
    )
    person.save()
    person_json = {
        'officer': {
            'id': person.id,
            'partyType': Party.PartyTypes.PERSON.value,
            'firstName': person.first_name,
            'lastName': person.last_name,
            'middleInitial': person.middle_initial,
            'alternateName': person.alternate_name,
            'email': None
        },
        'title': person.title
    }
    organization = Party(
        party_type=Party.PartyTypes.ORGANIZATION.value,
        organization_name='organization'
    )
    organization.save()
    organization_json = {
        'officer': {
            'id': organization.id,
            'partyType': Party.PartyTypes.ORGANIZATION.value,
            'organizationName': organization.organization_name,
            'identifier': None,
            'email': None
        },
    }

    assert person.json == person_json
    assert organization.json == organization_json


def test_party_save(session):
    """Assert that the party member saves correctly."""
    member1 = Party(
        first_name='Michael',
        last_name='Crane',
        middle_initial='Joe',
        title='VP'
    )
    member2 = Party(
        party_type=Party.PartyTypes.ORGANIZATION.value,
        organization_name='organization'
    )

    member1.save()
    member2.save()
    assert member1.id
    assert member2.id


def test_invalid_org_party_type(session):
    """Assert the party model validates the party type correctly."""
    member1 = Party(
        party_type=Party.PartyTypes.ORGANIZATION.value,
        first_name='invalid',
        last_name='name',
        middle_initial='test',
        title='INV'
    )
    member2 = Party(
        party_type=Party.PartyTypes.PERSON.value,
        organization_name='organization'
    )
    with pytest.raises(BusinessException) as party_type_err1:
        member1.save()
    session.rollback()
    with pytest.raises(BusinessException) as party_type_err2:
        member2.save()

    assert party_type_err1 and party_type_err2
    assert party_type_err1.value.status_code == HTTPStatus.BAD_REQUEST
    assert party_type_err2.value.status_code == HTTPStatus.BAD_REQUEST
