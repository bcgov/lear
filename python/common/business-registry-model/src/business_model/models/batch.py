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
"""This module holds data for batch."""
from __future__ import annotations

from enum import auto
from typing import List

from sqlalchemy import func

from business_model.utils.base import BaseEnum
from business_model.utils.datetime import datetime

from .db import db


class Batch(db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages the batch."""

    class BatchType(BaseEnum):
        """Render an Enum of the batch type."""

        INVOLUNTARY_DISSOLUTION = auto()

    class BatchStatus(BaseEnum):
        """Render an Enum of the batch status."""

        HOLD = auto()
        PROCESSING = auto()
        COMPLETED = auto()
        CANCELLED = auto()
        ERROR = auto()

    __tablename__ = 'batches'

    id = db.Column(db.Integer, primary_key=True)
    batch_type = db.Column('batch_type', db.Enum(BatchType), nullable=False)
    status = db.Column('status', db.Enum(BatchStatus), nullable=False)
    size = db.Column('size', db.Integer, nullable=True)
    start_date = db.Column('start_date', db.DateTime(timezone=True),  default=func.now())
    end_date = db.Column('end_date', db.DateTime(timezone=True), nullable=True)
    notes = db.Column('notes', db.String(150), default='', nullable=True)
    max_size = db.Column('max_size', db.Integer, nullable=True)

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, batch_id: int):
        """Return the batch matching the id."""
        batch = None
        if batch_id:
            batch = cls.query.filter_by(id=batch_id).one_or_none()
        return batch

    @classmethod
    def find_by(cls,  # pylint: disable=too-many-arguments
                batch_type: BatchType = None,
                status: BatchStatus = None) -> List[Batch]:
        """Return the batch matching."""
        query = db.session.query(Batch)
        batches = []

        if batch_type:
            query = query.filter(Batch.batch_type == batch_type)

        if status:
            query = query.filter(Batch.status == status)

        batches = query.order_by(Batch.id).all()
        return batches
