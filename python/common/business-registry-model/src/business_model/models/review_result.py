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
"""This module holds the data about review result."""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import backref

from .db import db
from .review import Review, ReviewStatus


class ReviewResult(db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages the review result."""

    __tablename__ = 'review_results'

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column('status', db.Enum(ReviewStatus), nullable=False)
    comments = db.Column(db.Text)

    reviewer_id = db.Column('reviewer_id', db.Integer, db.ForeignKey('users.id'))
    reviewer = db.relationship('User',
                               backref=backref('reviewer', uselist=False),
                               foreign_keys=[reviewer_id])

    creation_date = db.Column('creation_date', db.DateTime(timezone=True), default=func.now())
    submission_date = db.Column('submission_date', db.DateTime(timezone=True))  # submission/re-submission date

    # parent keys
    review_id = db.Column('review_id', db.Integer, db.ForeignKey('reviews.id'), nullable=False)

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def get_review_results(cls, review_id) -> list[ReviewResult]:
        """Return review results by the review id."""
        review_results = None
        if review_id:
            review_results = (db.session.query(ReviewResult).
                              filter(ReviewResult.review_id == review_id).
                              all())
        return review_results

    @classmethod
    def get_last_review_result(cls, filing_id) -> ReviewResult:
        """Return the last review result by the filing id."""
        review_result = None
        if filing_id:
            review_result = (db.session.query(ReviewResult).join(Review).
                             filter(Review.filing_id == filing_id).
                             order_by(ReviewResult.creation_date.desc()).
                             first())
        return review_result

    @property
    def json(self) -> dict:
        """Return ReviewResult as a JSON object."""
        return {
            'status': self.status.name,
            'comments': self.comments,
            'reviewer': self.reviewer.display_name,
            'submissionDate': self.submission_date.isoformat() if self.submission_date else None,
            'creationDate': self.creation_date.isoformat()
        }
