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

The Comments class and Schema are held in this module.
"""
from datetime import datetime
from http import HTTPStatus

from sqlalchemy import event
from sqlalchemy.orm import backref

from legal_api.exceptions import BusinessException

from .db import db, ma
from .user import UserSchema


class Comment(db.Model):
    """This class manages the database model of storing and retrieving comments from the local DB.

    This class does NOT have a continuum shadow as comments should not be edited.
    """

    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.String(4096))
    timestamp = db.Column('timestamp', db.DateTime(timezone=True), default=datetime.utcnow)

    # parent keys
    business_id = db.Column('business_id', db.Integer, db.ForeignKey('businesses.id'), index=True)
    staff_id = db.Column('staff_id', db.Integer, db.ForeignKey('users.id'), index=True)

    # Relationships - Users
    staff = db.relationship('User',
                            backref=backref('staff_comments'),
                            foreign_keys=[staff_id])
    business_comments = db.relationship('Business',
                                        backref=backref('comments', uselist=False),
                                        foreign_keys=[business_id])

    def json(self):
        """Return the json repressentation of a comment."""
        return {
            'id': self.id,
            'staff': 'unknown' if (self.staff is None) else self.staff.username,
            'comment': self.comment,
            'timestamp': self.timestamp
        }

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    def save_to_session(self):
        """Save toThe session, do not commit immediately."""
        db.session.add(self)

    @staticmethod
    def delete():
        """Delete this object. WILL throw a BusinessException using the SQLAlchemy Listener framework."""
        raise BusinessException(
            error='Deletion not allowed.',
            status_code=HTTPStatus.FORBIDDEN
        )


@event.listens_for(Comment, 'before_delete')
def block_comment_delete_listener_function(*arg):  # pylint: disable=unused-argument
    """Raise an error when trying to delete a Comment."""
    raise BusinessException(
        error='Deletion not allowed.',
        status_code=HTTPStatus.FORBIDDEN
    )


class CommentSchema(ma.ModelSchema):
    """Marshmallow base schema for Comments."""

    class Meta:  # pylint: disable=too-few-public-methods
        """Meta class for the marshmallow schema."""

        model = Comment
        fields = ('comment', 'timestamp', 'staff', 'id')
    staff = ma.Nested(UserSchema, many=False, only='username')  # pylint: disable=no-member
