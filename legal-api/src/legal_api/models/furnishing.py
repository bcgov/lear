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
"""This module holds data for furnishings."""
from __future__ import annotations

from enum import auto
from typing import List

from sqlalchemy.dialects.postgresql import JSONB

from legal_api.utils.base import BaseEnum
from legal_api.utils.datetime import datetime

from .db import db


class Furnishing(db.Model):
    """This class manages the furnishings."""

    class FurnishingType(BaseEnum):
        """Render an Enum for the furnishing type."""

        EMAIL = auto()
        MAIL = auto()
        GAZETTE = auto()

    class FurnishingName(BaseEnum):
        """Render an Enum for the furnishing name."""

        DISSOLUTION_COMMENCEMENT_NO_AR = auto()
        DISSOLUTION_COMMENCEMENT_NO_TR = auto()
        DISSOLUTION_COMMENCEMENT_NO_AR_XPRO = auto()
        DISSOLUTION_COMMENCEMENT_NO_TR_XPRO = auto()
        INTENT_TO_DISSOLVE = auto()
        INTENT_TO_DISSOLVE_XPRO = auto()
        CORP_DISSOLVED = auto()
        CORP_DISSOLVED_XPRO = auto()

    class FurnishingStatus(BaseEnum):
        """Render an Enum for the furnishing status."""

        QUEUED = auto()
        PROCESSED = auto()
        FAILED = auto()

    __tablename__ = 'furnishings'

    id = db.Column(db.Integer, primary_key=True)
    furnishing_type = db.Column('furnishing_type', db.Enum(FurnishingType), nullable=False)
    furnishing_name = db.Column('furnishing_name', db.Enum(FurnishingName), nullable=False)
    grouping_identifier = db.Column(db.Integer, nullable=True)
    business_identifier = db.Column('business_identifier', db.String(10), default='', nullable=False)
    processed_date = db.Column('processed_date', db.DateTime(timezone=True), nullable=True)
    status = db.Column('status', db.Enum(FurnishingStatus), nullable=False)
    notes = db.Column('notes', db.String(150), default='', nullable=True)
    meta_data = db.Column('meta_data', JSONB, nullable=True)
    created_date = db.Column('created_date', db.DateTime(timezone=True), default=datetime.utcnow)
    last_modified = db.Column('last_modified', db.DateTime(timezone=True), default=datetime.utcnow)
    email = db.Column('email', db.String(254), default='', nullable=True)
    last_name = db.Column('last_name', db.String(30), default='', nullable=True)
    first_name = db.Column('first_name', db.String(30), default='', nullable=True)
    middle_name = db.Column('middle_name', db.String(30), default='', nullable=True)
    last_ar_date = db.Column('last_ar_date', db.DateTime(timezone=True), nullable=True)
    business_name = db.Column('business_name', db.String(1000), nullable=True)

    # parent keys
    batch_id = db.Column('batch_id', db.Integer, db.ForeignKey('batches.id'), index=True, nullable=False)
    business_id = db.Column('business_id', db.Integer, db.ForeignKey('businesses.id'), index=True, nullable=False)

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, furnishing_id: int):
        """Return a Furnishing entry by the id."""
        furnishing = None
        if furnishing_id:
            furnishing = cls.query.filter_by(id=furnishing_id).one_or_none()
        return furnishing

    @classmethod
    def find_by(cls,  # pylint: disable=too-many-arguments
                batch_id: int = None,
                business_id: int = None,
                furnishing_name: str = None,
                furnishing_type: str = None,
                status: str = None,
                grouping_identifier: int = None
                ) -> List[Furnishing]:
        """Return the Furnishing entries matching the filter."""
        query = db.session.query(Furnishing)

        if batch_id:
            query = query.filter(Furnishing.batch_id == batch_id)

        if business_id:
            query = query.filter(Furnishing.business_id == business_id)

        if furnishing_name:
            query = query.filter(Furnishing.furnishing_name == furnishing_name)

        if furnishing_type:
            query = query.filter(Furnishing.furnishing_type == furnishing_type)

        if status:
            query = query.filter(Furnishing.status == status)

        if grouping_identifier:
            query = query.filter(Furnishing.grouping_identifier == grouping_identifier)

        return query.all()

    @classmethod
    def get_next_grouping_identifier(cls):
        """Return the next grouping_identifier from the sequence."""
        return db.session.execute("SELECT nextval('grouping_identifier')").scalar()
