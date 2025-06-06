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
"""This module holds data for user roles."""
from datetime import datetime

from business_model.utils.base import BaseEnum

from .db import db


class Role(db.Model):
    """This class manages all of the user roles."""

    class RoleType(BaseEnum):
        """Render an Enum of the user roles types."""

        CONTACT_CENTRE = 'contact_centre_staff'
        MAXIMUS = 'maximus_staff'
        PUBLIC = 'public_user'
        SBC = 'sbc_staff'
        STAFF = 'staff'

    __tablename__ = 'user_roles'

    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column('role_name', db.Enum(RoleType), nullable=False, unique=True, default=RoleType.PUBLIC)
    created_date = db.Column('created_date', db.DateTime(timezone=True), default=datetime.utcnow)
    last_modified = db.Column('last_modified', db.DateTime(timezone=True), default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, nullable=True)
    modified_by_id = db.Column(db.Integer, nullable=True)

    authorized_actions = db.relationship(
        'AuthorizedRoleAction',
        back_populates='role',
        cascade='all, delete-orphan'
    )

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()
