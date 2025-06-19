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

from enum import Enum

from sql_versioning import Versioned
from sqlalchemy import desc

from .db import db


class DocumentType(Enum):
    """Document types."""

    AFFIDAVIT = 'affidavit'
    AUTHORIZATION_FILE = 'authorization_file'
    COOP_RULES = 'coop_rules'
    COOP_MEMORANDUM = 'coop_memorandum'
    COURT_ORDER = 'court_order'
    DIRECTOR_AFFIDAVIT = 'director_affidavit'


class Document(db.Model, Versioned):
    """This is the model for a document."""

    __versioned__ = {}
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column('type', db.String(30), nullable=False)
    file_key = db.Column('file_key', db.String(100), nullable=False)
    file_name = db.Column('file_name', db.String(1000))

    # parent keys
    business_id = db.Column('business_id', db.Integer, db.ForeignKey('businesses.id'), index=True)
    filing_id = db.Column('filing_id', db.Integer, db.ForeignKey('filings.id'), index=True)

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, document_id: int) -> Document:
        """Return the document matching the id."""
        return cls.query.filter_by(id=document_id).one_or_none()

    @classmethod
    def find_all_by(cls, filing_id: int, document_type: str):
        """Return all the documents matching filing id and document type."""
        return cls.query.filter_by(filing_id=filing_id, type=document_type).all()

    @classmethod
    def find_by_business_id_and_type(cls, business_id: int, document_type: str):
        """Return the document matching the business id and type."""
        return cls.query.filter_by(
            business_id=business_id,
            type=document_type
        ).order_by(desc(Document.id)).first()

    @classmethod
    def find_by_file_key(cls, file_key: str):
        """Return the document matching the file key."""
        return cls.query.filter_by(file_key=file_key).one_or_none()

    @classmethod
    def find_one_by(cls, business_id: int, filing_id: int, document_type: str):
        """Return the document matching the business id, filing id and document type."""
        return cls.query.filter_by(
            business_id=business_id,
            filing_id=filing_id,
            type=document_type
        ).order_by(desc(Document.id)).first()