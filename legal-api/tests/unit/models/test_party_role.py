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

from legal_api.models import Party, PartyRole
from tests.unit.models import factory_business


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
            'firstName': member.first_name,
            'lastName': member.last_name,
            'middleInitial': member.middle_initial
        },
        'title': member.title
    }

    assert party_role.json == party_role_json
