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
"""This module holds data for party roles in a business."""
from datetime import datetime
from enum import Enum

from sqlalchemy import Date, cast, or_

from .db import db


from .party_member import PartyMember  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy rel


class PartyRole(db.Model):
    """Class that manages data for party roles related to a business."""

    class RoleTypes(Enum):
        """Render an Enum of the role types."""

        DIRECTOR = 'director'

    __versioned__ = {}
    __tablename__ = 'party_roles'

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column('role', db.String(30), default=RoleTypes.DIRECTOR)
    appointment_date = db.Column('appointment_date', db.DateTime(timezone=True))
    cessation_date = db.Column('cessation_date', db.DateTime(timezone=True))

    business_id = db.Column('business_id', db.Integer, db.ForeignKey('businesses.id'))
    party_member_id = db.Column('party_member_id', db.Integer, db.ForeignKey('party_members.id'))

    # relationships
    party_member = db.relationship('PartyMember')

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @property
    def json(self):
        """Return the party member as a json object."""
        member = {
            **self.party_member.json,
            'appointmentDate': datetime.date(self.appointment_date).isoformat(),
            'cessationDate': datetime.date(self.cessation_date).isoformat() if self.cessation_date else None,
            'role': self.role
        }

        return member

    @staticmethod
    def get_by_role(business_id: int, role: RoleTypes):
        """Return all party members with the given role for this business."""
        members = db.session.query(PartyRole). \
            filter(PartyRole.business_id == business_id). \
            filter(PartyRole.role == role.value). \
            all()
        return members

    @staticmethod
    def get_active_directors(business_id: int, end_date: datetime):
        """Return the active directors as of given date."""
        directors = db.session.query(PartyRole). \
            filter(PartyRole.business_id == business_id). \
            filter(PartyRole.role == PartyRole.RoleTypes.DIRECTOR.value). \
            filter(cast(PartyRole.appointment_date, Date) <= end_date). \
            filter(or_(PartyRole.cessation_date.is_(None), cast(PartyRole.cessation_date, Date) > end_date)). \
            all()
        return directors
