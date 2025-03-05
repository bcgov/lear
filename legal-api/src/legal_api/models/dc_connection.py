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
# limitations under the License.
"""This module holds data for digital credentials connection."""
from __future__ import annotations

from enum import Enum
from typing import List

from .db import db


class DCConnection(db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages the digital credentials connection."""

    class State(Enum):
        """Enum of the didexchange protocol states."""

        START = 'start'  # altough there is a start state we never see it
        INVITATION_SENT = 'invitation-sent'
        REQUEST_RECEIVED = 'request-received'
        RESPONSE_SENT = 'response-sent'
        ABANDONED = 'abandoned'
        COMPLETED = 'completed'
        ACTIVE = 'active'  # artifact from the connection protocol

    __tablename__ = 'dc_connections'

    id = db.Column(db.Integer, primary_key=True)
    connection_id = db.Column('connection_id', db.String(100))
    invitation_url = db.Column('invitation_url', db.String(4096))
    is_active = db.Column('is_active', db.Boolean, default=False)

    # connection_state values we recieve in webhook, but we may not need all of it
    connection_state = db.Column('connection_state', db.String(50))

    business_id = db.Column('business_id', db.Integer,
                            db.ForeignKey('businesses.id'))

    is_attested = db.Column('is_attested', db.Boolean, default=False)
    last_attested = db.Column('last_attested', db.DateTime, default=None)

    @property
    def json(self):
        """Return a dict of this object, with keys in JSON format."""
        dc_connection = {
            'id': self.id,
            'businessId': self.business_id,
            'connectionId': self.connection_id,
            'invitationUrl': self.invitation_url,
            'isActive': self.is_active,
            'connectionState': self.connection_state,
            'isAttested': self.is_attested,
            'lastAttested': self.last_attested
        }
        return dc_connection

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    def delete(self):
        """Delete the object from the database immediately."""
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, dc_connection_id: str) -> DCConnection:
        """Return the digital credential connection matching the id."""
        dc_connection = None
        if dc_connection_id:
            dc_connection = cls.query.filter_by(
                id=dc_connection_id).one_or_none()
        return dc_connection

    @classmethod
    def find_by_connection_id(cls, connection_id: str) -> DCConnection:
        """Return the digital credential connection matching the connection_id."""
        dc_connection = None
        if connection_id:
            dc_connection = cls.query.filter(
                DCConnection.connection_id == connection_id).one_or_none()
        return dc_connection

    @classmethod
    def find_active_by(cls, business_id: str) -> DCConnection:
        """Return the active digital credential connection matching the business_id."""
        dc_connection = None
        if business_id:
            dc_connection = (
              cls.query
                 .filter(DCConnection.business_id == business_id)
                 .filter(DCConnection.is_active == True)  # noqa: E712 # pylint: disable=singleton-comparison
                 .one_or_none())
        return dc_connection

    @classmethod
    def find_by(cls,
                business_id: int = None,
                connection_state: str = None) -> List[DCConnection]:
        """Return the digital credential connection matching the filter."""
        query = db.session.query(DCConnection)

        if business_id:
            query = query.filter(DCConnection.business_id == business_id)

        if connection_state:
            query = query.filter(
                DCConnection.connection_state == connection_state)

        return query.all()
