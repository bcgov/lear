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
"""This module holds all of the additional data about a continuation in."""
from __future__ import annotations

from .db import db


class ContinuationIn(db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages the continuation in."""

    __versioned__ = {}
    __tablename__ = 'continuation_ins'

    id = db.Column(db.Integer, primary_key=True)
    jurisdiction = db.Column('jurisdiction', db.String(10))
    jurisdiction_region = db.Column('jurisdiction_region', db.String(10))
    identifier = db.Column('identifier', db.String(50))
    legal_name = db.Column('legal_name', db.String(1000))
    tax_id = db.Column('tax_id', db.String(15))
    incorporation_date = db.Column('incorporation_date', db.DateTime(timezone=True))
    expro_identifier = db.Column('expro_identifier', db.String(10))
    expro_legal_name = db.Column('expro_legal_name', db.String(1000))

    # parent keys
    business_id = db.Column('business_id', db.Integer, db.ForeignKey('businesses.id'), nullable=False, index=True)
    filing_id = db.Column('filing_id', db.Integer, db.ForeignKey('filings.id'), nullable=False)

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, continuation_in_id) -> ContinuationIn:
        """Return continuation in by the id."""
        continuation_in = None
        if continuation_in_id:
            continuation_in = cls.query.filter_by(id=continuation_in_id).one_or_none()
        return continuation_in

    @classmethod
    def get_by_business_id(cls, business_id) -> ContinuationIn:
        """Return continuation in by the business id."""
        continuation_in = None
        if business_id:
            continuation_in = cls.query.filter_by(business_id=business_id).one_or_none()
        return continuation_in
