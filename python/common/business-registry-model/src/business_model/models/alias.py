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

from enum import Enum

from sql_versioning import Versioned

from .db import db


class Alias(db.Model, Versioned):  # pylint: disable=too-many-instance-attributes
    """This class manages the aliases."""

    class AliasType(Enum):
        """Render an Enum of the types of aliases."""

        TRANSLATION = 'TRANSLATION'

    __versioned__ = {}
    __tablename__ = 'aliases'

    id = db.Column(db.Integer, primary_key=True)
    alias = db.Column('alias', db.String(1000), index=True, nullable=False)
    type = db.Column('type', db.String(20), default=AliasType.TRANSLATION, nullable=False)

    # parent keys
    business_id = db.Column('business_id', db.Integer, db.ForeignKey('businesses.id'))

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @property
    def json(self):
        """Return a dict of this object, with keys in JSON format."""
        alias = {
            'id': str(self.id),
            'name': self.alias,
            'type': self.type
        }
        return alias

    @classmethod
    def find_by_id(cls, alias_id: int) -> Alias:
        """Return the alias matching the id."""
        alias = None
        if alias_id:
            alias = cls.query.filter_by(id=alias_id).one_or_none()
        return alias

    @classmethod
    def find_by_type(cls, business_id: int, alias_type: str):
        """Return the aliases matching the type."""
        aliases = db.session.query(Alias). \
            filter(Alias.business_id == business_id). \
            filter(Alias.type == alias_type). \
            all()
        return aliases
