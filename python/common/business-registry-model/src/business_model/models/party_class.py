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
"""This module holds data for party roles in a business."""
from __future__ import annotations

from sql_versioning import Versioned
from sqlalchemy import select
from sqlalchemy.orm import Mapped, mapped_column

from .db import db
from .party_role import (
    PartyRole,
)
from .types.party_class_type import PartyClassType


class PartyClass(db.Model, Versioned):
    """Class that manages data for party classes related to a PartyRole."""

    __versioned__ = {}
    __tablename__ = 'party_class'

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    class_type: Mapped[PartyClassType] = mapped_column(db.Enum(PartyClassType), nullable=False, unique=True)
    short_description: Mapped[str] = mapped_column(db.String(512))
    full_description: Mapped[str] = mapped_column(db.String(1024))

    party_roles: Mapped[list[PartyRole]] = db.relationship(back_populates="party_class")

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
            stmt = select(cls).where(cls.id == internal_id)
            party_class = db.session.execute(stmt).scalar_one_or_none()
        return party_class
    
    @classmethod
    def find_by_class_type(cls, class_type: PartyClassType) -> PartyClass | None:
        """Return a party class by the class type."""
        party_class = None
        if class_type:
            stmt = select(cls).where(cls.class_type == class_type)
            party_class = db.session.execute(stmt).scalar_one_or_none()
        return party_class
