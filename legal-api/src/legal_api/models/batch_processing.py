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
"""This module holds data for batch processing."""
from enum import auto

from sqlalchemy.dialects.postgresql import JSONB

from legal_api.utils.base import BaseEnum
from legal_api.utils.datetime import datetime

from .db import db


class BatchProcessing(db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages the batch processing."""

    class BatchProcessingStep(BaseEnum):
        """Render an Enum of the batch processing step."""

        WARNING_LEVEL_1 = auto()
        WARNING_LEVEL_2 = auto()
        DISSOLUTION = auto()

    class BatchProcessingStatus(BaseEnum):
        """Render an Enum of the batch processing status."""

        HOLD = auto()
        PROCESSING = auto()
        WITHDRAWN = auto()
        COMPLETED = auto()
        ERROR = auto()

    __tablename__ = 'batch_processing'

    id = db.Column(db.Integer, primary_key=True)
    business_identifier = db.Column('business_identifier', db.String(10), default='', nullable=False)
    step = db.Column('step', db.Enum(BatchProcessingStep), nullable=False)
    status = db.Column('status', db.Enum(BatchProcessingStatus), nullable=False)
    notes = db.Column('notes', db.String(150), default='', nullable=True)
    created_date = db.Column('created_date', db.DateTime(timezone=True), default=datetime.utcnow)
    trigger_date = db.Column('trigger_date', db.DateTime(timezone=True), nullable=True)
    last_modified = db.Column('last_modified', db.DateTime(timezone=True), default=datetime.utcnow)
    meta_data = db.Column('meta_data', JSONB, nullable=True)

    # parent keys
    batch_id = db.Column('batch_id', db.Integer, db.ForeignKey('batches.id'), index=True, nullable=False)
    business_id = db.Column('business_id', db.Integer, db.ForeignKey('businesses.id'), index=True, nullable=False)
    filing_id = db.Column('filing_id', db.Integer, db.ForeignKey('filings.id'), index=True, nullable=True)

    # relationships
    business = db.relationship('Business', back_populates='batch_processing')

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, batch_processing_id: int):
        """Return the batch matching the id."""
        batch_processing = None
        if batch_processing_id:
            batch_processing = cls.query.filter_by(id=batch_processing_id).one_or_none()
        return batch_processing

    @classmethod
    def find_by(cls,  # pylint: disable=too-many-arguments
                batch_id: int = None,
                business_id: int = None,
                filing_id: int = None,
                step: BatchProcessingStep = None,
                status: BatchProcessingStatus = None) -> dict:
        """Return the batch matching."""
        query = db.session.query(BatchProcessing)
        batch_processinges = []

        if batch_id:
            query = query.filter(BatchProcessing.batch_id == batch_id)

        if business_id:
            query = query.filter(BatchProcessing.business_id == business_id)

        if filing_id:
            query = query.filter(BatchProcessing.filing_id == filing_id)

        if step:
            query = query.filter(BatchProcessing.step == step)

        if status:
            query = query.filter(BatchProcessing.status == status)

        batch_processinges = query.order_by(BatchProcessing.id).all()
        return batch_processinges
