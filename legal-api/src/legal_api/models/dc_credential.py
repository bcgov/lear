# Copyright © 2025 Province of British Columbia
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
"""This module holds data for digital credentials."""
from __future__ import annotations

from typing import Any, List

from sqlalchemy.dialects.postgresql import JSONB

from .db import db


class DCCredential(db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages the digital credential."""

    __tablename__ = 'dc_credentials'

    id = db.Column(db.Integer, primary_key=True)
    credential_id = db.Column('credential_id', db.String(10))
    connection_id = db.Column('connection_id', db.Integer, db.ForeignKey(
        'dc_connections.id'), nullable=False)
    credential_exchange_id = db.Column(
        'credential_exchange_id', db.String(100))
    definition_id = db.Column('definition_id', db.Integer, db.ForeignKey(
        'dc_definitions.id'), nullable=False)

    credential_revocation_id = db.Column(
        'credential_revocation_id', db.String(10))
    revocation_registry_id = db.Column(
        'revocation_registry_id', db.String(200))

    credential_json = db.Column('raw_data', JSONB)
    self_attested_roles = db.Column('self_attested_roles', JSONB)

    is_issued = db.Column('is_issued', db.Boolean, default=False)
    date_of_issue = db.Column('date_of_issue', db.DateTime(timezone=True))
    is_revoked = db.Column('is_revoked', db.Boolean, default=False)
    date_of_revocation = db.Column(
        'date_of_revocation', db.DateTime(timezone=True))

    business_user_id = db.Column('business_user_id', db.Integer, db.ForeignKey(
        'dc_business_users.id'), nullable=False)

    # relationships
    connection = db.relationship(
        'DCConnection', backref='credentials', foreign_keys=[connection_id])
    definition = db.relationship(
        'DCDefinition', backref='credentials', foreign_keys=[definition_id])

    @property
    def json(self):
        """Return a dict of this object, with keys in JSON format."""
        dc_credential = {
            'id': self.id,
            'credentialId': self.credential_id,
            'connectionId': self.connection_id,
            'credentialExchangeId': self.credential_exchange_id,
            'definitionId': self.definition_id,
            'isIssued': self.is_issued,
            'dateOfIssue': self.date_of_issue.isoformat() if self.date_of_issue else None,
            'isRevoked': self.is_revoked,
            'credentialRevocationId': self.credential_revocation_id,
            'revocationRegistryId': self.revocation_registry_id
        }
        return dc_credential

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    def delete(self):
        """Delete the object from the database immediately."""
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, credential_id: str) -> DCCredential:
        """Return the digital credential matching the id."""
        dc_credential = None
        if credential_id:
            dc_credential = cls.query.filter_by(
                id=credential_id).one_or_none()
        return dc_credential

    @classmethod
    def find_by_credential_exchange_id(cls, credential_exchange_id: str) -> DCCredential:
        """Return the digital credential matching the credential exchange id."""
        dc_credential = None
        if credential_exchange_id:
            dc_credential = cls.query. \
                filter(DCCredential.credential_exchange_id ==
                       credential_exchange_id).one_or_none()
        return dc_credential

    @classmethod
    def find_by_credential_id(cls, credential_id: str) -> DCCredential:
        """Return the digital credential matching the credential id."""
        dc_credential = None
        if credential_id:
            dc_credential = cls.query. \
                filter(DCCredential.credential_id ==
                       credential_id).one_or_none()
        return dc_credential

    @classmethod
    def find_by_connection_id(cls, connection_id: str) -> DCCredential:
        """Return the digital credential matching the connection id."""
        dc_credential = None
        if connection_id:
            dc_credential = cls.query. \
                filter(DCCredential.connection_id ==
                       connection_id).one_or_none()
        return dc_credential

    @classmethod
    def find_by_filters(cls, filters: List[Any] = None) -> List[DCCredential]:
        """Return the digital credential matching any provided filter."""
        query = db.session.query(DCCredential)

        if filters:
            for query_filter in filters:
                query = query.filter(query_filter)

        return query.all()