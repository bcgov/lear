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

"""Tests to assure the PartyMember Model.

Test-Suite to ensure that the PartyMember Model is working as expected.
"""
from legal_api.models import PartyMember


def test_party_member_json(session):
    """Assert the json format of party member."""
    member = PartyMember(
        first_name='Michael',
        last_name='Crane',
        middle_initial='Joe',
        title='VP',
    )

    member_json = {
        'officer': {
            'firstName': member.first_name,
            'lastName': member.last_name,
            'middleInitial': member.middle_initial
        },
        'title': member.title
    }

    assert member.json == member_json


def test_party_member_save(session):
    """Assert that the party member saves correctly."""
    member = PartyMember(
        first_name='Michael',
        last_name='Crane',
        middle_initial='Joe',
        title='VP'
    )

    member.save()
    assert member.id
