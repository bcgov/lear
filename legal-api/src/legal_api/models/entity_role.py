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
"""This module holds data for entity roles."""
from __future__ import annotations

from datetime import datetime
from enum import auto

from sql_versioning import Versioned
from sqlalchemy import Date, cast, or_

from ..utils.base import BaseEnum
from .db import db


# pylint: disable=import-outside-toplevel
class EntityRole(Versioned, db.Model):
    """This class manages the entity roles."""

    # pylint: disable=invalid-name
    class RoleTypes(BaseEnum):
        """Enum for the role type."""

        applicant = auto()
        completing_party = auto()
        custodian = auto()
        director = auto()
        incorporator = auto()
        liquidator = auto()
        proprietor = auto()
        partner = auto()

    __tablename__ = 'entity_roles'
    __mapper_args__ = {
        'include_properties': [
            'id',
            'appointment_date',
            'cessation_date',
            'change_filing_id',
            'delivery_address_id',
            'filing_id',
            'legal_entity_id',
            'mailing_address_id',
            'related_colin_entity_id',
            'related_entity_id',
            'role_type',
        ]
    }

    id = db.Column(db.Integer, primary_key=True)
    role_type = db.Column('role_type', db.Enum(RoleTypes), nullable=False)
    appointment_date = db.Column('appointment_date', db.DateTime(timezone=True), nullable=True)
    cessation_date = db.Column('cessation_date', db.DateTime(timezone=True), nullable=True)

    # parent keys
    change_filing_id = db.Column('change_filing_id', db.Integer, db.ForeignKey('filings.id'))
    delivery_address_id = db.Column('delivery_address_id', db.Integer, db.ForeignKey('addresses.id'))
    filing_id = db.Column('filing_id', db.Integer, db.ForeignKey('filings.id'))
    legal_entity_id = db.Column('legal_entity_id', db.Integer, db.ForeignKey('legal_entities.id'))
    mailing_address_id = db.Column('mailing_address_id', db.Integer, db.ForeignKey('addresses.id'))
    related_entity_id = db.Column('related_entity_id', db.Integer, db.ForeignKey('legal_entities.id'))
    related_colin_entity_id = db.Column('related_colin_entity_id', db.Integer, db.ForeignKey('colin_entities.id'))

    # relationships
    filing = db.relationship('Filing', foreign_keys=[filing_id],
                             primaryjoin="(EntityRole.filing_id==Filing.id)")
    change_filing = db.relationship('Filing', foreign_keys=[change_filing_id],
                                    primaryjoin="(EntityRole.change_filing_id==Filing.id)")
   
    legal_entity = db.relationship('LegalEntity', foreign_keys=[legal_entity_id])
    related_entity = db.relationship('LegalEntity', backref='legal_entities_related_entity',
                                     foreign_keys=[related_entity_id])
    related_colin_entity = db.relationship('ColinEntity', foreign_keys=[related_colin_entity_id])
    delivery_address = db.relationship('Address', foreign_keys=[delivery_address_id],
                                       cascade='all, delete')
    mailing_address = db.relationship('Address', foreign_keys=[mailing_address_id],
                                      cascade='all, delete')

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_by_internal_id(cls, internal_id: int) -> EntityRole:
        """Return a party role by the internal id."""
        party_role = None
        if internal_id:
            party_role = cls.query.filter_by(id=internal_id).one_or_none()
        return party_role

    # pylint: disable=too-many-arguments; one too many
    @classmethod
    def find_party_by_name(cls, legal_entity_id: int, first_name: str, last_name: str, middle_initial: str,
                           org_name: str):
        """Return a Party connected to the given legal_entity_id by the given name."""
        from legal_api.models import LegalEntity, ColinEntity

        party = None

        # the given name to find
        search_name = ''
        if org_name:
            search_name = org_name
        elif middle_initial:
            search_name = ' '.join((first_name.strip(), middle_initial.strip(), last_name.strip()))
        else:
            search_name = ' '.join((first_name.strip(), last_name.strip()))

        entity_roles \
            = cls.query \
            .join(LegalEntity, EntityRole.related_entity_id == LegalEntity.id) \
            .filter(EntityRole.legal_entity_id == legal_entity_id) \
            .all()
        for role in entity_roles:
            # the name of the party for each role
            name = role.related_entity.name
            if name and name.strip().upper() == search_name.strip().upper():
                party = role.related_entity
                return party

        entity_roles_colin \
            = cls.query \
            .join(ColinEntity, EntityRole.related_colin_entity_id == ColinEntity.id) \
            .filter(EntityRole.legal_entity_id == legal_entity_id) \
            .all()
        for role in entity_roles_colin:
            # the name of the party for each role
            name = role.related_colin_entity.name
            if name and name.strip().upper() == search_name.strip().upper():
                party = role.related_colin_entity
                return party

        return party

    @staticmethod
    def get_parties_by_role(legal_entity_id: int, role: str) -> list:
        """Return all people/organizations with the given role for this business (ceased + current)."""
        members = db.session.query(EntityRole). \
            filter(EntityRole.legal_entity_id == legal_entity_id). \
            filter(EntityRole.role_type == role). \
            all()
        return members

    @staticmethod
    def get_active_directors(legal_entity_id: int, end_date: datetime) -> list:
        """Return the active directors as of given date."""
        directors = db.session.query(EntityRole). \
            filter(EntityRole.legal_entity_id == legal_entity_id). \
            filter(EntityRole.role_type == EntityRole.RoleTypes.director). \
            filter(cast(EntityRole.appointment_date, Date) <= end_date). \
            filter(or_(EntityRole.cessation_date.is_(None), cast(EntityRole.cessation_date, Date) > end_date)). \
            all()
        return directors

    @staticmethod
    def get_entity_roles(legal_entity_id: int, end_date: datetime, role: str = None) -> list:
        """Return the parties that match the filter conditions."""
        entity_roles = db.session.query(EntityRole). \
            filter(EntityRole.legal_entity_id == legal_entity_id). \
            filter(cast(EntityRole.appointment_date, Date) <= end_date). \
            filter(or_(EntityRole.cessation_date.is_(None), cast(EntityRole.cessation_date, Date) > end_date))

        if role is not None:
            try:
                role_type = EntityRole.RoleTypes[role.lower()]
            except KeyError:
                return []
            entity_roles = entity_roles.filter(EntityRole.role_type == role_type)

        entity_roles = entity_roles.all()
        return entity_roles

    @staticmethod
    def get_entity_roles_by_party_id(legal_entity_id: int, party_id: int) -> list:
        """Return the parties that match the filter conditions."""
        entity_roles = db.session.query(EntityRole). \
            filter(EntityRole.legal_entity_id == legal_entity_id). \
            filter(or_(EntityRole.related_entity_id == party_id,
                       EntityRole.related_colin_entity_id == party_id)). \
            all()
        return entity_roles

    @staticmethod
    def get_entity_roles_by_filing(filing_id: int, end_date: datetime, role: str = None) -> list:
        """Return the parties that match the filter conditions."""
        entity_roles = db.session.query(EntityRole). \
            filter(EntityRole.filing_id == filing_id). \
            filter(cast(EntityRole.appointment_date, Date) <= end_date). \
            filter(or_(EntityRole.cessation_date.is_(None), cast(EntityRole.cessation_date, Date) > end_date))

        if role is not None:
            try:
                _ = EntityRole.RoleTypes[role.lower()]
            except KeyError:
                return []
            entity_roles = entity_roles.filter(EntityRole.role_type == role.lower())

        entity_roles = entity_roles.all()
        return entity_roles

    @property
    def is_related_colin_entity(self):
        """Return if entity role is for a colin entity."""
        return bool(self.related_colin_entity_id)

    @property
    def is_related_person(self):
        """Return if entity role is for individual entity in legal_entities table."""
        from legal_api.models import LegalEntity

        if self.related_entity_id and self.related_entity.entity_type == LegalEntity.EntityTypes.PERSON.value:
            return True

        return False

    @property
    def is_related_organization(self):
        """Return if entity role is a business in legal_entities table."""
        from legal_api.models import LegalEntity

        if self.related_entity_id and \
                self.related_entity.entity_type != LegalEntity.EntityType.PERSON.value:
            return True

        return False

    @property
    def is_filing_colin_entity(self):
        """Return if entity role is for a colin entity."""
        return bool(self.filing_id) and bool(self.related_colin_entity_id)

    @property
    def is_filing_related_person(self):
        """Return if entity role is for individual entity in legal_entities table."""
        from legal_api.models import LegalEntity

        if self.filing_id and self.legal_entity_id and \
                self.legal_entity.entity_type == LegalEntity.EntityTypes.PERSON.value:
            return True

        return False

    @property
    def is_filing_related_organization(self):
        """Return if entity role is a business in legal_entities table."""
        from legal_api.models import LegalEntity

        if self.filing_id and self.legal_entity_id and \
                self.legal_entity.entity_type != LegalEntity.EntityType.PERSON.value:
            return True

        return False

    @property
    def json(self) -> dict:
        """Return the party member as a json object."""
        party = {
            **self.related_entity.party_json,
            'appointmentDate': datetime.date(self.appointment_date).isoformat(),
            'cessationDate': datetime.date(self.cessation_date).isoformat() if self.cessation_date else None,
            'role': self.role_type.name
        }

        return party
