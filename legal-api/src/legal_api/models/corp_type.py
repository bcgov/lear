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
"""This module holds data for corp type."""

from __future__ import annotations

from .db import db


class CorpType(db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages the corp type."""

    __tablename__ = "corp_types"

    corp_type_cd = db.Column("corp_type_cd", db.String(5), primary_key=True)
    colin_ind = db.Column("colin_ind", db.String(1), nullable=False)
    corp_class = db.Column("corp_class", db.String(10), nullable=False)
    short_desc = db.Column("short_desc", db.String(25), nullable=False)
    full_desc = db.Column("full_desc", db.String(100), nullable=False)
    legislation = db.Column("legislation", db.String(100))

    @property
    def json(self):
        """Return a dict of this object, with keys in JSON format."""
        corp_type = {
            "corp_type_cd": self.corp_type_cd,
            "colin_ind": self.colin_ind,
            "corp_class": self.corp_class,
            "short_desc": self.short_desc,
            "full_desc": self.full_desc,
            "legislation": self.legislation,
        }
        return corp_type

    @classmethod
    def find_by_id(cls, corp_type_cd: str) -> CorpType:
        """Return the corp type matching the id."""
        corp_type = None
        if corp_type_cd:
            corp_type = cls.query.filter_by(corp_type_cd=corp_type_cd).one_or_none()
        return corp_type

    @classmethod
    def find_all(cls) -> list[CorpType]:
        """Return all corp types."""
        return db.session.query(CorpType).all()
