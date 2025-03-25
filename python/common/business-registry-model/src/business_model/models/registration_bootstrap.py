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
"""This module holds all of the basic data about a temporary registration.

The RegistrationBoostrap class and Schema are held in this module
"""
from datetime import datetime

from sqlalchemy.ext.hybrid import hybrid_property

from business_model.exceptions import BusinessException

from .db import db
from .filing import Filing  # noqa: F401,I003 pylint: disable=unused-import; needed by the SQLAlchemy backref
from .user import User  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy backref


class RegistrationBootstrap(db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages a temporary registration.

    Used to bootstrap a business registration.

    A business is base form of any entity that can interact directly
    with people and other businesses.
    Businesses can be sole-proprietors, corporations, societies, etc.
    """

    __tablename__ = 'registration_bootstrap'

    _identifier = db.Column('identifier', db.String(10), primary_key=True)
    account = db.Column('account', db.Integer, index=True)
    last_modified = db.Column('last_modified', db.DateTime(timezone=True), default=datetime.utcnow)

    # relationships
    filings = db.relationship('Filing', lazy='dynamic')

    @hybrid_property
    def identifier(self):
        """Return the unique business identifier."""
        return self._identifier

    @identifier.setter
    def identifier(self, value: str):
        """Set the business identifier."""
        if RegistrationBootstrap.validate_identifier(value):
            self._identifier = value
        else:
            raise BusinessException('invalid-identifier-format', 406)

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
        """Render a Business to the local cache."""
        db.session.delete(self)
        db.session.commit()

    def json(self):
        """Return the Business as a json object."""
        return {
            'identifier': self.identifier,
            'lastModified': self.last_modified.isoformat(),
        }

    @staticmethod
    def validate_identifier(identifier: str) -> bool:
        """Validate the identifier is a temporary format."""
        if identifier[:1] == 'T' and len(identifier) <= 10:
            return True

        return False
