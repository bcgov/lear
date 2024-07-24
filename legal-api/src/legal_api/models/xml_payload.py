# Copyright © 2024 Province of British Columbia
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
"""This module holds data for xml payloads."""
from __future__ import annotations

from datetime import datetime

from legal_api.models.custom_db_types import PostgreSQLXML

from .db import db


class XmlPayload(db.Model):
    """This class manages the xml_payloads."""

    __tablename__ = 'xml_payloads'

    id = db.Column(db.Integer, primary_key=True)
    payload = db.Column('payload', PostgreSQLXML(), default='', nullable=True)
    created_date = db.Column('created_date', db.DateTime(timezone=True), default=datetime.utcnow)

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, xml_payload_id: int):
        """Return a XmlPayload entry by the id."""
        xml_payload = None
        if xml_payload_id:
            xml_payload = cls.query.filter_by(id=xml_payload_id).one_or_none()
        return xml_payload
