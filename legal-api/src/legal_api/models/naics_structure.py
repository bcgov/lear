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
# limitations under the License
"""Immutable NAICS Structure record.

NaicsStructure is a representation of a NAICS code along with hierarchy and element info.

A NAICS code can have up to 6 digits. The breakdown:

The 1st and 2nd numbers = economic sector
The 3rd number = sub-sector
The 4th number = industry group
The 5th number = industry
The 6th number = national industry (a zero indicates no national industry is needed)
"""
from __future__ import annotations

import uuid
from typing import Optional

from flask import current_app
from sqlalchemy import and_, or_
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import contains_eager

from .db import db  # noqa: I001
from .naics_element import NaicsElement


class NaicsStructure(db.Model):
    """Immutable NAICS Structure record.

    Represents NAICS Structure.
    """

    __tablename__ = 'naics_structures'

    id = db.Column(db.Integer, primary_key=True)
    naics_key = db.Column('naics_key', UUID, nullable=False, default=uuid.uuid4)
    level = db.Column('level', db.Integer, index=True, nullable=False)
    hierarchical_structure = db.Column('hierarchical_structure', db.String(25), nullable=False)
    code = db.Column('code', db.String(10), index=True, nullable=False)
    year = db.Column('year', db.Integer, index=True, nullable=False)
    version = db.Column('version', db.Integer, index=True, nullable=False)
    class_title = db.Column('class_title', db.String(150), index=True, nullable=False)
    superscript = db.Column('superscript', db.String(5), nullable=True)
    class_definition = db.Column('class_definition', db.String(5100), index=True, nullable=False)

    # relationships
    naics_elements = db.relationship('NaicsElement')

    # json serializer
    @property
    def json(self) -> dict:
        """Return a dict of this object, with keys in JSON format."""
        naics_structures = {
            'naicsKey': self.naics_key,
            'code': self.code,
            'year': self.year,
            'version': self.version,
            'classTitle': self.class_title,
            'classDefinition': self.class_definition
        }

        elements = []
        for naics_element in self.naics_elements:
            elements.append(naics_element.json)

        naics_structures['naicsElements'] = elements
        return naics_structures

    @classmethod
    def find_by_search_term(cls, search_term: str) -> list[NaicsStructure]:
        """Return matching NAICS Structures matching search term.

        NAICS elements associated with matching NAICS codes will be returned according to following logic:
        * if naics structure match contains search term in NaicsStructure.class_title return all examples
        * if naics structure match does not contain search term in NaicsStructure.class_title, only return
        examples where NaicsElement.class_title or NaicsElement.element_description contains search term
        """
        naics_year = int(current_app.config.get('NAICS_YEAR'))
        naics_version = int(current_app.config.get('NAICS_VERSION'))
        search_term = f'%{search_term}%'

        # query used to retrieve query matching 6 digit NAICS codes along with relevant NAICS elements
        query = \
            db.session.query(NaicsStructure) \
            .distinct() \
            .outerjoin(NaicsElement,  # logic used to populate NaicsElement as per logic outlined in function desc
                       and_(
                           NaicsElement.naics_structure_id == NaicsStructure.id,
                           or_(
                               and_(
                                   NaicsStructure.class_title.ilike(search_term),
                                   NaicsElement.element_type.in_([NaicsElement.ElementType.ALL_EXAMPLES,
                                                                  NaicsElement.ElementType.ILLUSTRATIVE_EXAMPLES]),
                               ).self_group(),
                               and_(
                                   NaicsStructure.class_title.notilike(search_term),
                                   NaicsElement.element_type.in_([NaicsElement.ElementType.ALL_EXAMPLES,
                                                                 NaicsElement.ElementType.ILLUSTRATIVE_EXAMPLES]),
                                   or_(
                                       NaicsElement.class_title.ilike(search_term),
                                       NaicsElement.element_description.ilike(search_term)
                                   )
                               ).self_group()
                           ).self_group()
                       ).self_group()) \
            .options(contains_eager(NaicsStructure.naics_elements)) \
            .filter(NaicsStructure.year == naics_year) \
            .filter(NaicsStructure.version == naics_version) \
            .filter(NaicsStructure.level == 5) \
            .filter(  # core logic to determine which NaicsStructure records to return in addition to year and level
                or_(
                    or_(
                        NaicsStructure.class_title.ilike(search_term),
                        NaicsStructure.class_definition.ilike(search_term)
                    ).self_group(),
                    and_(
                        NaicsElement.element_type.in_([NaicsElement.ElementType.ALL_EXAMPLES,
                                                       NaicsElement.ElementType.ILLUSTRATIVE_EXAMPLES]),
                        or_(
                            NaicsElement.class_title.ilike(search_term),
                            NaicsElement.element_description.ilike(search_term)
                        )
                    ).self_group()
                ).self_group()
            )

        results = query.all()
        return results

    @classmethod
    def find_by_code(cls, code: str, level=5) -> Optional[NaicsStructure]:
        """Return NAICS Structure matching code and level."""
        naics_year = int(current_app.config.get('NAICS_YEAR'))
        naics_version = int(current_app.config.get('NAICS_VERSION'))

        query = \
            db.session.query(NaicsStructure) \
            .join(NaicsElement) \
            .options(contains_eager(NaicsStructure.naics_elements)) \
            .filter(NaicsStructure.level == level) \
            .filter(NaicsStructure.year == naics_year) \
            .filter(NaicsStructure.version == naics_version) \
            .filter(NaicsStructure.code == code) \
            .filter(NaicsElement.element_type.in_([NaicsElement.ElementType.ALL_EXAMPLES,
                                                   NaicsElement.ElementType.ILLUSTRATIVE_EXAMPLES]))

        result = query.one_or_none()
        return result

    @classmethod
    def find_by_naics_key(cls, naics_key: str) -> Optional[NaicsStructure]:
        """Return NAICS Structure matching naics_key."""
        query = \
            db.session.query(NaicsStructure) \
            .join(NaicsElement) \
            .options(contains_eager(NaicsStructure.naics_elements)) \
            .filter(NaicsStructure.naics_key == naics_key) \
            .filter(NaicsElement.element_type.in_([NaicsElement.ElementType.ALL_EXAMPLES,
                                                   NaicsElement.ElementType.ILLUSTRATIVE_EXAMPLES]))

        result = query.one_or_none()
        return result
