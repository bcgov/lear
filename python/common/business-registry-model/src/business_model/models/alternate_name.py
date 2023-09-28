# Copyright © 2020 Province of British Columbia
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
"""This module holds data for aliases."""
from __future__ import annotations

from sql_versioning import Versioned

from ..utils.enum import BaseEnum, auto
from .db import db


class AlternateName(Versioned, db.Model):
    """This class manages the alternate names."""

    class NameType(BaseEnum):
        """Enum for the name type."""

        OPERATING = auto()

    __tablename__ = 'alternate_names'
    __mapper_args__ = {
        'include_properties': [
            'id',
            'bn15',
            'change_filing_id',
            'end_date',
            'identifier',
            'legal_entity_id',
            'name',
            'name_type',
            'start_date',
        ]
    }

    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column('identifier', db.String(10), nullable=True)
    name_type = db.Column('name_type', db.Enum(NameType), nullable=False)
    name = db.Column('name', db.String(1000), nullable=False)
    bn15 = db.Column('bn15', db.String(20), nullable=True)
    start_date = db.Column('start_date', db.DateTime(timezone=True), nullable=False)
    end_date = db.Column('end_date', db.DateTime(timezone=True), nullable=True)

    # parent keys
    legal_entity_id = db.Column('legal_entity_id', db.Integer, db.ForeignKey('legal_entities.id'))
    change_filing_id = db.Column('change_filing_id', db.Integer, db.ForeignKey('filings.id'), index=True)

    # relationships
    legal_entity = db.relationship("LegalEntity", back_populates="_alternate_names")


    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()
