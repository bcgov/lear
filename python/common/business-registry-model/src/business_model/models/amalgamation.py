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
"""Meta information about the service.

Currently this only provides API versioning information
"""
from __future__ import annotations

from enum import auto

from ..utils.enum import BaseEnum
from .db import db


class Amalgamation(db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages the amalgamations."""

    # pylint: disable=invalid-name
    class AmalgamationTypes(BaseEnum):
        """Enum for the amalgamation type."""

        regular = auto()
        vertical = auto()
        horizontal = auto()

    # __versioned__ = {}
    __tablename__ = "amalgamation"

    id = db.Column(db.Integer, primary_key=True)
    amalgamation_type = db.Column("amalgamation_type", db.Enum(AmalgamationTypes), nullable=False)
    amalgamation_date = db.Column("amalgamation_date", db.DateTime(timezone=True), nullable=False)
    court_approval = db.Column("court_approval", db.Boolean())

    # parent keys
    legal_entity_id = db.Column("legal_entity_id", db.Integer, db.ForeignKey("legal_entities.id"))
    filing_id = db.Column("filing_id", db.Integer, db.ForeignKey("filings.id"), nullable=False)

    # Relationships
    amalgamating_businesses = db.relationship("AmalgamatingBusiness", lazy="dynamic")

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, amalgamation_id) -> Amalgamation:
        """Return amalgamation by the id."""
        amalgamation = None
        if amalgamation_id:
            amalgamation = cls.query.filter_by(id=amalgamation_id).one_or_none()
        return amalgamation

    def json(self):
        """Return amalgamation json."""
        from .legal_entity import LegalEntity  # pylint: disable=import-outside-toplevel

        legal_entity = LegalEntity.find_by_internal_id(self.legal_entity_id)

        return {
            "amalgamationDate": self.amalgamation_date.isoformat(),
            "amalgamationType": self.amalgamation_type.name,
            "courtApproval": self.court_approval,
            "identifier": legal_entity.identifier,
            "legalName": legal_entity.legal_name,
        }
