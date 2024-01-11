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
"""This module holds data for resolutions."""
from __future__ import annotations

from enum import Enum

from sql_versioning import Versioned

from .db import db


class Resolution(Versioned, db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages the resolutions."""

    class ResolutionType(Enum):
        """Render an Enum of the types of resolutions."""

        ORDINARY = "ORDINARY"
        SPECIAL = "SPECIAL"

    __tablename__ = "resolutions"
    __mapper_args__ = {
        "include_properties": [
            "id",
            "change_filing_id",
            "legal_entity_id",
            "resolution",
            "resolution_date",
            "resolution_sub_type",
            "resolution_type",
            "signing_date",
            "signing_party_id",
            "signing_legal_entity_id",
        ]
    }

    id = db.Column(db.Integer, primary_key=True)
    resolution_date = db.Column("resolution_date", db.Date, nullable=False)
    resolution_type = db.Column("type", db.String(20), default=ResolutionType.SPECIAL, nullable=False)
    resolution_sub_type = db.Column("sub_type", db.String(20))
    signing_date = db.Column("signing_date", db.Date)
    resolution = db.Column(db.Text)

    # parent keys
    change_filing_id = db.Column("change_filing_id", db.Integer, db.ForeignKey("filings.id"), index=True)
    legal_entity_id = db.Column("legal_entity_id", db.Integer, db.ForeignKey("legal_entities.id"))
    signing_party_id = db.Column("signing_party_id", db.Integer, db.ForeignKey("parties.id"))
    signing_legal_entity_id = db.Column("signing_legal_entity_id", db.Integer, db.ForeignKey("legal_entities.id"))

    # relationships
    party = db.relationship("Party")
    signing_legal_entity = db.relationship(
        "LegalEntity", back_populates="resolution_signing_legal_entity", foreign_keys=[signing_legal_entity_id]
    )

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @property
    def json(self):
        """Return a dict of this object, with keys in JSON format."""
        resolution_json = {"id": self.id, "type": self.resolution_type, "date": self.resolution_date.isoformat()}
        if self.resolution:
            resolution_json["resolution"] = self.resolution
        if self.resolution_sub_type:
            resolution_json["subType"] = self.resolution_sub_type
        if self.signing_date:
            resolution_json["signingDate"] = self.signing_date.isoformat()
        if self.signing_legal_entity_id:
            resolution_json["signatory"] = {}
            resolution_json["signatory"]["givenName"] = self.signing_legal_entity.first_name
            resolution_json["signatory"]["familyName"] = self.signing_legal_entity.last_name
            if self.signing_legal_entity.middle_initial:
                resolution_json["signatory"]["additionalName"] = self.signing_legal_entity.middle_initial
        return resolution_json

    @classmethod
    def find_by_id(cls, resolution_id: int) -> Resolution:
        """Return the resolution matching the id."""
        resolution = None
        if resolution_id:
            resolution = cls.query.filter_by(id=resolution_id).one_or_none()
        return resolution

    @classmethod
    def find_by_type(cls, legal_entity_id: int, resolution_type: str):
        """Return the resolutions matching the type."""
        resolutions = (
            db.session.query(Resolution)
            .filter(Resolution.legal_entity_id == legal_entity_id)
            .filter(Resolution.resolution_type == resolution_type)
            .all()
        )
        return resolutions
