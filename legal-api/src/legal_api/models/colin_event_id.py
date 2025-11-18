# Copyright © 2019 Province of British Columbia
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
"""This model manages the data store for colin event ids (used to link filings in lear to filings in colin).

The ColinEventId class and Schema are held in this module.
"""

from .db import db


class ColinEventId(db.Model):  # pylint: disable=too-few-public-methods
    """This table maps colin_event_ids to filing ids."""

    __tablename__ = "colin_event_ids"

    colin_event_id = db.Column("colin_event_id", db.Integer, unique=True, primary_key=True)
    filing_id = db.Column("filing_id", db.Integer, db.ForeignKey("filings.id"))

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @staticmethod
    def get_by_filing_id(filing_id):
        """Get the list of colin_event_ids linked to the given filing_id."""
        colin_event_id_objs = db.session.query(ColinEventId).filter(ColinEventId.filing_id == filing_id).all()
        id_list = []
        for obj in colin_event_id_objs:
            id_list.append(obj.colin_event_id)
        return id_list

    @staticmethod
    def get_by_colin_id(colin_id):
        """Get the ColinEventId obj with the given colin id."""
        colin_event_id_obj =\
            db.session.query(ColinEventId).filter(ColinEventId.colin_event_id == colin_id).one_or_none()
        return colin_event_id_obj
