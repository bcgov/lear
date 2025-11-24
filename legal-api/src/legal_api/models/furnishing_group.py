# Copyright © 2024 Province of British Columbia
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
"""This module holds data for furnishing groups."""
from __future__ import annotations

from .db import db


class FurnishingGroup(db.Model):
    """This class manages the furnishing groups."""

    __tablename__ = "furnishing_groups"

    id = db.Column(db.Integer, primary_key=True)

    # parent keys
    xml_payload_id = db.Column("xml_payload_id", db.Integer, db.ForeignKey("xml_payloads.id"),
                               index=True, nullable=True)

    # relationships
    xml_payload = db.relationship("XmlPayload", backref=db.backref("furnishing_groups", lazy=True))

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, furnishing_group_id: int):
        """Return a Furnishing entry by the id."""
        furnishing_group = None
        if furnishing_group_id:
            furnishing_group = cls.query.filter_by(id=furnishing_group_id).one_or_none()
        return furnishing_group

    @classmethod
    def find_by(cls,  # pylint: disable=too-many-arguments
                xml_payload_id: int | None = None
                ) -> list[FurnishingGroup]:
        """Return the Furnishing entries matching the filter."""
        query = db.session.query(FurnishingGroup)

        if xml_payload_id:
            query = query.filter(FurnishingGroup.xml_payload_id == xml_payload_id)

        return query.all()
