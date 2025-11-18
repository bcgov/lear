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
"""This module holds data for digitial credentials business users."""

from __future__ import annotations

from typing import List

from .db import db


class DCBusinessUser(db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages the user of a business that has a digital credential."""

    __tablename__ = "dc_business_users"

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column("business_id", db.Integer, db.ForeignKey("businesses.id"), nullable=False)
    user_id = db.Column("user_id", db.Integer, db.ForeignKey("users.id"), nullable=False)

    # relationships
    business = db.relationship("Business", backref="business_users", foreign_keys=[business_id])
    user = db.relationship("User", backref="business_users", foreign_keys=[user_id])

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, business_user_id: str) -> DCBusinessUser:
        """Return the business user matching the id."""
        business_user = None
        if business_user_id:
            business_user = cls.query.filter_by(id=business_user_id).one_or_none()
        return business_user

    @classmethod
    def find_by(cls, business_id: int = None, user_id: int = None) -> List[DCBusinessUser]:
        """Return the business user matching the user_id and buisness_id."""
        business_user = None
        if business_id and user_id:
            business_user = (
                cls.query.filter(DCBusinessUser.business_id == business_id)
                .filter(DCBusinessUser.user_id == user_id)
                .one_or_none()
            )
        return business_user
