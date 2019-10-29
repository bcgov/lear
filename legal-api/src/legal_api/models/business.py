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

import datedelta
from sqlalchemy.exc import OperationalError, ResourceClosedError
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref

from legal_api.exceptions import BusinessException

from .db import db, ma


from .director import Director  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy relationship
from .address import Address  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy relationship
from .filing import Filing  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy backref
from .user import User  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy backref
from .office import Office  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy relationship

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
    last_ledger_timestamp = db.Column('last_ledger_timestamp', db.DateTime(timezone=True), default=datetime.utcnow)
    last_ar_date = db.Column('last_ar_date', db.DateTime(timezone=True))
    last_agm_date = db.Column('last_agm_date', db.DateTime(timezone=True))
    legal_name = db.Column('legal_name', db.String(1000), index=True)
    legal_type = db.Column('legal_type', db.String(10))
    founding_date = db.Column('founding_date', db.DateTime(timezone=True), default=datetime.utcnow)
    dissolution_date = db.Column('dissolution_date', db.DateTime(timezone=True), default=None)
    _identifier = db.Column('identifier', db.String(10), index=True)
    tax_id = db.Column('tax_id', db.String(15), index=True)
    fiscal_year_end_date = db.Column('fiscal_year_end_date', db.DateTime(timezone=True), default=datetime.utcnow)

    submitter_userid = db.Column('submitter_userid', db.Integer, db.ForeignKey('users.id'))
    submitter = db.relationship('User', backref=backref('submitter', uselist=False), foreign_keys=[submitter_userid])

    # relationships
    filings = db.relationship('Filing', lazy='dynamic')
    directors = db.relationship('Director', lazy='dynamic')
    offices = db.relationship('Office', lazy='dynamic')

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

    @property
    def next_anniversary(self):
        """Retrieve the next anniversary date for which an AR filing is due."""
        last_anniversary = self.founding_date
        if self.last_ar_date:
            last_anniversary = self.last_ar_date

        return last_anniversary + datedelta.datedelta(years=1)

    @property
    def mailing_address(self):
        registered_office = db.session.query(Office).filter(Office.business_id == self.id).\
            filter(Office.office_type == 'registeredOffice').one_or_none()
        if registered_office:
            return registered_office.addresses.filter(Address.address_type == 'mailing')

        return db.session.query(Address).filter(Address.business_id == self.id).\
            filter(Address.address_type == Address.MAILING)

    @property
    def delivery_address(self):
        registered_office = db.session.query(Office).filter(Office.business_id == self.id).\
            filter(Office.office_type == 'registeredOffice').one_or_none()
        if registered_office:
            return registered_office.addresses.filter(Address.address_type == 'delivery')

        return db.session.query(Address).filter(Address.business_id == self.id).\
            filter(Address.address_type == Address.DELIVERY)

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

    @classmethod
    def find_by_internal_id(cls, internal_id: int = None):
        """Return a Business by the internal id."""
        business = None
        if internal_id:
            business = cls.query.filter_by(id=internal_id).one_or_none()
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
            'lastAnnualReport': datetime.date(self.last_ar_date).isoformat() if self.last_ar_date else '',
            'nextAnnualReport': self.next_anniversary.isoformat(),
            'lastAnnualGeneralMeetingDate': datetime.date(self.last_agm_date).isoformat() if self.last_agm_date else '',
            'lastLedgerTimestamp': self.last_ledger_timestamp.isoformat(),
            'legalName': self.legal_name,
            'legalType': self.legal_type,
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

        return d

    @classmethod
    def get_filing_by_id(cls, business_identifier: int, filing_id: str):
        """Return the filings for a specific business and filing_id."""
        filing = db.session.query(Business, Filing). \
            filter(Business.id == Filing.business_id). \
            filter(Business.identifier == business_identifier). \
            filter(Filing.id == filing_id). \
            one_or_none()
        return None if not filing else filing[1]

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
        # TODO This is not correct for entity types that are not Coops
        if identifier[:-7] not in ('CP', 'XCP'):
            return False

        return True


class BusinessSchema(ma.ModelSchema):
    """Main schema used to serialize the Business."""

    class Meta:  # pylint: disable=too-few-public-methods
        """Returns all the fields from the SQLAlchemy class."""

        model = Business
