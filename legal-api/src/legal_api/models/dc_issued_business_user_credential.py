# Copyright © 2023 Province of British Columbia
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
"""This module holds data for issued credential."""
from __future__ import annotations

from typing import List

from .db import db


class DCBusinessUser(db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages the issued credential IDs for a user of a business."""

    __tablename__ = 'dc_business_users'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column('user_id', db.Integer, db.ForeignKey('users.id'))
    business_id = db.Column('business_id', db.Integer, db.ForeignKey('businesses.id'))

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_id(cls, dc_issued_business_user_id: str) -> DCBusinessUser:
        """Return the issued business user credential matching the id."""
        dc_issued_business_user = None
        if dc_issued_business_user_id:
            dc_issued_business_user = cls.query.filter_by(id=dc_issued_business_user_id).one_or_none()
        return dc_issued_business_user

    @classmethod
    def find_by(cls,
                business_id: int = None,
                user_id: int = None) -> List[DCBusinessUser]:
        """Return the issued business user credential matching the user_id and buisness_id."""
        dc_issued_business_user_credential = None
        if business_id and user_id:
            dc_issued_business_user_credential = (
                cls.query
                .filter(DCBusinessUser.business_id == business_id)
                .filter(DCBusinessUser.user_id == user_id)
                .one_or_none())
        return dc_issued_business_user_credential
