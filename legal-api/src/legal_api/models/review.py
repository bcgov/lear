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

from datetime import timezone
from enum import auto

from legal_api.utils.base import BaseEnum
from legal_api.utils.datetime import datetime
from legal_api.utils.legislation_datetime import LegislationDatetime

from .db import db
from .filing import Filing


class ReviewStatus(BaseEnum):
    """Render an Enum of the review status."""

    AWAITING_REVIEW = auto()
    CHANGE_REQUESTED = auto()
    RESUBMITTED = auto()
    APPROVED = auto()
    REJECTED = auto()


class Review(db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages the review."""

    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    nr_number = db.Column('nr_number', db.String(15))
    identifier = db.Column('identifier', db.String(50))
    completing_party = db.Column('completing_party', db.String(150))
    status = db.Column('status', db.Enum(ReviewStatus), nullable=False)
    submission_date = db.Column('submission_date',
                                db.DateTime(timezone=True),
                                default=datetime.utcnow)  # last submission date
    creation_date = db.Column('creation_date', db.DateTime(timezone=True), default=datetime.utcnow)

    # parent keys
    filing_id = db.Column('filing_id', db.Integer, db.ForeignKey('filings.id'), nullable=False)

    # relationships
    review_results = db.relationship('ReviewResult', lazy='dynamic')

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, review_id) -> Review:
        """Return review by the id."""
        review = None
        if review_id:
            review = cls.query.filter_by(id=review_id).one_or_none()
        return review

    @classmethod
    def get_review(cls, filing_id) -> Review:
        """Return review by the filing id."""
        review = None
        if filing_id:
            review = (db.session.query(Review).
                      filter(Review.filing_id == filing_id).
                      one_or_none())
        return review

    @classmethod
    def get_paginated_reviews(cls, page, limit):
        """Return paginated reviews."""
        query = db.session.query(Review, Filing.effective_date). \
            join(Filing, Filing.id == Review.filing_id). \
            order_by(Review.creation_date.asc())

        pagination = query.paginate(per_page=limit, page=page)
        results = pagination.items
        total_count = pagination.total
        result = []

        for review, effective_date in results:
            future_effective_date = ''
            if effective_date > datetime.now(timezone.utc):
                future_effective_date = LegislationDatetime.format_as_legislation_date(effective_date)

            result.append({
                **review.json,
                'futureEffectiveDate': future_effective_date
            })

        reviews = {
            'reviews': result,
            'page': page,
            'limit': limit,
            'total': total_count
        }
        return reviews

    @property
    def json(self) -> dict:
        """Return Review as a JSON object."""
        return {
            'id': self.id,
            'nrNumber': self.nr_number,
            'identifier': self.identifier,
            'completingParty': self.completing_party,
            'status': self.status.name,
            'submissionDate': self.submission_date.isoformat(),
            'creationDate': self.creation_date.isoformat(),
            'filingId': self.filing_id,
            'results': [result.json for result in self.review_results]
        }
