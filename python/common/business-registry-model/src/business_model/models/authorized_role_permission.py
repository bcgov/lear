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
"""This module holds data for the authorized permissions for user roles."""

from sqlalchemy import func

from .db import db


class AuthorizedRolePermission(db.Model):
    """This class manages all of the authorized role permissions."""

    __tablename__ = 'authorized_role_permissions'

    role_id = db.Column(db.Integer, db.ForeignKey('authorized_roles.id'), primary_key=True)
    permission_id = db.Column(db.Integer, db.ForeignKey('permissions.id'), primary_key=True)
    created_date = db.Column('created_date', db.DateTime(timezone=True), default=func.now())
    last_modified = db.Column('last_modified', db.DateTime(timezone=True), onupdate=func.now(), default=func.now())
    created_by_id = db.Column(db.Integer, nullable=True)
    modified_by_id = db.Column(db.Integer, nullable=True)

    role = db.relationship('AuthorizedRole', back_populates='permissions')
    permission = db.relationship('Permission', back_populates='authorized_roles')

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def get_authorized_permissions_by_role_name(cls, role_name):
        """Return a list of authorized permissions for a given role."""
        from .permission import Permission  # pylint: disable=import-outside-toplevel
        from .authorized_role import AuthorizedRole  # pylint: disable=import-outside-toplevel

        authorized_permissions = (
            db.session.query(Permission)
            .join(cls, cls.permission_id == Permission.id)
            .join(AuthorizedRole, AuthorizedRole.id == cls.role_id)
            .filter(AuthorizedRole.role_name == role_name)
            .all()
        )
        return [ap.permission_name for ap in authorized_permissions]
