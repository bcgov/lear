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
"""This module holds all of the basic data about a LegalEntity.

The Business class and Schema are held in this module
"""
import re
from enum import Enum
from http import HTTPStatus
from typing import Final, Optional

import datedelta
from flask import current_app
from sql_versioning import Versioned
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError, ResourceClosedError
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref

from legal_api.exceptions import BusinessException
from legal_api.utils.base import BaseMeta
from legal_api.utils.datetime import datetime, timezone
from legal_api.utils.legislation_datetime import LegislationDatetime

from .address import Address  # noqa: F401,I003 pylint: disable=unused-import; needed by the SQLAlchemy relationship
from .alternate_name import AlternateName  # noqa: F401 pylint: disable=unused-import; needed by SQLAlchemy relationship
from .amalgamation import Amalgamation  # noqa: F401 pylint: disable=unused-import; needed by SQLAlchemy relationship
from .business_common import BusinessCommon
from .db import db  # noqa: I001
from .entity_role import EntityRole  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy relationship
from .filing import Filing  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy backref
from .office import Office  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy relationship
from .resolution import Resolution  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy backref
from .role_address import RoleAddress  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy relationship
from .share_class import ShareClass  # noqa: F401,I001,I003 pylint: disable=unused-import
from .user import User  # noqa: F401,I003 pylint: disable=unused-import; needed by the SQLAlchemy backref


