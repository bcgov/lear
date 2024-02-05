# Copyright © 2021 Province of British Columbia
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
"""Table for storing all static document details.

Documents which are static in nature are stored in file server and details will be saved in this table
"""

from __future__ import annotations

from sql_versioning import Versioned
from sqlalchemy import Column, String, desc

from ..utils.enum import BaseEnum, auto
from .db import db


class DocumentType(BaseEnum):
    """Document types."""

    COOP_RULES = auto()
    COOP_MEMORANDUM = auto()
    AFFIDAVIT = auto()
    COURT_ORDER = auto()


class Document(Versioned, db.Model):
    """This is the model for a document."""

    __tablename__ = "documents"
    __mapper_args__ = {
        "include_properties": [
            "id",
            "file_key",
            "filing_id",
            "legal_entity_id",
            "type",
            "alternate_name_id",
        ]
    }

    id = Column(db.Integer, primary_key=True)
    type = Column("type", String(30), nullable=False)
    file_key = Column("file_key", String(100), nullable=False)

    # parent keys
    legal_entity_id = db.Column("legal_entity_id", db.Integer, db.ForeignKey("legal_entities.id"), index=True)
    filing_id = db.Column("filing_id", db.Integer, db.ForeignKey("filings.id"), index=True)
    alternate_name_id = db.Column("alternate_name_id", db.Integer, db.ForeignKey("alternate_names.id"), index=True)

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, document_id: int) -> Document:
        """Return the document matching the id."""
        return cls.query.filter_by(id=document_id).one_or_none()

    @classmethod
    def find_by_legal_entity_id_and_type(cls, legal_entity_id: int, document_type: String):
        """Return the document matching the business id and type."""
        return (
            cls.query.filter_by(legal_entity_id=legal_entity_id, type=document_type)
            .order_by(desc(Document.id))
            .limit(1)
            .one_or_none()
        )
