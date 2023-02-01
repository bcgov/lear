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

"""Tests to assure the PartyRoleRelationship Model.

Test-Suite to ensure that the PartyRoleRelationship Model is working as expected.
"""
import datetime

from legal_api.models import PartyRole, PartyRoleRelationship


def _create_party_role_relationship():
    party_role = PartyRole(
        role=PartyRole.RoleTypes.APPLICANT.value,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None
    )
    party_role.party_role_relationships.append(
        PartyRoleRelationship(
            relationship_type=PartyRoleRelationship.RelationshipTypes.HEIR_OR_LEGAL_REPRESENTATIVE.value))
    party_role.party_role_relationships.append(
        PartyRoleRelationship(
            relationship_type=PartyRoleRelationship.RelationshipTypes.DIRECTOR.value))
    party_role.save()
    return party_role


def test_party_role_relationship_save(session):
    """Assert that the party role relationship saves correctly."""
    party_role = _create_party_role_relationship()
    assert party_role.id

    relationships = PartyRoleRelationship.find_by_party_role_id(party_role.id)
    assert len(relationships) == 2
    expected = [PartyRoleRelationship.RelationshipTypes.HEIR_OR_LEGAL_REPRESENTATIVE.value,
                PartyRoleRelationship.RelationshipTypes.DIRECTOR.value]
    assert relationships[0].relationship_type in expected
    assert relationships[1].relationship_type in expected


def test_party_role_relationship_delete(session, db):
    """Assert that the party role relationship delete correctly."""
    party_role = _create_party_role_relationship()
    party_role_id = party_role.id

    db.session.delete(party_role)
    db.session.commit()

    relationships = PartyRoleRelationship.find_by_party_role_id(party_role_id)
    assert len(relationships) == 0