class LegalEntity(
    Versioned, db.Model, BusinessCommon
):  # pylint: disable=too-many-instance-attributes, too-many-public-methods, too-many-lines
    """This class manages all of the base data about a LegalEntity.

    A business is base form of any entity that can interact directly
    with people and other businesses.
    Businesses can be sole-proprietors, corporations, societies, etc.
    """

    class AssociationTypes(Enum):
        """Render an Enum of the Business Association Types."""

        CP_COOPERATIVE = "CP"
        CP_HOUSING_COOPERATIVE = "HC"
        CP_COMMUNITY_SERVICE_COOPERATIVE = "CSC"

        SP_SOLE_PROPRIETORSHIP = "SP"
        SP_DOING_BUSINESS_AS = "DBA"

    BUSINESSES = {
        BusinessCommon.EntityTypes.BCOMP: {
            "numberedBusinessNameSuffix": "B.C. LTD.",
            "numberedDescription": "Numbered Benefit Company",
        },
        BusinessCommon.EntityTypes.COMP: {
            "numberedBusinessNameSuffix": "B.C. LTD.",
            "numberedDescription": "Numbered Limited Company",
        },
        BusinessCommon.EntityTypes.BC_ULC_COMPANY: {
            "numberedBusinessNameSuffix": "B.C. UNLIMITED LIABILITY COMPANY",
            "numberedDescription": "Numbered Unlimited Liability Company",
        },
        BusinessCommon.EntityTypes.BC_CCC: {
            "numberedBusinessNameSuffix": "B.C. COMMUNITY CONTRIBUTION COMPANY LTD.",
            "numberedDescription": "Numbered Community Contribution Company",
        },
    }

    __tablename__ = "legal_entities"
    # __mapper_args__ = {
    #     'include_properties': [
    #         'id',
    #         'additional_name',
    #         'admin_freeze',
    #         'association_type',
    #         'bn9',
    #         'continuation_out_date',
    #         'delivery_address_id'
    #         'dissolution_date',
    #         'email',
    #         'entity_type',
    #         'first_name',
    #         'fiscal_year_end_date',
    #         'foreign_identifier',
    #         'foreign_jurisdiction_region',
    #         'foreign_legal_name',
    #         'foreign_legal_type',
    #         'foreign_incorporation_date',
    #         'founding_date',
    #         'identifier',
    #         'jurisdiction',
    #         'last_agm_date',
    #         'last_ar_date',
    #         'last_ar_year',
    #         'last_ar_reminder_year',
    #         'last_coa_date',
    #         'last_cod_date',
    #         'last_ledger_id',
    #         'last_ledger_timestamp',
    #         'last_modified',
    #         'last_name',
    #         'last_remote_ledger_id',
    #         'legal_name',
    #         'mailing_address_id',
    #         'middle_initial',
    #         'naics_code',
    #         'naics_description',
    #         'naics_key',
    #         'restoration_expiry_date',
    #         'restriction_ind',
    #         'send_ar_ind',
    #         'start_date',
    #         'state',
    #         'state_filing_id',
    #         'submitter_userid',
    #         'tax_id',
    #         'tax_id',
    #         'title',
    #     ]
    # }

    id = db.Column(db.Integer, primary_key=True)
    last_modified = db.Column("last_modified", db.DateTime(timezone=True), default=datetime.utcnow)
    last_ledger_id = db.Column("last_ledger_id", db.Integer)
    last_remote_ledger_id = db.Column("last_remote_ledger_id", db.Integer, default=0)
    last_ledger_timestamp = db.Column("last_ledger_timestamp", db.DateTime(timezone=True), default=datetime.utcnow)
    last_ar_date = db.Column("last_ar_date", db.DateTime(timezone=True))
    last_agm_date = db.Column("last_agm_date", db.DateTime(timezone=True))
    last_coa_date = db.Column("last_coa_date", db.DateTime(timezone=True))
    last_cod_date = db.Column("last_cod_date", db.DateTime(timezone=True))
    _legal_name = db.Column("legal_name", db.String(1000), index=True)
    _entity_type = db.Column("entity_type", db.String(15), index=True)
    founding_date = db.Column("founding_date", db.DateTime(timezone=True), default=datetime.utcnow)
    start_date = db.Column("start_date", db.DateTime(timezone=True))
    restoration_expiry_date = db.Column("restoration_expiry_date", db.DateTime(timezone=True))
    dissolution_date = db.Column("dissolution_date", db.DateTime(timezone=True), default=None)
    continuation_out_date = db.Column("continuation_out_date", db.DateTime(timezone=True))
    _identifier = db.Column("identifier", db.String(10), index=True)
    tax_id = db.Column("tax_id", db.String(15), index=True)
    fiscal_year_end_date = db.Column("fiscal_year_end_date", db.DateTime(timezone=True), default=datetime.utcnow)
    restriction_ind = db.Column("restriction_ind", db.Boolean, unique=False, default=False)
    last_ar_year = db.Column("last_ar_year", db.Integer)
    last_ar_reminder_year = db.Column("last_ar_reminder_year", db.Integer)
    association_type = db.Column("association_type", db.String(50))
    state = db.Column("state", db.Enum(BusinessCommon.State), default=BusinessCommon.State.ACTIVE)
    admin_freeze = db.Column("admin_freeze", db.Boolean, unique=False, default=False)
    submitter_userid = db.Column("submitter_userid", db.Integer, db.ForeignKey("users.id"))
    submitter = db.relationship(
        "User",
        backref=backref("submitter", uselist=False),
        foreign_keys=[submitter_userid],
    )
    send_ar_ind = db.Column("send_ar_ind", db.Boolean, unique=False, default=True)
    bn9 = db.Column("bn9", db.String(9))
    first_name = db.Column("first_name", db.String(30), index=True)
    middle_initial = db.Column("middle_initial", db.String(30), index=True)
    last_name = db.Column("last_name", db.String(30))
    additional_name = db.Column("additional_name", db.String(100))
    title = db.Column("title", db.String(1000))
    email = db.Column("email", db.String(254))
    naics_key = db.Column(db.String(50))
    naics_code = db.Column(db.String(10))
    naics_description = db.Column(db.String(300))

    jurisdiction = db.Column("foreign_jurisdiction", db.String(10))
    foreign_jurisdiction_region = db.Column("foreign_jurisdiction_region", db.String(10))
    foreign_identifier = db.Column(db.String(15))
    foreign_legal_name = db.Column(db.String(1000))
    foreign_legal_type = db.Column(db.String(10))
    foreign_incorporation_date = db.Column(db.DateTime(timezone=True))

    # parent keys
    delivery_address_id = db.Column("delivery_address_id", db.Integer, db.ForeignKey("addresses.id"))
    mailing_address_id = db.Column("mailing_address_id", db.Integer, db.ForeignKey("addresses.id"))
    change_filing_id = db.Column("change_filing_id", db.Integer, db.ForeignKey("filings.id"), index=True)
    state_filing_id = db.Column("state_filing_id", db.Integer, db.ForeignKey("filings.id"))

    # relationships
    change_filing = db.relationship("Filing", foreign_keys=[change_filing_id])
    filings = db.relationship(
        "Filing",
        lazy="dynamic",
        foreign_keys="Filing.legal_entity_id",
        #   primaryjoin="(Filing.id==Address.user_id)",
    )
    offices = db.relationship("Office", lazy="dynamic", cascade="all, delete, delete-orphan")
    share_classes = db.relationship("ShareClass", lazy="dynamic", cascade="all, delete, delete-orphan")
    resolutions = db.relationship("Resolution", lazy="dynamic", foreign_keys="Resolution.legal_entity_id")
    documents = db.relationship("Document", lazy="dynamic")
    consent_continuation_outs = db.relationship("ConsentContinuationOut", lazy="dynamic")
    entity_roles = db.relationship(
        "EntityRole",
        foreign_keys="EntityRole.legal_entity_id",
        lazy="dynamic",
        overlaps="legal_entity",
    )
    alternate_names = db.relationship("AlternateName", back_populates="legal_entity", lazy="dynamic")
    role_addresses = db.relationship("RoleAddress", lazy="dynamic")
    entity_delivery_address = db.relationship(
        "Address",
        back_populates="legal_entity_delivery_address",
        foreign_keys=[delivery_address_id],
    )
    entity_mailing_address = db.relationship(
        "Address",
        back_populates="legal_entity_mailing_address",
        foreign_keys=[mailing_address_id],
    )
    resolution_signing_legal_entity = db.relationship(
        "Resolution",
        back_populates="signing_legal_entity",
        foreign_keys="Resolution.signing_legal_entity_id",
        lazy="dynamic",
    )
    amalgamating_businesses = db.relationship("AmalgamatingBusiness", lazy="dynamic")
    amalgamation = db.relationship("Amalgamation", lazy="dynamic")

    @hybrid_property
    def identifier(self):
        """Return the unique business identifier."""
        return self._identifier

    @identifier.setter
    def identifier(self, value: str):
        """Set the business identifier."""
        if LegalEntity.validate_identifier(self.entity_type, value):
            self._identifier = value
        else:
            raise BusinessException("invalid-identifier-format", 406)

    @property
    def next_anniversary(self):
        """Retrieve the next anniversary date for which an AR filing is due."""
        last_anniversary = self.founding_date
        if self.last_ar_date:
            last_anniversary = self.last_ar_date

        return last_anniversary + datedelta.datedelta(years=1)

    def get_ar_dates(self, next_ar_year):
        """Get ar min and max date for the specific year."""
        ar_min_date = datetime(next_ar_year, 1, 1).date()
        ar_max_date = datetime(next_ar_year, 12, 31).date()

        if self.entity_type == self.EntityTypes.COOP.value:
            # This could extend by moving it into a table with start and end date against each year when extension
            # is required. We need more discussion to understand different scenario's which can come across in future.
            if next_ar_year == 2020:
                # For year 2020, set the max date as October 31th next year (COVID extension).
                ar_max_date = datetime(next_ar_year + 1, 10, 31).date()
            else:
                # If this is a CO-OP, set the max date as April 30th next year.
                ar_max_date = datetime(next_ar_year + 1, 4, 30).date()
        elif self.entity_type in [
            self.EntityTypes.BCOMP.value,
            self.EntityTypes.COMP.value,
            self.EntityTypes.BC_ULC_COMPANY.value,
            self.EntityTypes.BC_CCC.value,
        ]:
            # For BCOMP min date is next anniversary date.
            ar_min_date = datetime(next_ar_year, self.founding_date.month, self.founding_date.day).date()
            ar_max_date = ar_min_date + datedelta.datedelta(days=60)

        if ar_max_date > datetime.utcnow().date():
            ar_max_date = datetime.utcnow().date()

        return ar_min_date, ar_max_date

    @property
    def office_mailing_address(self):
        """Return the mailing address."""
        registered_office = (
            db.session.query(Office)
            .filter(Office.legal_entity_id == self.id)
            .filter(Office.office_type == "registeredOffice")
            .one_or_none()
        )
        if registered_office:
            return registered_office.addresses.filter(Address.address_type == "mailing")
        elif (
            business_office := db.session.query(Office)  # SP/GP
            .filter(Office.legal_entity_id == self.id)
            .filter(Office.office_type == "businessOffice")
            .one_or_none()
        ):
            return business_office.addresses.filter(Address.address_type == "mailing")

        return (
            db.session.query(Address)
            .filter(Address.legal_entity_id == self.id)
            .filter(Address.address_type == Address.MAILING)
        )

    @property
    def aliases(self):
        """Return aliases(name translation) for a business if any."""
        return (
            db.session.query(AlternateName)
            .filter(AlternateName.legal_entity_id == self.id)
            .filter(AlternateName.name_type == AlternateName.NameType.TRANSLATION)
        )

    @property
    def office_delivery_address(self):
        """Return the delivery address."""
        registered_office = (
            db.session.query(Office)
            .filter(Office.legal_entity_id == self.id)
            .filter(Office.office_type == "registeredOffice")
            .one_or_none()
        )
        if registered_office:
            return registered_office.addresses.filter(Address.address_type == "delivery")
        elif (
            business_office := db.session.query(Office)  # SP/GP
            .filter(Office.legal_entity_id == self.id)
            .filter(Office.office_type == "businessOffice")
            .one_or_none()
        ):
            return business_office.addresses.filter(Address.address_type == "delivery")

        return (
            db.session.query(Address)
            .filter(Address.legal_entity_id == self.id)
            .filter(Address.address_type == Address.DELIVERY)
        )

    # @property
    def alternate_names_json(self):
        """Return alternate names (dba & translation) for a business if any."""
        # le_alias = aliased(LegalEntity)
        # alternate_names = (
        #     db.session.query(AlternateName.identifier,
        #                      AlternateName.name,
        #                      AlternateName.start_date,
        #                      le_alias.entity_type,
        #                      le_alias.founding_date)
        #     .join(le_alias, AlternateName.identifier == le_alias.identifier)
        # .filter(~le_alias.entity_type.in_(LegalEntity.NON_BUSINESS_ENTITY_TYPES))
        # .filter(AlternateName.legal_entity_id == self.id)
        #     .all()
        # )

        if alternate_names := self.alternate_names.all():
            names = []
            for alternate_name in alternate_names:
                if alternate_name.name_type == AlternateName.NameType.DBA:
                    # format dba
                    names.append(
                        {
                            "entityType": alternate_name.entity_type,
                            "identifier": alternate_name.identifier,
                            "name": alternate_name.name,
                            "nameRegisteredDate": alternate_name.start_date.isoformat(),
                            "nameStartDate": LegislationDatetime.format_as_legislation_date(
                                alternate_name.business_start_date
                            )
                            if alternate_name.business_start_date
                            else None,
                            "nameType": alternate_name.name_type.name,
                            "operatingName": alternate_name.name,  # will be removed in the future
                        }
                    )
                else:
                    # format name translation
                    names.append(
                        {
                            "name": alternate_name.name,
                            "nameStartDate": LegislationDatetime.format_as_legislation_date(alternate_name.start_date),
                            "nameType": alternate_name.name_type.name,
                        }
                    )

            return names

        return []

    def save(self):
        """Render a Business to the local cache."""
        db.session.add(self)
        db.session.commit()

    def delete(self):
        """Businesses cannot be deleted.

        TODO: Hook SQLAlchemy to block deletes
        """
        if self.dissolution_date:
            self.save()
        return self

    def json(self, slim=False):
        """Return the Business as a json object.

        None fields are not included.
        """
        slim_json = self._slim_json()
        if slim:
            return slim_json

        ar_min_date, ar_max_date = self.get_ar_dates(
            (self.last_ar_year if self.last_ar_year else self.founding_date.year) + 1
        )
        d = {
            **slim_json,
            "arMinDate": ar_min_date.isoformat(),
            "arMaxDate": ar_max_date.isoformat(),
            "foundingDate": self.founding_date.isoformat(),
            "hasRestrictions": self.restriction_ind,
            "complianceWarnings": self.compliance_warnings,
            "warnings": self.warnings,
            "lastAnnualGeneralMeetingDate": datetime.date(self.last_agm_date).isoformat() if self.last_agm_date else "",
            "lastAnnualReportDate": datetime.date(self.last_ar_date).isoformat() if self.last_ar_date else "",
            "lastLedgerTimestamp": self.last_ledger_timestamp.isoformat(),
            "lastAddressChangeDate": "",
            "lastDirectorChangeDate": "",
            "lastModified": self.last_modified.isoformat(),
            "naicsKey": self.naics_key,
            "naicsCode": self.naics_code,
            "naicsDescription": self.naics_description,
            "nextAnnualReport": LegislationDatetime.as_legislation_timezone_from_date(self.next_anniversary)
            .astimezone(timezone.utc)
            .isoformat(),
            "associationType": self.association_type,
            "allowedActions": self.allowable_actions,
        }
        self._extend_json(d)

        return d

    def _slim_json(self):
        """Return a smaller/faster version of the business json."""
        d = {
            "adminFreeze": self.admin_freeze or False,
            "goodStanding": self.good_standing,
            "identifier": self.identifier,
            "legalName": self._legal_name,
            "legalType": self.entity_type,
            "state": self.state.name,
        }

        if self.tax_id:
            d["taxId"] = self.tax_id

        if self.alternate_names:
            d["alternateNames"] = self.alternate_names_json()

        return d

    def _extend_json(self, d):
        """Include conditional fields to json."""
        base_url = current_app.config.get("LEGAL_API_BASE_URL")

        if self.last_coa_date:
            d["lastAddressChangeDate"] = LegislationDatetime.format_as_legislation_date(self.last_coa_date)
        if self.last_cod_date:
            d["lastDirectorChangeDate"] = LegislationDatetime.format_as_legislation_date(self.last_cod_date)

        if self.dissolution_date:
            d["dissolutionDate"] = LegislationDatetime.format_as_legislation_date(self.dissolution_date)

        if self.fiscal_year_end_date:
            d["fiscalYearEndDate"] = datetime.date(self.fiscal_year_end_date).isoformat()
        if self.state_filing_id:
            # TODO: revert once amalgamation tables and migration scripts have been run
            # if self.state == LegalEntity.State.HISTORICAL and (
            #     amalgamating_business := self.amalgamating_businesses.one_or_none()
            # ):
            #     amalgamation = Amalgamation.find_by_id(amalgamating_business.amalgamation_id)
            #     d["amalgamatedInto"] = amalgamation.json()
            # else:
            #     d["stateFiling"] = f"{base_url}/{self.identifier}/filings/{self.state_filing_id}"
            d["stateFiling"] = f"{base_url}/{self.identifier}/filings/{self.state_filing_id}"

        if self.start_date:
            d["startDate"] = LegislationDatetime.format_as_legislation_date(self.start_date)

        if self.restoration_expiry_date:
            d["restorationExpiryDate"] = LegislationDatetime.format_as_legislation_date(self.restoration_expiry_date)
        if self.continuation_out_date:
            d["continuationOutDate"] = LegislationDatetime.format_as_legislation_date(self.continuation_out_date)

        if self.jurisdiction:
            d["jurisdiction"] = self.jurisdiction
            d["jurisdictionRegion"] = self.foreign_jurisdiction_region
            d["foreignIdentifier"] = self.foreign_identifier
            d["foreignLegalName"] = self.foreign_legal_name
            d["foreignLegalType"] = self.foreign_legal_type
            d["foreignIncorporationDate"] = (
                LegislationDatetime.format_as_legislation_date(self.foreign_incorporation_date)
                if self.foreign_incorporation_date
                else None
            )

        d["hasCorrections"] = Filing.has_completed_filing(self, "correction")
        d["hasCourtOrders"] = Filing.has_completed_filing(self, "courtOrder")

    @property
    def party_json(self) -> dict:
        """Return the party member as a json object."""
        if self.entity_type == LegalEntity.EntityTypes.PERSON.value:
            member = {
                "officer": {
                    "id": self.id,
                    "partyType": self.entity_type,
                    "firstName": self.first_name,
                    "lastName": self.last_name,
                }
            }
            if self.title:
                member["title"] = self.title
            if self.middle_initial:
                member["officer"]["middleInitial"] = self.middle_initial
        else:
            member = {
                "officer": {
                    "id": self.id,
                    "partyType": self.entity_type,
                    "organizationName": self._legal_name,
                    "identifier": self.identifier,
                }
            }
        member["officer"]["email"] = self.email
        if self.entity_delivery_address:
            member_address = self.entity_delivery_address.json
            if "addressType" in member_address:
                del member_address["addressType"]
            member["deliveryAddress"] = member_address
        if self.entity_mailing_address:
            member_mailing_address = self.entity_mailing_address.json
            if "addressType" in member_mailing_address:
                del member_mailing_address["addressType"]
            member["mailingAddress"] = member_mailing_address
        else:
            if self.entity_delivery_address:
                member["mailingAddress"] = member["deliveryAddress"]

        return member

    @property
    def name(self) -> str:
        """Return the full name of the party for comparison."""
        if self.entity_type == LegalEntity.EntityTypes.PERSON.value:
            if self.middle_initial:
                return " ".join((self.first_name, self.middle_initial, self.last_name)).strip().upper()
            return " ".join((self.first_name, self.last_name)).strip().upper()
        return self._legal_name

    @classmethod
    def find_by_legal_name(cls, legal_name: str = None):
        """Given a legal_name, this will return an Active LegalEntity."""
        legal_entity = None
        if legal_name:
            try:
                legal_entity = (
                    cls.query.filter_by(_legal_name=legal_name).filter_by(dissolution_date=None).one_or_none()
                )
            except (OperationalError, ResourceClosedError):
                # TODO: This usually means a misconfigured database.
                # This is not a business error if the cache is unavailable.
                return None
        return legal_entity

    @classmethod
    def find_by_operating_name(cls, operating_name: str = None):
        """Given a operating_name, this will return an Active LegalEntity."""
        if not operating_name:
            return None
        if alternate_name := AlternateName.find_by_name(operating_name):
            return cls.find_by_id(alternate_name.legal_entity_id)
        return None

    @classmethod
    def find_by_identifier(cls, identifier: str = None):
        """Return a Business by the id assigned by the Registrar."""
        if not identifier or not cls.validate_identifier(entity_type=None, identifier=identifier):
            return None

        non_business_types = [
            LegalEntity.EntityTypes.PERSON.value,
            LegalEntity.EntityTypes.ORGANIZATION.value,
        ]
        legal_entity = (
            cls.query.filter(~LegalEntity._entity_type.in_(non_business_types))
            .filter_by(identifier=identifier)
            .one_or_none()
        )

        return legal_entity

    @classmethod
    def find_by_internal_id(cls, internal_id: int = None):
        """Return a Business by the internal id."""
        legal_entity = None
        if internal_id:
            legal_entity = cls.query.filter_by(id=internal_id).one_or_none()
        return legal_entity

    @classmethod
    def find_by_tax_id(cls, tax_id: str):
        """Return a Business by the tax_id."""
        legal_entity = None
        if tax_id:
            legal_entity = cls.query.filter_by(tax_id=tax_id).one_or_none()
        return legal_entity

    @classmethod
    def get_all_by_no_tax_id(cls):
        """Return all businesses with no tax_id."""
        no_tax_id_types = [
            LegalEntity.EntityTypes.COOP.value,
            LegalEntity.EntityTypes.SOLE_PROP.value,
            LegalEntity.EntityTypes.PARTNERSHIP.value,
            LegalEntity.EntityTypes.PERSON.value,
            LegalEntity.EntityTypes.ORGANIZATION.value,
        ]
        legal_entities = cls.query.filter(~LegalEntity._entity_type.in_(no_tax_id_types)).filter_by(tax_id=None).all()
        return legal_entities
    
    @classmethod
    def is_pending_amalgamating_business(cls, business_identifier):
        """Check if a business has a pending amalgamation with the provided business identifier."""
        where_clause = {'identifier': business_identifier}

        # Query the database to find amalgamation filings
        # pylint: disable=protected-access
        # pylint: disable=unsubscriptable-object
        filing = db.session.query(Filing). \
            filter(Filing._status == Filing.Status.PAID.value,
                   Filing._filing_type == 'amalgamationApplication',
                   Filing.filing_json['filing']['amalgamationApplication']
                   ['amalgamatingBusinesses'].contains([where_clause])
                   ).one_or_none()
        return filing

    @classmethod
    def get_next_value_from_sequence(cls, business_type: str) -> Optional[int]:
        """Return the next value from the sequence."""
        sequence_mapping = {
            "CP": "legal_entity_identifier_coop",
            "FM": "legal_entity_identifier_sp_gp",
            "P": "legal_entity_identifier_person",
        }
        if sequence_name := sequence_mapping.get(business_type, None):
            return db.session.execute(text(f"SELECT nextval('{sequence_name}')")).scalar()
        return None

    @staticmethod
    def validate_identifier(entity_type: BusinessCommon.EntityTypes, identifier: str) -> bool:
        """Validate the identifier meets the Registry naming standards.

        All legal entities with BC Reg are PREFIX + 7 digits

        CP = BC COOPS prefix;
        XCP = Expro COOP prefix

        Examples:
            ie: CP1234567 or XCP1234567

        """
        if (
            entity_type
            and entity_type == LegalEntity.EntityTypes.PERSON.value
            and (identifier and identifier.startswith("P") or not identifier)
        ):
            return True

        if identifier[:2] == "NR":
            return True

        if len(identifier) < 9:
            return False

        try:
            d = int(identifier[-7:])
            if d == 0:
                return False
        except ValueError:
            return False
        # TODO This is not correct for entity types that are not Coops
        if identifier[:-7] not in ("BC", "CP", "FM", "P", "XCP"):
            return False

        return True

    @property
    def valid_party_type_data(self) -> bool:
        """Validate the model based on the party type (person/organization)."""
        if self.entity_type != LegalEntity.EntityTypes.PERSON.value:
            if self.first_name or self.middle_initial or self.last_name:
                return False

        if self.entity_type == LegalEntity.EntityTypes.PERSON.value:
            if not (self.first_name or self.middle_initial or self.last_name) or self._legal_name:
                return False
        return True

    @classmethod
    def find_by_id(cls, legal_entity_id: int):
        """Return a legal entity by the internal id."""
        legal_entity = None
        if legal_entity_id:
            legal_entity = cls.query.filter_by(id=legal_entity_id).one_or_none()
        return legal_entity


