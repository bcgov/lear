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

from sqlalchemy import Column, String, desc

from .db import db


class DocumentType(Enum):
    """Document types."""

    COOP_RULES = 'coop_rules'
    COOP_MEMORANDUM = 'coop_memorandum'
    AFFIDAVIT = 'affidavit'


class Document(db.Model):
    """This is the model for a document."""

    __versioned__ = {}
    __tablename__ = 'documents'

    id = Column(db.Integer, primary_key=True)
    type = Column('type', String(30), nullable=False)
    file_key = Column('file_key', String(100), nullable=False)
    file_name = Column('file_name', String(100), nullable=False)
    content_type = Column('content_type', String(20), nullable=False)

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
    def find_by_business_id_and_type(cls, business_id: int, type: String):
        """Return the document matching the business id and type"""
        return cls.query.filter_by(business_id=business_id, type=type).order_by(desc(Document.id)).limit(1).one_or_none()