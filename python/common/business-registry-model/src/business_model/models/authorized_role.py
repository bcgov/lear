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
"""This module holds data for authorized roles."""
from sqlalchemy import func

from .db import db


class AuthorizedRole(db.Model):
    """This class manages all of the authorized roles."""

    __tablename__ = 'authorized_roles'

    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column('role_name', db.String(50), nullable=False, unique=True, default='public_user')
    created_date = db.Column('created_date', db.DateTime(timezone=True), default=func.now())
    last_modified = db.Column('last_modified', db.DateTime(timezone=True), onupdate=func.now(), default=func.now())
    created_by_id = db.Column(db.Integer, nullable=True)
    modified_by_id = db.Column(db.Integer, nullable=True)

    permissions = db.relationship(
        'AuthorizedRolePermission',
        back_populates='role',
        cascade='all, delete-orphan'
    )

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()
