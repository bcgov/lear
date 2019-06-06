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
"""This manages a User record that can be used in an audit trail.

Actual user data is kept in the OIDC and IDP services, this data is
here as a convenience for audit and db reporting.
"""
from datetime import datetime

from flask import current_app

from .db import db, ma


class User(db.Model):
    """Used to hold the audit information for a User of this service."""

    __versioned__ = {}
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(1000), index=True)
    firstname = db.Column(db.String(1000))
    lastname = db.Column(db.String(1000))
    email = db.Column(db.String(1024))
    sub = db.Column(db.String(36), unique=True)
    iss = db.Column(db.String(1024))
    creation_date = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    @classmethod
    def find_by_jwt_token(cls, token: dict):
        """Return a User if they exist and match the provided JWT."""
        return cls.query.filter_by(sub=token['sub']).one_or_none()

    @classmethod
    def create_from_jwt_token(cls, token: dict):
        """Create a user record from the provided JWT token.

        Use the values found in the vaild JWT for the realm
        to populate the User audit data
        """
        if token:
            # TODO: schema doesn't parse from token need to figure that out ... LATER!
            # s = KeycloakUserSchema()
            # u = s.load(data=token, partial=True)
            user = User(
                username=token.get('username', None),
                firstname=token.get('given_name', None),
                lastname=token.get('family_name', None),
                iss=token['iss'],
                sub=token['sub']
            )
            current_app.logger.debug('Creating user from JWT:{}; User:{}'.format(token, user))
            db.session.add(user)
            db.session.commit()
            return user
        return None

    @classmethod
    def find_by_username(cls, username):
        """Return the oldest User record for the provided username."""
        return cls.query.filter_by(username=username).order_by(User.creation_date.desc()).first()

    @classmethod
    def find_by_sub(cls, sub):
        """Return a User based on the unique sub field."""
        return cls.query.filter_by(sub=sub).one_or_none()

    def save(self):
        """Store the User into the local cache."""
        db.session.add(self)
        db.session.commit()

    def delete(self):
        """Cannot delete User records."""
        return self
        # need to intercept the ORM and stop Users from being deleted


class UserSchema(ma.ModelSchema):
    """Used to manage the default mapping between JSON and Domain model."""

    class Meta:  # pylint: disable=too-few-public-methods
        """Maps all of the Domain fields to a default schema."""

        model = User