@event.listens_for(LegalEntity, "before_insert")
@event.listens_for(LegalEntity, "before_update")
def receive_before_change(mapper, connection, target):  # pylint: disable=unused-argument; SQLAlchemy callback signature
    """Run checks/updates before adding/changing the party model data."""
    party = target

    # skip this party updater if the flag is set
    # Scenario: data loading party data that is missing required party information
    if hasattr(party, "skip_party_listener") and party.skip_party_listener:
        return

    if not party.valid_party_type_data:
        raise BusinessException(
            error=f"Attempt to change/add {party.entity_type} had invalid data.",
            status_code=HTTPStatus.BAD_REQUEST,
        )


ASSOCIATION_TYPE_DESC: Final = {
    LegalEntity.AssociationTypes.CP_COOPERATIVE.value: "Ordinary Cooperative",
    LegalEntity.AssociationTypes.CP_HOUSING_COOPERATIVE.value: "Housing Cooperative",
    LegalEntity.AssociationTypes.CP_COMMUNITY_SERVICE_COOPERATIVE.value: "Community Service Cooperative",
    LegalEntity.AssociationTypes.SP_SOLE_PROPRIETORSHIP.value: "Sole Proprietorship",
    LegalEntity.AssociationTypes.SP_DOING_BUSINESS_AS.value: "Sole Proprietorship (DBA)",
}


