# Copyright © 2020 Province of British Columbia
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
"""This module holds data for aliases."""
from __future__ import annotations

from enum import auto

from flask import current_app
from sql_versioning import Versioned
from sqlalchemy.dialects.postgresql import UUID

from ..utils.base import BaseEnum
from ..utils.datetime import datetime
from ..utils.legislation_datetime import LegislationDatetime
from .address import Address  # noqa: F401,I003 pylint: disable=unused-import; needed by the SQLAlchemy relationship
from .business_common import BusinessCommon
from .db import db
from .office import Office  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy relationship


# pylint: disable=import-outside-toplevel
class AlternateName(Versioned, db.Model, BusinessCommon):
    """This class manages the alternate names."""

    class EntityType(BaseEnum):
        """Render an Enum of the types of aliases."""

        DBA = "DBA"
        SP = "SP"
        GP = "GP"

    class NameType(BaseEnum):
        """Enum for the name type."""

        OPERATING = auto()
        TRANSLATION = auto()

    __tablename__ = "alternate_names"
    __mapper_args__ = {
        "include_properties": [
            "id",
            "bn15",
            "change_filing_id",
            "end_date",
            "identifier",
            "legal_entity_id",
            "colin_entity_id",
            "name",
            "name_type",
            "start_date",
            "naics_key",
            "naics_code",
            "naics_description",
            "business_start_date",
            "dissolution_date",
            "state",
            "state_filing_id",
            "admin_freeze",
            "last_modified",
            "email",
            "delivery_address_id",
            "mailing_address_id",
        ]
    }

    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column("identifier", db.String(10), nullable=True, index=True)
    name_type = db.Column("name_type", db.Enum(NameType), nullable=False)
    name = db.Column("name", db.String(1000), nullable=False, index=True)
    bn15 = db.Column("bn15", db.String(20), nullable=True)
    start_date = db.Column("start_date", db.DateTime(timezone=True), nullable=False)
    end_date = db.Column("end_date", db.DateTime(timezone=True), nullable=True)
    naics_code = db.Column("naics_code", db.String(10), nullable=True)
    naics_key = db.Column("naics_key", UUID, nullable=True)
    naics_description = db.Column("naics_description", db.String(300), nullable=True)
    business_start_date = db.Column("business_start_date", db.DateTime(timezone=True), default=datetime.utcnow)
    dissolution_date = db.Column("dissolution_date", db.DateTime(timezone=True), default=None)
    state = db.Column("state", db.Enum(BusinessCommon.State), default=BusinessCommon.State.ACTIVE.value)
    admin_freeze = db.Column("admin_freeze", db.Boolean, unique=False, default=False)
    last_modified = db.Column("last_modified", db.DateTime(timezone=True), default=datetime.utcnow)
    email = db.Column("email", db.String(254), nullable=True)
    delivery_address_id = db.Column("delivery_address_id", db.Integer, db.ForeignKey("addresses.id"))
    mailing_address_id = db.Column("mailing_address_id", db.Integer, db.ForeignKey("addresses.id"))

    # parent keys
    legal_entity_id = db.Column("legal_entity_id", db.Integer, db.ForeignKey("legal_entities.id"))
    colin_entity_id = db.Column("colin_entity_id", db.Integer, db.ForeignKey("colin_entities.id"))
    change_filing_id = db.Column("change_filing_id", db.Integer, db.ForeignKey("filings.id"), index=True)
    state_filing_id = db.Column("state_filing_id", db.Integer, db.ForeignKey("filings.id"))

    # relationships
    legal_entity = db.relationship("LegalEntity", back_populates="alternate_names")
    colin_entity = db.relationship("ColinEntity", back_populates="alternate_names")
    filings = db.relationship("Filing", lazy="dynamic", foreign_keys="Filing.alternate_name_id")
    documents = db.relationship("Document", lazy="dynamic")

    delivery_address = db.relationship("Address", foreign_keys=[delivery_address_id])
    mailing_address = db.relationship("Address", foreign_keys=[mailing_address_id])

    @classmethod
    def find_by_identifier(cls, identifier: str) -> AlternateName | None:
        """Return None or the AlternateName found by its registration number."""
        alternate_name = cls.query.filter_by(identifier=identifier).one_or_none()
        return alternate_name

    @classmethod
    def find_by_internal_id(cls, internal_id: int) -> AlternateName | None:
        """Return None or the AlternateName found by the internal id."""
        alternate_name = cls.query.filter_by(id=internal_id).one_or_none()
        return alternate_name

    @classmethod
    def find_by_name(cls, name: str = None):
        """Given a name, this will return an AlternateName."""
        if not name:
            return None
        alternate_name = cls.query.filter_by(name=name).filter_by(end_date=None).one_or_none()
        return alternate_name

    @classmethod
    def find_by_id(cls, id: int = None):  # pylint: disable=W0622
        """Given a name, this will return an AlternateName."""
        if not id:
            return None
        alternate_name = cls.query.filter_by(id=id).one_or_none()
        return alternate_name

    @property
    def office_mailing_address(self):
        """Return the mailing address."""
        if (
            business_office := db.session.query(Office)  # SP/GP
            .filter(Office.alternate_name_id == self.id)
            .filter(Office.office_type == "businessOffice")
            .one_or_none()
        ):
            return business_office.addresses.filter(Address.address_type == "mailing")

        return (
            db.session.query(Address)
            .filter(Address.alternate_name_id == self.id)
            .filter(Address.address_type == Address.MAILING)
        )

    @property
    def office_delivery_address(self):
        """Return the delivery address."""
        if (
            business_office := db.session.query(Office)  # SP/GP
            .filter(Office.alternate_name_id == self.id)
            .filter(Office.office_type == "businessOffice")
            .one_or_none()
        ):
            return business_office.addresses.filter(Address.address_type == "delivery")

        return (
            db.session.query(Address)
            .filter(Address.alternate_name_id == self.id)
            .filter(Address.address_type == Address.DELIVERY)
        )

    @property
    def is_owned_by_legal_entity_person(self):
        """Return if owned by LE person."""
        return bool(self.legal_entity) and self.legal_entity.entity_type == BusinessCommon.EntityTypes.PERSON.value

    @property
    def is_owned_by_legal_entity_org(self):
        """Return if owned by LE org."""
        return bool(self.legal_entity) and self.legal_entity.entity_type not in BusinessCommon.NON_BUSINESS_ENTITY_TYPES

    @property
    def is_owned_by_colin_entity(self):
        """Return if owned by colin entity."""
        return bool(self.colin_entity)

    @property
    def owner_data_json(self):
        """Return if owner data."""
        json = {
            "deliveryAddress": None,
            "mailingAddress": None,
            "officer": {},
            "roles": [{"appointmentDate": datetime.date(self.start_date).isoformat(),
                       "cessationDate": None, "roleType": "Proprietor"}],
        }

        if self.delivery_address:
            member_address = self.delivery_address.json
            if "addressType" in member_address:
                del member_address["addressType"]
            json["deliveryAddress"] = member_address
        if self.mailing_address:
            member_mailing_address = self.mailing_address.json
            if "addressType" in member_mailing_address:
                del member_mailing_address["addressType"]
            json["mailingAddress"] = member_mailing_address
        else:
            if self.delivery_address:
                json["mailingAddress"] = json["deliveryAddress"]

        if self.is_owned_by_legal_entity_person:
            json["officer"] = {
                "id": self.legal_entity.id,
                "email": self.legal_entity.email,
                "firstName": self.legal_entity.first_name,
                "lastName": self.legal_entity.last_name,
                "middleInitial": self.legal_entity.middle_initial,
                "partyType": "person",
            }
        elif self.is_owned_by_legal_entity_org:
            json["officer"] = {
                "id": self.legal_entity.id,
                "email": self.legal_entity.email,
                "identifier": self.legal_entity.identifier,
                "organizationName": self.legal_name,
                "partyType": "organization",
            }
        elif self.is_owned_by_colin_entity:
            json["officer"] = {
                "id": self.colin_entity.id,
                "email": self.colin_entity.email,
                "identifier": self.colin_entity.identifier,
                "organizationName": self.legal_name,
                "partyType": "organization",
            }

        return json

    def save(self):
        """Save the object to the database immediately."""
        db.session.add(self)
        db.session.commit()

    def json(self, slim=False):
        """Return the Business as a json object.
        None fields are not included.
        """
        # TODO flesh out json fully once all additional columns added to this model
        slim_json = self._slim_json()
        if slim:
            return slim_json

        d = {
            **slim_json,
            "complianceWarnings": self.compliance_warnings,
            "warnings": self.warnings,
            "foundingDate": self.start_date.isoformat(),
            "lastModified": self.last_modified.isoformat(),
            "naicsKey": self.naics_key,
            "naicsCode": self.naics_code,
            "naicsDescription": self.naics_description,
            "allowedActions": self.allowable_actions,
        }
        self._extend_json(d)

        return d

    def _slim_json(self):
        """Return a smaller/faster version of the business json."""
        legal_name = self.legal_entity.legal_name if self.legal_entity else None
        d = {
            "adminFreeze": self.admin_freeze or False,
            "goodStanding": True,
            "identifier": self.identifier,
            "legalName": legal_name,
            "legalType": self.entity_type,
            "state": self.state.name if self.state else AlternateName.State.ACTIVE.name,
            "alternateNames": [
                {
                    "identifier": self.identifier,
                    "operatingName": self.name,
                    "entityType": self.entity_type,
                    "nameRegisteredDate": self.start_date.isoformat(),
                }
            ],
        }
        return d

    def _extend_json(self, d):
        """Include conditional fields to json."""
        from legal_api.models import Filing

        base_url = current_app.config.get("LEGAL_API_BASE_URL")

        if self.dissolution_date:
            d["dissolutionDate"] = LegislationDatetime.format_as_legislation_date(self.dissolution_date)

        if self.state_filing_id:
            d["stateFiling"] = f"{base_url}/{self.identifier}/filings/{self.state_filing_id}"

        if self.start_date:
            d["startDate"] = LegislationDatetime.format_as_legislation_date(self.start_date)

        d["hasCorrections"] = Filing.has_completed_filing(self, "correction")
        d["hasCourtOrders"] = Filing.has_completed_filing(self, "courtOrder")
