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
from __future__ import annotations

from datetime import datetime
from enum import Enum

from sql_versioning import Versioned
from sqlalchemy import Date, cast, or_

from .db import db
from .party import (
    Party,
)


class PartyRole(db.Model, Versioned):
    """Class that manages data for party roles related to a business."""

    class RoleTypes(Enum):
        """Render an Enum of the role types."""

        APPLICANT = 'applicant'
        COMPLETING_PARTY = 'completing_party'
        CUSTODIAN = 'custodian'
        DIRECTOR = 'director'
        INCORPORATOR = 'incorporator'
        LIQUIDATOR = 'liquidator'
        PROPRIETOR = 'proprietor'
        PARTNER = 'partner'
        RECEIVER = 'receiver'
        OFFICER = 'officer'

    __versioned__ = {}
    __tablename__ = 'party_roles'

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column('role', db.String(30), default=RoleTypes.DIRECTOR)
    appointment_date = db.Column('appointment_date', db.DateTime(timezone=True))
    cessation_date = db.Column('cessation_date', db.DateTime(timezone=True))

    business_id = db.Column('business_id', db.Integer, db.ForeignKey('businesses.id'))
    filing_id = db.Column('filing_id', db.Integer, db.ForeignKey('filings.id'))
    party_id = db.Column('party_id', db.Integer, db.ForeignKey('parties.id'))

    # relationships
    party = db.relationship('Party')

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @property
    def json(self) -> dict:
        """Return the party member as a json object."""
        party = {
            **self.party.json,
            'appointmentDate': datetime.date(self.appointment_date).isoformat(),
            'cessationDate': datetime.date(self.cessation_date).isoformat() if self.cessation_date else None,
            'role': self.role
        }

        return party

    @classmethod
    def find_by_internal_id(cls, internal_id: int) -> PartyRole:
        """Return a party role by the internal id."""
        party_role = None
        if internal_id:
            party_role = cls.query.filter_by(id=internal_id).one_or_none()
        return party_role

    @classmethod
    def find_party_by_name(cls, business_id: int, first_name: str,  # pylint: disable=too-many-arguments; one too many
                           last_name: str, middle_initial: str, org_name: str) -> Party:
        """Return a Party connected to the given business_id by the given name."""
        party_roles = cls.query.filter_by(business_id=business_id).all()
        party = None
        # the given name to find
        search_name = ''
        if org_name:
            search_name = org_name
        elif middle_initial:
            search_name = ' '.join((first_name.strip(), middle_initial.strip(), last_name.strip()))
        else:
            search_name = ' '.join((first_name.strip(), last_name.strip()))

        for role in party_roles:
            # the name of the party for each role
            name = role.party.name
            if name and name.strip().upper() == search_name.strip().upper():
                party = role.party
                break

        return party

    @staticmethod
    def get_parties_by_role(business_id: int, role: str) -> list:
        """Return all people/oraganizations with the given role for this business (ceased + current)."""
        members = db.session.query(PartyRole). \
            filter(PartyRole.business_id == business_id). \
            filter(PartyRole.role == role). \
            all()
        return members

    @staticmethod
    def get_active_directors(business_id: int, end_date: datetime) -> list:
        """Return the active directors as of given date."""
        directors = db.session.query(PartyRole). \
            filter(PartyRole.business_id == business_id). \
            filter(PartyRole.role == PartyRole.RoleTypes.DIRECTOR.value). \
            filter(cast(PartyRole.appointment_date, Date) <= end_date). \
            filter(or_(PartyRole.cessation_date.is_(None), cast(PartyRole.cessation_date, Date) > end_date)). \
            all()
        return directors

    @staticmethod
    def get_party_roles(business_id: int, end_date: datetime = None, role: str = None) -> list:
        """Return the parties that match the filter conditions."""
        unsupported_roles = [
            PartyRole.RoleTypes.OFFICER.value,
            PartyRole.RoleTypes.LIQUIDATOR.value,
            PartyRole.RoleTypes.RECEIVER.value,
        ]

        party_roles = db.session.query(PartyRole). \
            filter(PartyRole.business_id == business_id)

        if end_date is not None:
            party_roles = party_roles.filter(cast(PartyRole.appointment_date, Date) <= end_date). \
                filter(or_(PartyRole.cessation_date.is_(None), cast(PartyRole.cessation_date, Date) > end_date))

        # TODO: rework the unsupported party roles section; change-on-change to still bring back these roles
        if role:
            party_roles = party_roles.filter(PartyRole.role == role.lower())
        else:
            party_roles = party_roles.filter(PartyRole.role.notin_(unsupported_roles))

        party_roles = party_roles.all()
        return party_roles

    @staticmethod
    def get_party_roles_by_party_id(business_id: int, party_id: int) -> list:
        """Return the parties that match the filter conditions."""
        party_roles = db.session.query(PartyRole). \
            filter(PartyRole.business_id == business_id). \
            filter(PartyRole.party_id == party_id). \
            all()
        return party_roles

    @staticmethod
    def get_party_roles_by_filing(filing_id: int, end_date: datetime, role: str = None) -> list:
        """Return the parties that match the filter conditions."""
        party_roles = db.session.query(PartyRole). \
            filter(PartyRole.filing_id == filing_id). \
            filter(cast(PartyRole.appointment_date, Date) <= end_date). \
            filter(or_(PartyRole.cessation_date.is_(None), cast(PartyRole.cessation_date, Date) > end_date))

        if role is not None:
            party_roles = party_roles.filter(PartyRole.role == role.lower())

        party_roles = party_roles.all()
        return party_roles
