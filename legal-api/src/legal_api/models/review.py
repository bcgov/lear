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

from dataclasses import dataclass, field
from datetime import timezone
from enum import auto
from typing import List

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
    def get_paginated_reviews(cls, review_filter, mapped_sort_by_column):
        """Return filtered, sorted and paginated reviews."""
        query = db.session.query(Review, Filing.effective_date). \
            join(Filing, Filing.id == Review.filing_id)

        if review_filter.start_date:
            start_date_utc = LegislationDatetime.as_utc_timezone_from_legislation_date_str(review_filter.start_date)
            start_of_day = datetime.combine(start_date_utc, datetime.min.time())
            query = query.filter(Review.submission_date >= start_of_day)
        if review_filter.end_date:
            end_date_utc = LegislationDatetime.as_utc_timezone_from_legislation_date_str(review_filter.end_date)
            end_of_day = datetime.combine(end_date_utc, datetime.max.time())
            query = query.filter(Review.submission_date <= end_of_day)
        if review_filter.nr_number:
            query = query.filter(Review.nr_number.ilike(f'%{review_filter.nr_number}%'))
        if review_filter.identifier:
            query = query.filter(Review.identifier.ilike(f'%{review_filter.identifier}%'))
        if review_filter.completing_party:
            query = query.filter(Review.identifier.ilike(f'%{review_filter.completing_party}%'))
        if review_filter.status:
            query = query.filter(Review.status.in_(review_filter.status))
        if review_filter.submitted_sort_by:
            column = Review.__table__.columns[mapped_sort_by_column]
            desc_sort_order = review_filter.submitted_sort_order
            query = query.order_by(column.desc() if desc_sort_order == 'true' else column.asc())
        else:
            query = query.order_by(Review.creation_date.asc())

        pagination = query.paginate(per_page=review_filter.limit, page=review_filter.page)
        results = pagination.items
        total_count = pagination.total
        result = Review.build_reviews(results)

        reviews = {
            'reviews': result,
            'page': review_filter.page,
            'limit': review_filter.limit,
            'total': total_count
        }
        return reviews

    @classmethod
    def build_reviews(cls, results):
        """Return reviews with appended future effective date."""
        result = []

        for review, effective_date in results:
            future_effective_date = ''
            if effective_date > datetime.now(timezone.utc):
                future_effective_date = effective_date.isoformat()

            result.append({
                **review.json,
                'futureEffectiveDate': future_effective_date
            })
        return result

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

    @dataclass
    class ReviewFilter:
        """Used for filtering and sorting reviews."""

        status: List[str] = field()
        start_date: str = ''
        end_date: str = ''
        nr_number: str = ''
        identifier: str = ''
        completing_party: str = ''
        submitted_sort_by: str = ''
        submitted_sort_order: bool = ''
        page: int = 1
        limit: int = 10
