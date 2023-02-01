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
"""This module holds data for partie role relationships."""
from __future__ import annotations

from enum import Enum

from .db import db  # noqa: I001


class PartyRoleRelationship(db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages party role relationship."""

    class RelationshipTypes(Enum):
        """Render an Enum of the relationship types."""

        HEIR_OR_LEGAL_REPRESENTATIVE = 'heir_or_legal_representative'
        OFFICER = 'officer'
        DIRECTOR = 'director'
        SHAREHOLDER = 'shareholder'
        COURT_ORDERED_PARTY = 'court_ordered_party'

    __versioned__ = {}
    __tablename__ = 'party_role_relationships'

    id = db.Column(db.Integer, primary_key=True)
    relationship_type = db.Column('relationship_type', db.String(30), nullable=False)

    party_role_id = db.Column('party_role_id', db.Integer,
                              db.ForeignKey('party_roles.id', ondelete='CASCADE'), nullable=False)

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @property
    def json(self) -> dict:
        """Return the party role relationship as a json object."""
        return {
            'id': self.id,
            'relationshipType': self.relationship_type,
            'partyRoleId': self.party_role_id
        }

    @classmethod
    def find_by_id(cls, party_role_relationship_id: int) -> PartyRoleRelationship:
        """Return a party role relationship by the internal id."""
        return cls.query.filter_by(id=party_role_relationship_id).one_or_none()

    @classmethod
    def find_by_party_role_id(cls, party_role_id: int) -> list[PartyRoleRelationship]:
        """Return a party role relationships by the party role id."""
        return cls.query.filter(PartyRoleRelationship.party_role_id == party_role_id).all()
