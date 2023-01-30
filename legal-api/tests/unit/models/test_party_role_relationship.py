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
import json

from legal_api.models import PartyRole, PartyRoleRelationship


def test_party_role_relationship_save(session):
    """Assert that the party role relationship saves correctly."""
    relationship_types = PartyRoleRelationship.RelationshipTypes

    party_role = PartyRole(
        role=PartyRole.RoleTypes.APPLICANT.value,
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None
    )
    party_role.party_role_relationships.append(
        PartyRoleRelationship(relationship_type=relationship_types.HEIR_OR_LEGAL_REPRESENTATIVE.value)
    )
    party_role.party_role_relationships.append(
        PartyRoleRelationship(relationship_type=relationship_types.DIRECTOR.value)
    )
    party_role.save()
    assert party_role.id

    relationships = PartyRoleRelationship.find_by_party_role_id(party_role.id)
    assert len(relationships) == 2
    relationships[0].relationship_type == relationship_types.HEIR_OR_LEGAL_REPRESENTATIVE.value
    relationships[1].relationship_type == relationship_types.DIRECTOR.value
