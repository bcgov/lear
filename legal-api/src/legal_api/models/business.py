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
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref

from legal_api.exceptions import BusinessException

from .db import db, ma


from .address import Address  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy relationship
from .filing import Filing  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy backref
from .user import User  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy backref


class Business(db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages all of the base data about a business.

    A business is base form of any entity that can interact directly
    with people and other businesses.
    Businesses can be sole-proprietors, corporations, societies, etc.
    """

    __versioned__ = {}
    __tablename__ = 'businesses'

    id = db.Column(db.Integer, primary_key=True)
    last_modified = db.Column('last_modified', db.DateTime(timezone=True), default=datetime.utcnow)
    last_ledger_id = db.Column('last_ledger_id', db.Integer)
    last_remote_ledger_id = db.Column('last_remote_ledger_id', db.Integer, default=0)
    last_ar_date = db.Column('last_ar_date', db.DateTime(timezone=True), default=datetime.utcnow)
    legal_name = db.Column('legal_name', db.String(1000), index=True)
    founding_date = db.Column('founding_date', db.DateTime(timezone=True), default=datetime.utcnow)
    dissolution_date = db.Column('dissolution_date', db.DateTime(timezone=True), default=None)
    _identifier = db.Column('identifier', db.String(10), index=True)
    tax_id = db.Column('tax_id', db.String(15), index=True)
    fiscal_year_end_date = db.Column('fiscal_year_end_date', db.DateTime(timezone=True), default=datetime.utcnow)

    submitter_userid = db.Column('submitter_userid', db.Integer, db.ForeignKey('users.id'))
    submitter = db.relationship('User', backref=backref('submitter', uselist=False), foreign_keys=[submitter_userid])

    # relationships
    filings = db.relationship('Filing', lazy='dynamic')
    business_mailing_address = db.relationship('Address', lazy='dynamic')

    @hybrid_property
    def identifier(self):
        """Return the unique business identifier."""
        return self._identifier

    @identifier.setter
    def identifier(self, value: str):
        """Set the business identifier."""
        if Business.validate_identifier(value):
            self._identifier = value
        else:
            raise BusinessException('invalid-identifier-format', 406)

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
            business = cls.query.filter_by(identifier=identifier).one_or_none()
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

    def json(self):
        """Return the Business as a json object.

        None fields are not included.
        """
        d = {
            'foundingDate': self.founding_date.isoformat(),
            'identifier': self.identifier,
            'lastModified': self.last_modified.isoformat(),
            'legalName': self.legal_name,
        }
        # if self.last_remote_ledger_timestamp:
        #     # this is not a typo, we want the external facing view object ledger timestamp to be the remote one
        #     d['last_ledger_timestamp'] = self.last_remote_ledger_timestamp.isoformat()
        # else:
        #     d['last_ledger_timestamp'] = None

        if self.dissolution_date:
            d['dissolutionDate'] = datetime.date(self.dissolution_date).isoformat()
        if self.fiscal_year_end_date:
            d['fiscalYearEndDate'] = datetime.date(self.fiscal_year_end_date).isoformat()
        if self.tax_id:
            d['taxId'] = self.tax_id
        mailing = self.business_mailing_address.one_or_none()
        if mailing:
            d['mailingAddress'] = mailing.json

        return d

    @staticmethod
    def validate_identifier(identifier: str) -> bool:
        """Validate the identifier meets the Registry naming standards.

        All legal entities with BC Reg are PREFIX + 7 digits

        CP = BC COOPS prefix;
        XCP = Expro COOP prefix

        Examples:
            ie: CP1234567 or XCP1234567

        """
        if len(identifier) < 9:
            return False

        try:
            d = int(identifier[-7:])
            if d == 0:
                return False
        except ValueError:
            return False

        if identifier[:-7] not in ('CP', 'XCP'):
            return False

        return True


class BusinessSchema(ma.ModelSchema):
    """Main schema used to serialize the Business."""

    class Meta:  # pylint: disable=too-few-public-methods
        """Returns all the fields from the SQLAlchemy class."""

        model = Business
