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
"""This module holds data for share structure (class and series)."""

from enum import Enum
from http import HTTPStatus

from sqlalchemy import event
from sqlalchemy.orm import backref

from legal_api.exceptions import BusinessException

from .db import db


class ShareStructure(db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages the share structure (class and series)."""

    class ShareStructureTypes(Enum):
        """Render an Enum of the share structure types."""

        CLASS = 'class'
        SERIES = 'series'

    __versioned__ = {}
    __tablename__ = 'share_structure'

    id = db.Column(db.Integer, primary_key=True)
    share_type = db.Column('share_type', db.String(20))
    name = db.Column('name', db.String(1000), index=True)
    priority = db.Column('priority', db.Integer)
    max_shares = db.Column('max_shares', db.Integer, nullable=True)
    par_value = db.Column('par_value', db.Float, nullable=True)
    currency = db.Column('currency', db.String(10), nullable=True)
    special_rights = db.Column('special_rights', db.Boolean, unique=False, default=False)

    # parent keys
    business_id = db.Column('business_id', db.Integer, db.ForeignKey('businesses.id'))
    parent_share_id = db.Column(db.Integer, db.ForeignKey('share_structure.id'))

    # Relationships
    parent_share = db.relationship('ShareStructure', remote_side=[id], backref=backref('series'))

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @property
    def json(self):
        """Return a dict of this object, with keys in JSON format."""
        share_class = {
            'id': self.id,
            'name': self.name,
            'shareStructureType': self.share_type,
            'priority': self.priority,
            'maxNumberOfShares': self.max_shares,
            'parValue': self.par_value,
            'currency': self.currency,
            'hasRightsOrRestrictions': self.special_rights
        }

        series = []

        for share_series in self.series:
            series.append(share_series.json)

        share_class['series'] = series

        return share_class


@event.listens_for(ShareStructure, 'before_insert')
@event.listens_for(ShareStructure, 'before_update')
def receive_before_change(mapper, connection, target):  # pylint: disable=unused-argument; SQLAlchemy callback signature
    """Run checks/updates before adding/changing the share structure."""
    share_structure = target

    if not share_structure.parent_share:
        if share_structure.share_type is None:
            share_structure.share_type = ShareStructure.ShareStructureTypes.CLASS.value
        elif share_structure.share_type != ShareStructure.ShareStructureTypes.CLASS.value:
            raise BusinessException(
                error=f'The share structure {share_structure.name} has invalid type.',
                status_code=HTTPStatus.BAD_REQUEST
            )
    else:
        if share_structure.share_type is None:
            share_structure.share_type = ShareStructure.ShareStructureTypes.SERIES.value
        elif share_structure.share_type != ShareStructure.ShareStructureTypes.SERIES.value:
            raise BusinessException(
                error=f'The share structure {share_structure.name} has invalid type.',
                status_code=HTTPStatus.BAD_REQUEST
            )
