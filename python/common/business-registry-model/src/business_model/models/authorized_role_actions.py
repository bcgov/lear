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
"""This module holds data for the authorized actions for user roles."""

from datetime import datetime

from .db import db


class AuthorizedRoleAction(db.Model):
    """This class manages all of the authorized role actions."""

    __tablename__ = 'authorized_role_actions'

    role_id = db.Column(db.Integer, db.ForeignKey('user_roles.id'), primary_key=True)
    action_id = db.Column(db.Integer, db.ForeignKey('actions.id'), primary_key=True)
    created_date = db.Column('created_date', db.DateTime(timezone=True), default=datetime.utcnow)
    last_modified = db.Column('last_modified', db.DateTime(timezone=True), default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, nullable=True)
    modified_by_id = db.Column(db.Integer, nullable=True)

    role = db.relationship('Role', back_populates='authorized_actions')
    action = db.relationship('Action', back_populates='authorized_roles')

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()
