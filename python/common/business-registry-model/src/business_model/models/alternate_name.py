# Copyright © 2020 Province of British Columbia
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
"""This module holds data for aliases."""
from __future__ import annotations

from sql_versioning import Versioned
from sqlalchemy.dialects.postgresql import UUID

from ..utils.enum import BaseEnum, auto
from .db import db


class AlternateName(Versioned, db.Model):
    """This class manages the alternate names."""

    class EntityType(BaseEnum):
        """Render an Enum of the types of aliases."""

        DBA = "DBA"
        SP = "DBA"
        GP = "DBA"

    class NameType(BaseEnum):
        """Enum for the name type."""

        OPERATING = auto()
        TRANSLATION = auto()

    __tablename__ = "alternate_names"
    __mapper_args__ = {
        "include_properties": [
            "id",
            "bn15",
            "change_filing_id",
            "end_date",
            "identifier",
            "legal_entity_id",
            "naics_code",
            "naics_key",
            "naics_description",
            "name",
            "name_type",
            "registration_date",
            "start_date",
        ]
    }

    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column("identifier", db.String(10), nullable=True)
    name_type = db.Column("name_type", db.Enum(NameType), nullable=False)
    name = db.Column("name", db.String(1000), nullable=False)
    bn15 = db.Column("bn15", db.String(20), nullable=True)
    start_date = db.Column("start_date", db.DateTime(timezone=True), nullable=False)
    registration_date = db.Column(
        "registration_date", db.DateTime(timezone=True), nullable=False
    )
    end_date = db.Column("end_date", db.DateTime(timezone=True), nullable=True)
    naics_code = db.Column("naics_code", db.String(10), nullable=True)
    naics_key = db.Column("naics_key", UUID, nullable=True)
    naics_description = db.Column(
        "naics_description", db.String(length=300), nullable=True
    )

    # parent keys
    legal_entity_id = db.Column(
        "legal_entity_id", db.Integer, db.ForeignKey("legal_entities.id")
    )
    change_filing_id = db.Column(
        "change_filing_id", db.Integer, db.ForeignKey("filings.id"), index=True
    )

    # relationships
    legal_entity = db.relationship("LegalEntity", back_populates="alternate_names")

    @classmethod
    def find_by_identifier(cls, identifier: str) -> AlternateName | None:
        """Return None or the AlternateName found by its registration number."""
        alternate_name = cls.query.filter_by(identifier=identifier).one_or_none()
        return alternate_name

    @classmethod
    def find_by_name(cls, name: str = None):
        """Given a name, this will return an AlternateName."""
        if not name:
            return None
        alternate_name = (
            cls.query.filter_by(name=name).filter_by(end_date=None).one_or_none()
        )
        return alternate_name

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()
