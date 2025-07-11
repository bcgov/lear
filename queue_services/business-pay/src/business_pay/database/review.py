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
"""This module holds the data about review."""
from __future__ import annotations

from enum import auto

from business_pay.utils import BaseEnum

from .db import db


class ReviewStatus(BaseEnum):
    """Render an Enum of the review status."""

    AWAITING_REVIEW = auto()
    CHANGE_REQUESTED = auto()
    RESUBMITTED = auto()
    APPROVED = auto()
    REJECTED = auto()


class Review(db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages the review."""

    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    nr_number = db.Column("nr_number", db.String(15))
    identifier = db.Column("identifier", db.String(50))
    completing_party = db.Column("completing_party", db.String(150))
    status = db.Column("status", db.Enum(ReviewStatus), nullable=False)
    submission_date = db.Column("submission_date", db.DateTime(timezone=True))
    creation_date = db.Column("creation_date", db.DateTime(timezone=True))

    # parent keys
    filing_id = db.Column(
        "filing_id", db.Integer, db.ForeignKey("filings.id"), nullable=False
    )

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()
