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

from .base import EntityCommonBase
from ..utils.enum import BaseEnum, auto
from .db import db


class AlternateName(Versioned, db.Model, EntityCommonBase):
    """This class manages the alternate names."""

    class NameType(BaseEnum):
        """Enum for the name type."""

        OPERATING = auto()

    __tablename__ = "alternate_names"
    __mapper_args__ = {
        "include_properties": [
            "id",
            "bn15",
            "change_filing_id",
            "end_date",
            "identifier",
            "legal_entity_id",
            "name",
            "name_type",
            "start_date",
            "naics_key",
            "naics_code",
            "naics_description"
        ]
    }

    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column("identifier", db.String(10), nullable=True)
    name_type = db.Column("name_type", db.Enum(NameType), nullable=False)
    name = db.Column("name", db.String(1000), nullable=False)
    bn15 = db.Column("bn15", db.String(20), nullable=True)
    start_date = db.Column("start_date", db.DateTime(timezone=True), nullable=False)
    end_date = db.Column("end_date", db.DateTime(timezone=True), nullable=True)
    naics_key = db.Column("naics_key", db.String(50), nullable=True)
    naics_code = db.Column("naics_code", db.String(10), nullable=True)
    naics_description = db.Column("naics_description", db.String(300), nullable=True)

    # parent keys
    legal_entity_id = db.Column("legal_entity_id", db.Integer, db.ForeignKey("legal_entities.id"))
    change_filing_id = db.Column("change_filing_id", db.Integer, db.ForeignKey("filings.id"), index=True)

    # relationships
    legal_entity = db.relationship("LegalEntity", back_populates="_alternate_names")

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_identifier(cls, identifier: str) -> AlternateName | None:
        """Return None or the AlternateName found by its registration number."""
        alternate_name = cls.query.filter_by(identifier=identifier).one_or_none()
        return alternate_name


    def json(self, slim=False):
        """Return the Business as a json object.

        None fields are not included.
        """
        # TODO flesh out json fully once all additional columns added to this model
        slim_json = self._slim_json()
        if slim:
            return slim_json

        d = {
            **slim_json,
            "warnings": self.warnings,
            "allowedActions": self.allowable_actions,
        }

        return d

    def _slim_json(self):
        """Return a smaller/faster version of the business json."""
        legal_name = self.legal_entity.legal_name if self.legal_entity else None
        d = {
            "legalType": self.entity_type,
            "identifier": self.identifier,
            "legalName": legal_name,
            "alternateNames": [
                {
                    "identifier": self.identifier,
                    "operatingName": self.name,
                    "entityType": 'SP',
                    "nameRegisteredDate": self.start_date.isoformat(),
                }
            ]
        }
        return d