class LegalEntityType(str, Enum, metaclass=BaseMeta):
    """The business type."""

    COOPERATIVE = "CP"
    INDIVIDUAL = "FP"
    PARTNERSHIP_AND_SOLE_PROP = "FM"
    PERSON = "P"
    TRUST = "TRUST"
    OTHER = "OT"
    DEFAULT = "OT"

    @classmethod
    def get_enum_by_value(cls, value: str) -> Optional[str]:
        """Return the enum by value."""
        for enum_value in cls:
            if enum_value.value == value:
                return enum_value
        return None


MAX_IDENTIFIER_NUM_LENGTH: Final[int] = 7


class LegalEntityIdentifier:
    """The business identifier."""

    @staticmethod
    def validate_format(value: str) -> bool:
        """Validate the business identifier."""
        legal_type = value[: re.search(r"\d", value).start()]

        if legal_type not in LegalEntityType or (not value[value.find(legal_type) + len(legal_type) :].isdigit()):
            return False

        return True

    @staticmethod
    def next_identifier(legal_entity_type: LegalEntityType) -> Optional[str]:
        """Get the next identifier."""
        if not (
            legal_entity_type in LegalEntityType
            and (sequence_val := LegalEntity.get_next_value_from_sequence(legal_entity_type))
        ):
            return None

        return f"{legal_entity_type.value}{str(sequence_val).zfill(MAX_IDENTIFIER_NUM_LENGTH)}"
