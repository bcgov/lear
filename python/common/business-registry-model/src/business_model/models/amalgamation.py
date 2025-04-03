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
"""Meta information about the service.

Currently this only provides API versioning information
"""
from __future__ import annotations

from enum import auto

from sql_versioning import Versioned
from sqlalchemy import or_

from business_model.utils.base import BaseEnum

from .db import VersioningProxy, db


class Amalgamation(db.Model, Versioned):  # pylint: disable=too-many-instance-attributes
    """This class manages the amalgamations."""

    # pylint: disable=invalid-name
    class AmalgamationTypes(BaseEnum):
        """Enum for the amalgamation type."""

        regular = auto()
        vertical = auto()
        horizontal = auto()
        unknown = auto()

    __versioned__ = {}
    __tablename__ = 'amalgamations'

    id = db.Column(db.Integer, primary_key=True)
    amalgamation_type = db.Column('amalgamation_type', db.Enum(AmalgamationTypes), nullable=False)
    amalgamation_date = db.Column('amalgamation_date', db.DateTime(timezone=True), nullable=False)
    court_approval = db.Column('court_approval', db.Boolean())

    # parent keys
    business_id = db.Column('business_id', db.Integer, db.ForeignKey('businesses.id'), index=True)
    filing_id = db.Column('filing_id', db.Integer, db.ForeignKey('filings.id'), nullable=False)

    # Relationships
    amalgamating_businesses = db.relationship('AmalgamatingBusiness', lazy='dynamic')

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, amalgamation_id) -> Amalgamation:
        """Return amalgamation by the id."""
        amalgamation = None
        if amalgamation_id:
            amalgamation = cls.query.filter_by(id=amalgamation_id).one_or_none()
        return amalgamation

    def json(self):
        """Return amalgamation json."""
        from .business import Business  # pylint: disable=import-outside-toplevel
        business = Business.find_by_internal_id(self.business_id)

        return {
            'amalgamationDate': self.amalgamation_date.isoformat(),
            'amalgamationType': self.amalgamation_type.name,
            'courtApproval': self.court_approval,
            'identifier': business.identifier,
            'legalName': business.legal_name
        }

    @classmethod
    def get_revision_by_id(cls, amalgamation_id, transaction_id=None, tombstone=False):
        """Get amalgamation for the given id.

        If tombstone is True, get all non-versioned amalgamating for the given id.
        """
        # pylint: disable=singleton-comparison;
        if tombstone:
            amalgamation = db.session.query(Amalgamation) \
                .filter(Amalgamation.id == amalgamation_id) \
                .one_or_none()
        else:
            amalgamation_version = VersioningProxy.version_class(db.session(), Amalgamation)
            amalgamation = db.session.query(amalgamation_version) \
                .filter(amalgamation_version.transaction_id <= transaction_id) \
                .filter(amalgamation_version.operation_type == 0) \
                .filter(amalgamation_version.id == amalgamation_id) \
                .filter(or_(amalgamation_version.end_transaction_id == None,
                            amalgamation_version.end_transaction_id > transaction_id)) \
                .order_by(amalgamation_version.transaction_id).one_or_none()
        return amalgamation

    @classmethod
    def get_revision(cls, transaction_id, business_id):
        """Get amalgamation for the given transaction id."""
        # pylint: disable=singleton-comparison;
        amalgamation_version = VersioningProxy.version_class(db.session(), Amalgamation)
        amalgamation = db.session.query(amalgamation_version) \
            .filter(amalgamation_version.transaction_id <= transaction_id) \
            .filter(amalgamation_version.operation_type == 0) \
            .filter(amalgamation_version.business_id == business_id) \
            .filter(or_(amalgamation_version.end_transaction_id == None,
                        amalgamation_version.end_transaction_id > transaction_id)) \
            .order_by(amalgamation_version.transaction_id).one_or_none()
        return amalgamation

    @classmethod
    def get_revision_json(cls, transaction_id, business_id, tombstone=False):
        """Get amalgamation json for the given transaction id.

        If tombstone is True, return placeholder amalgamation json.
        """
        if tombstone:
            return {
                'identifier': 'Not Available',
                'legalName': 'Not Available',
                'amalgamationDate': 'Not Available'
            }

        amalgamation = Amalgamation.get_revision(transaction_id, business_id)
        from .business import Business  # pylint: disable=import-outside-toplevel
        business = Business.find_by_internal_id(amalgamation.business_id)

        return {
            'amalgamationDate': amalgamation.amalgamation_date.isoformat(),
            'amalgamationType': amalgamation.amalgamation_type.name,
            'courtApproval': amalgamation.court_approval,
            'identifier': business.identifier,
            'legalName': business.legal_name
        }
