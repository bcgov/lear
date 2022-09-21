# Copyright © 2022 Province of British Columbia
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
"""This module holds data for issued credential."""
from __future__ import annotations

from typing import List

from .db import db


class DCIssuedCredential(db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages the issued credential."""

    __tablename__ = 'dc_issued_credentials'

    id = db.Column(db.Integer, primary_key=True)

    dc_definition_id = db.Column('dc_definition_id', db.Integer, db.ForeignKey('dc_definitions.id'))
    dc_connection_id = db.Column('dc_connection_id', db.Integer, db.ForeignKey('dc_connections.id'))

    credential_exchange_id = db.Column('credential_exchange_id', db.String(100))
    credential_id = db.Column('credential_id', db.String(100))  # not in use
    is_issued = db.Column('is_issued', db.Boolean, default=False)
    date_of_issue = db.Column('date_of_issue', db.DateTime(timezone=True))

    is_revoked = db.Column('is_revoked', db.Boolean, default=False)

    @property
    def json(self):
        """Return a dict of this object, with keys in JSON format."""
        dc_issued_credential = {
            'id': self.id,
            'dcDefinitionId': self.dc_definition_id,
            'dcConnectionId': self.dc_connection_id,
            'credentialExchangeId': self.credential_exchange_id,
            'isIssued': self.is_issued,
            'dateOfIssue': self.date_of_issue.isoformat(),
            'isRevoked': self.is_revoked
        }
        return dc_issued_credential

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, dc_issued_credential_id: str) -> DCIssuedCredential:
        """Return the issued credential matching the id."""
        dc_issued_credential = None
        if dc_issued_credential_id:
            dc_issued_credential = cls.query.filter_by(id=dc_issued_credential_id).one_or_none()
        return dc_issued_credential

    @classmethod
    def find_by_credential_exchange_id(cls, credential_exchange_id: str) -> DCIssuedCredential:
        """Return the issued credential matching the id."""
        dc_issued_credential = None
        if credential_exchange_id:
            dc_issued_credential = cls.query. \
                filter(DCIssuedCredential.credential_exchange_id == credential_exchange_id).one_or_none()
        return dc_issued_credential

    @classmethod
    def find_by(cls,
                dc_definition_id: int = None,
                dc_connection_id: int = None) -> List[DCIssuedCredential]:
        """Return the issued credential matching the filter."""
        query = db.session.query(DCIssuedCredential)

        if dc_definition_id:
            query.filter(DCIssuedCredential.dc_definition_id == dc_definition_id)

        if dc_connection_id:
            query.filter(DCIssuedCredential.dc_connection_id == dc_connection_id)

        return query.all()
