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
"""This module holds data for digital credentials schemas and credential definitions."""
from __future__ import annotations

from enum import auto

from legal_api.utils.base import BaseEnum

from .db import db


class DCDefinition(db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages the digital credentials schema and credential definition."""

    __tablename__ = 'dc_definitions'

    class CredentialType(BaseEnum):
        """Render an Enum of the Credential Type."""

        # pylint: disable=invalid-name
        business = auto()
        business_relationship = auto()

    id = db.Column(db.Integer, primary_key=True)
    schema_id = db.Column('schema_id', db.String(100))
    schema_name = db.Column('schema_name', db.String(50))
    schema_version = db.Column('schema_version', db.String(10))
    credential_definition_id = db.Column('credential_definition_id', db.String(100))
    credential_type = db.Column('credential_type', db.Enum(CredentialType), nullable=False)

    is_deleted = db.Column('is_deleted', db.Boolean, default=False)

    @property
    def json(self):
        """Return a dict of this object, with keys in JSON format."""
        dc_definition = {
            'id': self.id,
            'schemaId': self.schema_id,
            'schemaName': self.schema_name,
            'schemaVersion': self.schema_version,
            'credentialDefinitionId': self.credential_definition_id,
            'credentialType': self.credential_type.name,
            'isDeleted': self.is_deleted
        }
        return dc_definition

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, definition_id: str) -> DCDefinition:
        """Return the digital credential definition matching the id."""
        dc_definition = None
        if definition_id:
            dc_definition = cls.query.filter_by(id=definition_id).one_or_none()
        return dc_definition

    @classmethod
    def find_by_credential_type(cls, credential_type: CredentialType) -> DCDefinition:
        """Return the digital credential definition matching the credential_type."""
        dc_definition = None
        if credential_type:
            dc_definition = (
                cls.query
                   .filter(DCDefinition.credential_type == credential_type)
                   .filter(DCDefinition.is_deleted == False)  # noqa: E712 # pylint: disable=singleton-comparison
                   .one_or_none())
        return dc_definition

    @classmethod
    def find_by(cls,
                credential_type: CredentialType,
                schema_id: str,
                credential_definition_id: str,
                ) -> DCDefinition:
        """Return the digital credential definition matching the filter."""
        query = (
            db.session.query(DCDefinition)
                      .filter(DCDefinition.credential_type == credential_type)
                      .filter(DCDefinition.schema_id == schema_id)
                      .filter(DCDefinition.credential_definition_id == credential_definition_id)
                      .filter(DCDefinition.is_deleted == False))  # noqa: E712 # pylint: disable=singleton-comparison
        return query.one_or_none()

    @classmethod
    def deactivate(cls, credential_type: CredentialType):
        """Deactivate all definition for the specific credential type."""
        db.session.execute(f"UPDATE dc_definitions SET is_deleted=true WHERE credential_type='{credential_type.name}'")
