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
"""This module holds data for party classes in a business."""
from __future__ import annotations

from enum import auto
from sql_versioning import Versioned

from legal_api.utils.base import BaseEnum
from .db import db


class PartyClass(db.Model, Versioned):
    """Class that manages data for party classes related to a PartyRole."""

    class PartyClassType(BaseEnum):
        """Render an Enum of the party class types."""
        ATTORNEY = auto()
        AGENT = auto()
        DIRECTOR = auto()
        OFFICER = auto()


    __versioned__ = {}
    __tablename__ = 'party_class'

    id = db.Column(db.Integer, primary_key=True)
    class_type = db.Column(db.Enum(PartyClassType), nullable=False, unique=True)
    short_description = db.Column(db.String(512))
    full_description = db.Column(db.String(1024))

    party_roles = db.relationship('PartyRole', back_populates='party_class')

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @property
    def json(self) -> dict:
        """Return the party class as a json object."""
        return {
            'id': self.id,
            'classType': self.class_type.name,
            'shortDescription': self.short_description,
            'fullDescription': self.full_description
        }

    @classmethod
    def find_by_internal_id(cls, internal_id: int) -> PartyClass | None:
        """Return a party class by the internal id."""
        party_class = None
        if internal_id:
            party_class = cls.query.filter_by(id=internal_id).one_or_none()
        return party_class

    @classmethod
    def find_by_class_type(cls, class_type: PartyClassType) -> PartyClass | None:
        """Return a party class by the class type."""
        party_class = None
        if class_type:
            party_class = cls.query.filter_by(class_type=class_type).one_or_none()
        return party_class
