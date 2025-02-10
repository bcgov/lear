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


class Resolution(db.Model, Versioned):  # pylint: disable=too-many-instance-attributes
    """This class manages the resolutions."""

    class ResolutionType(Enum):
        """Render an Enum of the types of resolutions."""

        ORDINARY = 'ORDINARY'
        SPECIAL = 'SPECIAL'

    __versioned__ = {}
    __tablename__ = 'resolutions'

    id = db.Column(db.Integer, primary_key=True)
    resolution_date = db.Column('resolution_date', db.Date, nullable=False)
    resolution_type = db.Column('type', db.String(20), default=ResolutionType.SPECIAL, nullable=False)
    resolution_sub_type = db.Column('sub_type', db.String(20))
    signing_party_id = db.Column('signing_party_id', db.Integer, db.ForeignKey('parties.id'))
    signing_date = db.Column('signing_date', db.Date)
    resolution = db.Column(db.Text)

    # relationships
    party = db.relationship('Party')

    # parent keys
    business_id = db.Column('business_id', db.Integer, db.ForeignKey('businesses.id'))

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @property
    def json(self):
        """Return a dict of this object, with keys in JSON format."""
        resolution_json = {
            'id': self.id,
            'type': self.resolution_type,
            'date': self.resolution_date.isoformat()
        }
        if self.resolution:
            resolution_json['resolution'] = self.resolution
        if self.resolution_sub_type:
            resolution_json['subType'] = self.resolution_sub_type
        if self.signing_date:
            resolution_json['signingDate'] = self.signing_date.isoformat()
        if self.signing_party_id:
            resolution_json['signatory'] = {}
            resolution_json['signatory']['givenName'] = self.party.first_name
            resolution_json['signatory']['familyName'] = self.party.last_name
            if self.party.middle_initial:
                resolution_json['signatory']['additionalName'] = self.party.middle_initial
        return resolution_json

    @classmethod
    def find_by_id(cls, resolution_id: int) -> Resolution:
        """Return the resolution matching the id."""
        resolution = None
        if resolution_id:
            resolution = cls.query.filter_by(id=resolution_id).one_or_none()
        return resolution

    @classmethod
    def find_by_type(cls, business_id: int, resolution_type: str):
        """Return the resolutions matching the type."""
        resolutions = db.session.query(Resolution). \
            filter(Resolution.business_id == business_id). \
            filter(Resolution.resolution_type == resolution_type). \
            all()
        return resolutions

    @classmethod
    def get_all_by_business_id(cls, business_id: int):
        """Get all resolutions for a business."""
        return cls.query.filter_by(business_id=business_id).all()
