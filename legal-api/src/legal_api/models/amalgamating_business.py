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

from enum import auto

from sql_versioning import Versioned
from sqlalchemy import or_
from sqlalchemy_continuum import version_class

from ..utils.base import BaseEnum
from .db import db


class AmalgamatingBusiness(db.Model, Versioned):  # pylint: disable=too-many-instance-attributes
    """This class manages the amalgamating businesses."""

    # pylint: disable=invalid-name
    class Role(BaseEnum):
        """Enum for the Role Values."""

        amalgamating = auto()
        holding = auto()
        primary = auto()

    __versioned__ = {}
    __tablename__ = 'amalgamating_businesses'

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column('role', db.Enum(Role), nullable=False)
    foreign_jurisdiction = db.Column('foreign_jurisdiction', db.String(10))
    foreign_jurisdiction_region = db.Column('foreign_jurisdiction_region', db.String(10))
    foreign_name = db.Column('foreign_name', db.String(100))
    foreign_identifier = db.Column('foreign_identifier', db.String(50))

    # parent keys
    business_id = db.Column('business_id', db.Integer, db.ForeignKey('businesses.id'), index=True)
    amalgamation_id = db.Column('amalgamation_id', db.Integer, db.ForeignKey('amalgamations.id',
                                                                             ondelete='CASCADE'),
                                nullable=False)

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def get_revision(cls, transaction_id, amalgamation_id):
        """Get amalgamating businesses for the given transaction id."""
        # pylint: disable=singleton-comparison;
        amalgamating_businesses_version = version_class(AmalgamatingBusiness)
        amalgamating_businesses = db.session.query(amalgamating_businesses_version) \
            .filter(amalgamating_businesses_version.transaction_id <= transaction_id) \
            .filter(amalgamating_businesses_version.operation_type == 0) \
            .filter(amalgamating_businesses_version.amalgamation_id == amalgamation_id) \
            .filter(or_(amalgamating_businesses_version.end_transaction_id == None,  # noqa: E711;
                        amalgamating_businesses_version.end_transaction_id > transaction_id)) \
            .order_by(amalgamating_businesses_version.transaction_id).all()
        return amalgamating_businesses

    @classmethod
    def get_all_revision(cls, business_id, tombstone=False):
        """
        Get all amalgamating businesses for the given business id.

        ie:
        1. Business T1 is dissolved as part of amalgamation
        2. Put back on T1 with a court order
        3. Business T1 is dissolved as part of another amalgamation

        In this case T1 is involved in 2 amalgamation

        If tombstone is True, get all non-versioned amalgamating businesses
        for the given business id. 
        """
        if tombstone:
            amalgamating_businesses = db.session.query(AmalgamatingBusiness) \
            .filter(AmalgamatingBusiness.business_id == business_id) \
            .all()
        else:
            amalgamating_businesses_version = version_class(AmalgamatingBusiness)
            amalgamating_businesses = db.session.query(amalgamating_businesses_version) \
                .filter(amalgamating_businesses_version.operation_type == 0) \
                .filter(amalgamating_businesses_version.business_id == business_id) \
                .order_by(amalgamating_businesses_version.transaction_id).all()
        return amalgamating_businesses
