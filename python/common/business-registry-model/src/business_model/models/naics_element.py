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
"""NaicsElement are used to associate additional information to a given NAICS code at a given level.

Element types can be examples, illustrative examples, inclusions and exclusions.
"""
from enum import auto

from business_model.utils.base import BaseEnum

from .db import db  # noqa: I001


class NaicsElement(db.Model):
    """Immutable NAICS Element record.

    Represents NAICS Element.
    """

    class ElementType(BaseEnum):
        """Render an Enum of the Element Types."""

        ALL_EXAMPLES = auto()
        ILLUSTRATIVE_EXAMPLES = auto()
        INCLUSIONS = auto()
        EXCLUSIONS = auto()

    __tablename__ = 'naics_elements'

    id = db.Column(db.Integer, primary_key=True)
    level = db.Column('level', db.Integer, index=True, nullable=False)
    code = db.Column('code', db.String(10), index=True, nullable=False)
    year = db.Column('year', db.Integer, index=True, nullable=False)
    version = db.Column('version', db.Integer, index=True, nullable=False)
    class_title = db.Column('class_title', db.String(150), index=True, nullable=False)
    element_type = db.Column('element_type', db.Enum(ElementType), index=True, nullable=False)
    element_description = db.Column('element_description', db.String(500), index=True, nullable=False)

    # parent keys
    naics_structure_id = db.Column('naics_structure_id', db.Integer, db.ForeignKey('naics_structures.id'), index=True)

    # json serializer
    @property
    def json(self):
        """Return a dict of this object, with keys in JSON format."""
        naics_element = {
            'code': self.code,
            'year': self.year,
            'version': self.version,
            'classTitle': self.class_title,
            'elementType': self.element_type.name,
            'elementDescription': self.element_description
        }
        return naics_element
