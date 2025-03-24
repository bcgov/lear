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
"""This module holds data for share classes."""
from __future__ import annotations

from http import HTTPStatus

from sql_versioning import Versioned
from sqlalchemy import event

from business_model.exceptions import BusinessException

from .db import db
from .share_series import ShareSeries  # noqa: F401 pylint: disable=unused-import


class ShareClass(db.Model, Versioned):  # pylint: disable=too-many-instance-attributes
    """This class manages the share classes."""

    __versioned__ = {}
    __tablename__ = 'share_classes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column('name', db.String(1000), index=True)
    priority = db.Column('priority', db.Integer, nullable=True)
    max_share_flag = db.Column('max_share_flag', db.Boolean, unique=False, default=False)
    max_shares = db.Column('max_shares', db.Numeric(20), nullable=True)
    par_value_flag = db.Column('par_value_flag', db.Boolean, unique=False, default=False)
    par_value = db.Column('par_value', db.Float, nullable=True)
    currency = db.Column('currency', db.String(10), nullable=True)
    currency_additional = db.Column('currency_additional', db.String(40), nullable=True)
    special_rights_flag = db.Column('special_rights_flag', db.Boolean, unique=False, default=False)

    # parent keys
    business_id = db.Column('business_id', db.Integer, db.ForeignKey('businesses.id'))

    # Relationships
    series = db.relationship('ShareSeries',
                             backref='share_class',
                             cascade='all, delete, delete-orphan')

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
            'priority': self.priority,
            'hasMaximumShares': self.max_share_flag,
            'maxNumberOfShares': int(self.max_shares) if self.max_shares else None,
            'hasParValue': self.par_value_flag,
            'parValue': self.par_value,
            'currency': self.currency,
            'hasRightsOrRestrictions': self.special_rights_flag
        }

        series = []

        for share_series in self.series:
            series.append(share_series.json)

        share_class['series'] = series

        return share_class

    @classmethod
    def find_by_share_class_id(cls, share_class_id: int) -> ShareClass:
        """Return the share class matching the id."""
        share_class = None
        if share_class_id:
            share_class = cls.query.filter_by(id=share_class_id).one_or_none()
        return share_class


@event.listens_for(ShareClass, 'before_insert')
@event.listens_for(ShareClass, 'before_update')
def receive_before_change(mapper, connection, target):  # pylint: disable=unused-argument; SQLAlchemy callback signature
    """Run checks/updates before adding/changing the share class."""
    share_class = target

    # skip this status updater if the flag is set
    # Scenario: used for COLIN corp data migration as there is data that do not pass the following checks
    if hasattr(share_class, 'skip_share_class_listener') and share_class.skip_share_class_listener:
        return

    if share_class.max_share_flag:
        if not share_class.max_shares:
            raise BusinessException(
                error=f'The share class {share_class.name} must specify maximum number of share.',
                status_code=HTTPStatus.BAD_REQUEST
            )
    else:
        share_class.max_shares = None

    if share_class.par_value_flag:
        if not share_class.par_value:
            raise BusinessException(
                error=f'The share class {share_class.name} must specify par value.',
                status_code=HTTPStatus.BAD_REQUEST
            )
        if not share_class.currency:
            raise BusinessException(
                error=f'The share class {share_class.name} must specify currency.',
                status_code=HTTPStatus.BAD_REQUEST
            )
    else:
        share_class.par_value = None
        share_class.currency = None
        share_class.currency_additional = None
