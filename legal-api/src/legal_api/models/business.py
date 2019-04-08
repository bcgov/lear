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
"""This module holds all of the basic data about a business.

The Business class and Schema are held in this module
"""

from datetime import datetime

from sqlalchemy.exc import OperationalError, ResourceClosedError

from .db import db, ma


class Business(db.Model):
    """This class manages all of the base data about a business.

    A business is base form of any entity that can interact directly
    with people and other businesses.
    Businesses can be sole-propritors, corporations, societies, etc.
    """

    __tablename__ = 'business'

    id = db.Column(db.Integer, primary_key=True)
    last_update = db.Column('last_update', db.DateTime(timezone=True), default=None)
    legal_name = db.Column('legal_name', db.String(1000), index=True)
    founding_date = db.Column('founding_date', db.DateTime(timezone=True), default=datetime.utcnow)
    dissolution_date = db.Column('dissolution_date', db.DateTime(timezone=True), default=None)
    identifier = db.Column('identifier', db.String(10), index=True)
    tax_id = db.Column('tax_id', db.String(15), index=True)
    fiscal_year_end_date = db.Column('fiscal_year_end_date', db.DateTime(timezone=True), default=datetime.utcnow)

    # Status(Not in compliance / In good standing / Pending Dissolution)
    # Type of Cooperative

    @classmethod
    def find_by_legal_name(cls, legal_name: str = None):
        """Given a legal_name, this will return an Active Business."""
        business = None
        if legal_name:
            try:
                business = cls.query.filter_by(legal_name=legal_name).\
                    filter_by(dissolution_date=None).one_or_none()
            except (OperationalError, ResourceClosedError):
                # TODO: This usually means a misconfigured database.
                # This is not a business error if the cache is unavailable.
                return None
        return business

    @classmethod
    def find_by_identifier(cls, identifier: str = None):
        """Return a Business by the id assigned by the Registrar."""
        business = None
        if identifier:
            business = cls.query.filter_by(identifier=identifier).\
                filter_by(dissolution_date=None).one_or_none()
        return business

    def save(self):
        """Render a Business to the local cache."""
        db.session.add(self)
        db.session.commit()

    def delete(self):
        """Businesses cannot be deleted.

        TODO: Hook SQLAlchemy to block deletes
        """
        if self.dissolution_date:
            self.save()
        return self


class BusinessSchema(ma.ModelSchema):
    """Main schema used to serialize the Business."""

    class Meta:  # pylint: disable=too-few-public-methods
        """Returns all the fields from the SQLAlchemy class."""

        model = Business
