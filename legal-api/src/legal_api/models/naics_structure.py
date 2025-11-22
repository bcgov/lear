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

from flask import current_app
from sqlalchemy import and_, or_
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import contains_eager

from .db import db
from .naics_element import NaicsElement


class NaicsStructure(db.Model):
    """Immutable NAICS Structure record.

    Represents NAICS Structure.
    """

    __tablename__ = "naics_structures"

    id = db.Column(db.Integer, primary_key=True)
    naics_key = db.Column("naics_key", UUID, nullable=False, default=uuid.uuid4)
    level = db.Column("level", db.Integer, index=True, nullable=False)
    hierarchical_structure = db.Column("hierarchical_structure", db.String(25), nullable=False)
    code = db.Column("code", db.String(10), index=True, nullable=False)
    year = db.Column("year", db.Integer, index=True, nullable=False)
    version = db.Column("version", db.Integer, index=True, nullable=False)
    class_title = db.Column("class_title", db.String(150), index=True, nullable=False)
    superscript = db.Column("superscript", db.String(5), nullable=True)
    class_definition = db.Column("class_definition", db.String(5100), index=True, nullable=False)

    # relationships
    naics_elements = db.relationship("NaicsElement")

    # json serializer
    @property
    def json(self) -> dict:
        """Return a dict of this object, with keys in JSON format."""
        naics_structures = {
            "naicsKey": self.naics_key,
            "code": self.code,
            "year": self.year,
            "version": self.version,
            "classTitle": self.class_title,
            "classDefinition": self.class_definition
        }

        elements = []
        for naics_element in self.naics_elements:
            elements.append(naics_element.json)

        naics_structures["naicsElements"] = elements
        return naics_structures

    @classmethod
    def find_by_search_term(cls, search_term: str) -> list[NaicsStructure]:
        """Return matching NAICS Structures matching search term.

        There are two main queries which can be used to return search results.  The determining factor of which query
        will be used depends on whether the search term has at least one exact match in NaicsStructure.class_title.
        """
        has_exact_match_class_title_match = cls.has_exact_match_class_title_match(search_term)

        if has_exact_match_class_title_match:
            query = cls.get_exact_match_query(search_term)
        else:
            query = cls.get_non_exact_match_query(search_term)

        results = query.all()
        return results

    @classmethod
    def has_exact_match_class_title_match(cls, search_term: str, level=5) -> bool:
        """Return whether there is at least one exact match on class title exists."""
        search_term = f"%{search_term}%"
        naics_year, naics_version = cls.get_naics_config()

        query = \
            db.session.query(NaicsStructure) \
            .filter(NaicsStructure.level == level) \
            .filter(NaicsStructure.year == naics_year) \
            .filter(NaicsStructure.version == naics_version) \
            .filter(NaicsStructure.class_title.ilike(search_term))

        first_match = query.first()
        result = bool(first_match)
        return result

    @classmethod
    def get_exact_match_query(cls, search_term: str, level=5):
        """Return NAICS Structures for scenario where at least one exact match on class title exists.

        NAICS elements associated with matching NAICS codes will be returned according to following logic:
        * if naics structure match contains exact match in NaicsStructure.class_title return all examples
        * if naics structure match does not contain exact match in NaicsStructure.class_title, only return
        examples where contains exact match in NaicsElement.element_description
        """
        naics_year, naics_version = cls.get_naics_config()
        search_term = f"%{search_term}%"

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
                                                                  NaicsElement.ElementType.ILLUSTRATIVE_EXAMPLES])
                               ).self_group(),
                               and_(
                                   NaicsStructure.class_title.notilike(search_term),
                                   NaicsElement.element_type.in_([NaicsElement.ElementType.ALL_EXAMPLES,
                                                                  NaicsElement.ElementType.ILLUSTRATIVE_EXAMPLES]),
                                   NaicsElement.element_description.ilike(search_term)
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
                        NaicsStructure.class_title.ilike(search_term)
                    ).self_group(),
                    and_(
                        NaicsElement.element_type.in_([NaicsElement.ElementType.ALL_EXAMPLES,
                                                       NaicsElement.ElementType.ILLUSTRATIVE_EXAMPLES]),
                        NaicsElement.element_description.ilike(search_term)
                    ).self_group()
                ).self_group()
            )

        return query

    @classmethod
    def get_non_exact_match_query(cls, search_term: str, level=5):
        """Return NAICS Structures for scenario where no exact match on class title exists.

        Return only elements where example desc matches one of the words in the search term.
        """
        naics_year, naics_version = cls.get_naics_config()
        search_terms = search_term.split(" ")
        search_terms = [f"%{x}%" for x in search_terms]
        search_term = f"%{search_term}%"
        naics_element_class_desc_ilike_filters = [NaicsElement.element_description.ilike(x) for x in search_terms]

        # query used to retrieve query matching 6 digit NAICS codes along with relevant NAICS elements
        query = \
            db.session.query(NaicsStructure) \
            .distinct() \
            .outerjoin(NaicsElement,  # logic used to populate NaicsElement as per logic outlined in function desc
                       and_(
                           NaicsElement.naics_structure_id == NaicsStructure.id,
                           or_(*naics_element_class_desc_ilike_filters),
                           NaicsElement.element_type.in_([NaicsElement.ElementType.ALL_EXAMPLES,
                                                          NaicsElement.ElementType.ILLUSTRATIVE_EXAMPLES])
                       ).self_group()) \
            .options(contains_eager(NaicsStructure.naics_elements)) \
            .filter(NaicsStructure.year == naics_year) \
            .filter(NaicsStructure.version == naics_version) \
            .filter(NaicsStructure.level == 5) \
            .filter(or_(*naics_element_class_desc_ilike_filters)) \
            .filter(NaicsStructure.class_title.notilike(search_term)) \
            .filter(NaicsElement.element_type.in_([NaicsElement.ElementType.ALL_EXAMPLES,
                                                   NaicsElement.ElementType.ILLUSTRATIVE_EXAMPLES]))

        return query

    @classmethod
    def find_by_code(cls, code: str, level=5) -> NaicsStructure | None:
        """Return NAICS Structure matching code and level."""
        naics_year, naics_version = cls.get_naics_config()

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
    def find_by_naics_key(cls, naics_key: str) -> NaicsStructure | None:
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

    @classmethod
    def get_naics_config(cls):
        """Return NAICS config."""
        naics_year = int(current_app.config.get("NAICS_YEAR"))
        naics_version = int(current_app.config.get("NAICS_VERSION"))

        return naics_year, naics_version
