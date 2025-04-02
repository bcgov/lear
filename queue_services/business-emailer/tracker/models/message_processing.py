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
"""This model manages the data store for staff comments.

The MessageProcessing class and Schema are held in this module.
"""


from datetime import datetime
from enum import Enum
from sqlalchemy.dialects.postgresql import JSONB

from . import db


class MessageProcessing(db.Model):
    """This class manages the database model of storing and retrieving message_processing items from the local DB.

    """

    __bind_key__ = 'tracker'

    class Status(Enum):
        """Render an Enum of the Status Codes."""

        PROCESSING = 'PROCESSING'
        FAILED = 'FAILED'
        COMPLETE = 'COMPLETE'

    __tablename__ = 'message_processing'

    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(36), index=True)
    message_id = db.Column(db.String(60), unique=True, index=True)
    identifier = db.Column(db.String(36), index=True)
    message_type = db.Column(db.String(35), index=True)
    status = db.Column(db.String(10), index=True)
    message_json = db.Column('message_json', JSONB)
    message_seen_count = db.Column(db.Integer, default=1)
    last_error = db.Column(db.String(1000))
    create_date = db.Column('create_date', db.DateTime(timezone=True), default=datetime.utcnow)
    last_update = db.Column('last_update', db.DateTime(timezone=True), default=datetime.utcnow)

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    def save_to_session(self):
        """Save toThe session, do not commit immediately."""
        db.session.add(self)


    @staticmethod
    def find_message_by_message_id(message_id: str):
        """Return a MessageProcessing by message_id."""
        q = db.session.query(MessageProcessing).filter_by(message_id=message_id)
        result = q.one_or_none()
        return result


    @staticmethod
    def find_message_by_source_and_message_id(source: str, message_id: str):
        """Return a MessageProcessing by source and message id."""
        q = db.session.query(MessageProcessing)\
            .filter_by(source=source,
                       message_id=message_id)
        result = q.one_or_none()
        return result
