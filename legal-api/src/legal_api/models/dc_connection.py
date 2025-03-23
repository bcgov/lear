# Copyright © 2025 Province of British Columbia
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
"""This module holds data for digital credentials connections."""
from __future__ import annotations

from enum import Enum
from typing import Any, List

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
    # connection_state values we recieve in webhook, but we may not need all of it
    connection_state = db.Column('connection_state', db.String(50))
    invitation_url = db.Column('invitation_url', db.String(4096))

    is_active = db.Column('is_active', db.Boolean, default=False)
    is_attested = db.Column('is_attested', db.Boolean, default=False)
    last_attested = db.Column('last_attested', db.DateTime, default=None)

    # DEPRECATED: use business_user_id instead, remove when all references are removed
    business_id = db.Column('business_id', db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    business_user_id = db.Column('business_user_id', db.Integer, db.ForeignKey('dc_business_users.id'), nullable=False)

    # relationships
    business_user = db.relationship(
        'DCBusinessUser', backref='connections', foreign_keys=[business_user_id])

    @property
    def json(self):
        """Return a dict of this object, with keys in JSON format."""
        dc_connection = {
            'id': self.id,
            'connectionId': self.connection_id,
            'connectionState': self.connection_state,
            'invitationUrl': self.invitation_url,
            'isActive': self.is_active,
            'isAttested': self.is_attested,
            'lastAttested': self.last_attested,
            'businessId': self.business_id,  # DEPRECATED
            'businessUserId': self.business_user_id,
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
    def find_by_id(cls, connection_id: int) -> DCConnection:
        """Return the digital credential connection matching the id."""
        dc_connection = None
        if connection_id:
            dc_connection = cls.query.filter_by(id=connection_id).one_or_none()
        return dc_connection

    @classmethod
    def find_by_connection_id(cls, connection_id: str) -> DCConnection:
        """Return the digital credential connection matching the connection_id."""
        dc_connection = None
        if connection_id:
            dc_connection = cls.query.filter(DCConnection.connection_id == connection_id).one_or_none()
        return dc_connection

    @classmethod
    def find_by_business_user_id(cls, business_user_id) -> DCConnection:
        """Return the digital credential connection matching the business_user_id."""
        dc_connection = None
        if business_user_id:
            dc_connection = cls.query.filter(DCConnection.business_user_id == business_user_id).one_or_none()
        return dc_connection

    @classmethod
    def find_active_by_business_user_id(cls, business_user_id) -> DCConnection:
        """Return the active digital credential connection matching the business_user_id."""
        dc_connection = None
        if business_user_id:
            dc_connection = (
                cls.query
                   .filter(DCConnection.business_user_id == business_user_id)
                   .filter(DCConnection.is_active == True)  # noqa: E712 # pylint: disable=singleton-comparison
                   .one_or_none())
        return dc_connection

    @classmethod
    def find_state_by_business_user_id(cls, business_user_id, connection_state: DCConnection.State) -> DCConnection:
        """Return the active digital credential connection matching the business_user_id."""
        dc_connection = None
        if business_user_id:
            dc_connection = (
                cls.query
                   .filter(DCConnection.business_user_id == business_user_id)
                   .filter(DCConnection.connection_state == connection_state)
                   .one_or_none())
        return dc_connection

    @classmethod
    def find_by_filters(cls, filters: List[Any] = None) -> List[DCConnection]:
        """Return the digital credential connection matching any provided filter."""
        query = db.session.query(DCConnection)

        if filters:
            for query_filter in filters:
                query = query.filter(query_filter)

        return query.all()
