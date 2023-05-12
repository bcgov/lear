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
from enum import Enum, auto
from http import HTTPStatus
from typing import Final, Optional

import datedelta
from flask import current_app
from sqlalchemy import event
from sqlalchemy.exc import OperationalError, ResourceClosedError
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref

from legal_api.exceptions import BusinessException
from legal_api.utils.base import BaseEnum
from legal_api.utils.datetime import datetime, timezone
from legal_api.utils.legislation_datetime import LegislationDatetime

from .db import db  # noqa: I001
from .share_class import ShareClass  # noqa: F401,I001,I003 pylint: disable=unused-import


from .alternate_name import AlternateName  # noqa: F401 pylint: disable=unused-import; needed by SQLAlchemy relationship


from .address import Address  # noqa: F401,I003 pylint: disable=unused-import; needed by the SQLAlchemy relationship
from .alias import Alias  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy relationship
from .entity_role import EntityRole  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy relationship
from .filing import Filing  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy backref
from .office import Office  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy relationship
from .resolution import Resolution  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy backref
from .role_address import RoleAddress  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy relationship
from .user import User  # noqa: F401,I003 pylint: disable=unused-import; needed by the SQLAlchemy backref


class LegalEntity(db.Model):  # pylint: disable=too-many-instance-attributes,disable=too-many-public-methods
    """This class manages all of the base data about a LegalEntity.

    A business is base form of any entity that can interact directly
    with people and other businesses.
    Businesses can be sole-proprietors, corporations, societies, etc.
    """

    class State(BaseEnum):
        """Enum for the Business state."""

        ACTIVE = auto()
        HISTORICAL = auto()
        LIQUIDATION = auto()

    # NB: commented out items that exist in namex but are not yet supported by Lear
    class EntityTypes(str, Enum):
        """Render an Enum of the Business Legal Types."""

        COOP = 'CP'  # aka COOPERATIVE in namex
        BCOMP = 'BEN'  # aka BENEFIT_COMPANY in namex
        COMP = 'BC'  # aka CORPORATION in namex
        CONTINUE_IN = 'C'
        CO_1860 = 'QA'
        CO_1862 = 'QB'
        CO_1878 = 'QC'
        CO_1890 = 'QD'
        CO_1897 = 'QE'
        BC_ULC_COMPANY = 'ULC'
        ULC_CONTINUE_IN = 'CUL'
        ULC_CO_1860 = 'UQA'
        ULC_CO_1862 = 'UQB'
        ULC_CO_1878 = 'UQC'
        ULC_CO_1890 = 'UQD'
        ULC_CO_1897 = 'UQE'
        BC_CCC = 'CC'
        EXTRA_PRO_A = 'A'
        EXTRA_PRO_B = 'B'
        CEMETARY = 'CEM'
        EXTRA_PRO_REG = 'EPR'
        FOREIGN = 'FOR'
        LICENSED = 'LIC'
        LIBRARY = 'LIB'
        LIMITED_CO = 'LLC'
        PRIVATE_ACT = 'PA'
        PARISHES = 'PAR'
        PENS_FUND_SOC = 'PFS'
        REGISTRATION = 'REG'
        RAILWAYS = 'RLY'
        SOCIETY_BRANCH = 'SB'
        TRUST = 'T'
        TRAMWAYS = 'TMY'
        XPRO_COOP = 'XCP'
        CCC_CONTINUE_IN = 'CCC'
        SOCIETY = 'S'
        XPRO_SOCIETY = 'XS'
        SOLE_PROP = 'SP'
        PARTNERSHIP = 'GP'
        LIM_PARTNERSHIP = 'LP'
        XPRO_LIM_PARTNR = 'XP'
        LL_PARTNERSHIP = 'LL'
        XPRO_LL_PARTNR = 'XL'
        MISC_FIRM = 'MF'
        FINANCIAL = 'FI'
        CONT_IN_SOCIETY = 'CS'
        PERSON = 'person'
        ORGANIZATION = 'organization'
        # *** The following are not yet supported by legal-api: ***
        # DOING_BUSINESS_AS = 'DBA'
        # XPRO_CORPORATION = 'XCR'
        # XPRO_UNLIMITED_LIABILITY_COMPANY = 'XUL'

    LIMITED_COMPANIES: Final = [EntityTypes.COMP,
                                EntityTypes.CONTINUE_IN,
                                EntityTypes.CO_1860,
                                EntityTypes.CO_1862,
                                EntityTypes.CO_1878,
                                EntityTypes.CO_1890,
                                EntityTypes.CO_1897]

    UNLIMITED_COMPANIES: Final = [EntityTypes.BC_ULC_COMPANY,
                                  EntityTypes.ULC_CONTINUE_IN,
                                  EntityTypes.ULC_CO_1860,
                                  EntityTypes.ULC_CO_1862,
                                  EntityTypes.ULC_CO_1878,
                                  EntityTypes.ULC_CO_1890,
                                  EntityTypes.ULC_CO_1897]

    class AssociationTypes(Enum):
        """Render an Enum of the Business Association Types."""

        CP_COOPERATIVE = 'CP'
        CP_HOUSING_COOPERATIVE = 'HC'
        CP_COMMUNITY_SERVICE_COOPERATIVE = 'CSC'

        SP_SOLE_PROPRIETORSHIP = 'SP'
        SP_DOING_BUSINESS_AS = 'DBA'

    BUSINESSES = {
        EntityTypes.BCOMP: {
            'numberedLegalNameSuffix': 'B.C. LTD.',
            'numberedDescription': 'Numbered Benefit Company'
        },
        EntityTypes.COMP: {
            'numberedLegalNameSuffix': 'B.C. LTD.',
            'numberedDescription': 'Numbered Limited Company'
        },
        EntityTypes.BC_ULC_COMPANY: {
            'numberedLegalNameSuffix': 'B.C. UNLIMITED LIABILITY COMPANY',
            'numberedDescription': 'Numbered Unlimited Liability Company'
        },
        EntityTypes.BC_CCC: {
            'numberedLegalNameSuffix': 'B.C. COMMUNITY CONTRIBUTION COMPANY LTD.',
            'numberedDescription': 'Numbered Community Contribution Company'
        }
    }

    __versioned__ = {}
    __tablename__ = 'legal_entities'
    __mapper_args__ = {
        'include_properties': [
            'id',
            'admin_freeze',
            'association_type',
            'dissolution_date',
            'fiscal_year_end_date',
            'founding_date',
            'identifier',
            'last_agm_date',
            'last_ar_date',
            'last_ar_year',
            'last_ar_reminder_year',
            'last_coa_date',
            'last_cod_date',
            'last_ledger_id',
            'last_ledger_timestamp',
            'last_modified',
            'last_remote_ledger_id',
            'legal_name',
            'entity_type',
            'restriction_ind',
            'state',
            'state_filing_id',
            'submitter_userid',
            'tax_id',
            'naics_key',
            'naics_code',
            'naics_description',
            'start_date',
            'jurisdiction',
            'foreign_identifier',
            'foreign_legal_name',
            'foreign_legal_type',
            'foreign_incorporation_date',
            'send_ar_ind',
            'restoration_expiry_date',
            'cco_expiry_date',
            'tax_id',
            'bn9',
            'first_name',
            'middle_initial',
            'last_name',
            'additional_name',
            'title',
            'email',
            'mailing_address_id',
            'delivery_address_id'
        ]
    }

    id = db.Column(db.Integer, primary_key=True)
    last_modified = db.Column('last_modified', db.DateTime(timezone=True), default=datetime.utcnow)
    last_ledger_id = db.Column('last_ledger_id', db.Integer)
    last_remote_ledger_id = db.Column('last_remote_ledger_id', db.Integer, default=0)
    last_ledger_timestamp = db.Column('last_ledger_timestamp', db.DateTime(timezone=True), default=datetime.utcnow)
    last_ar_date = db.Column('last_ar_date', db.DateTime(timezone=True))
    last_agm_date = db.Column('last_agm_date', db.DateTime(timezone=True))
    last_coa_date = db.Column('last_coa_date', db.DateTime(timezone=True))
    last_cod_date = db.Column('last_cod_date', db.DateTime(timezone=True))
    legal_name = db.Column('legal_name', db.String(1000), index=True)
    entity_type = db.Column('entity_type', db.String(15), index=True)
    founding_date = db.Column('founding_date', db.DateTime(timezone=True), default=datetime.utcnow)
    start_date = db.Column('start_date', db.DateTime(timezone=True))
    restoration_expiry_date = db.Column('restoration_expiry_date', db.DateTime(timezone=True))
    dissolution_date = db.Column('dissolution_date', db.DateTime(timezone=True), default=None)
    cco_expiry_date = db.Column('cco_expiry_date', db.DateTime(timezone=True))  # consent continuation out expiry_date
    _identifier = db.Column('identifier', db.String(10), index=True)
    tax_id = db.Column('tax_id', db.String(15), index=True)
    fiscal_year_end_date = db.Column('fiscal_year_end_date', db.DateTime(timezone=True), default=datetime.utcnow)
    restriction_ind = db.Column('restriction_ind', db.Boolean, unique=False, default=False)
    last_ar_year = db.Column('last_ar_year', db.Integer)
    last_ar_reminder_year = db.Column('last_ar_reminder_year', db.Integer)
    association_type = db.Column('association_type', db.String(50))
    state = db.Column('state', db.Enum(State), default=State.ACTIVE.value)
    state_filing_id = db.Column('state_filing_id', db.Integer)
    admin_freeze = db.Column('admin_freeze', db.Boolean, unique=False, default=False)
    submitter_userid = db.Column('submitter_userid', db.Integer, db.ForeignKey('users.id'))
    submitter = db.relationship('User', backref=backref('submitter', uselist=False), foreign_keys=[submitter_userid])
    send_ar_ind = db.Column('send_ar_ind', db.Boolean, unique=False, default=True)
    bn9 = db.Column('bn9', db.String(9))
    first_name = db.Column('first_name', db.String(30), index=True)
    middle_initial = db.Column('middle_initial', db.String(30), index=True)
    last_name = db.Column('last_name', db.String(30))
    additional_name = db.Column('additional_name', db.String(100))
    title = db.Column('title', db.String(1000))
    email = db.Column('email', db.String(254))

    # parent keys
    delivery_address_id = db.Column('delivery_address_id', db.Integer, db.ForeignKey('addresses.id'))
    mailing_address_id = db.Column('mailing_address_id', db.Integer, db.ForeignKey('addresses.id'))
    naics_key = db.Column(db.String(50))
    naics_code = db.Column(db.String(10))
    naics_description = db.Column(db.String(150))

    jurisdiction = db.Column('foreign_jurisdiction', db.String(10))
    foreign_identifier = db.Column(db.String(15))
    foreign_legal_name = db.Column(db.String(1000))
    foreign_legal_type = db.Column(db.String(10))
    foreign_incorporation_date = db.Column(db.DateTime(timezone=True))

    # relationships
    filings = db.relationship('Filing', lazy='dynamic')
    offices = db.relationship('Office', lazy='dynamic', cascade='all, delete, delete-orphan')
    share_classes = db.relationship('ShareClass', lazy='dynamic', cascade='all, delete, delete-orphan')
    aliases = db.relationship('Alias', lazy='dynamic')
    resolutions = db.relationship('Resolution', lazy='dynamic', foreign_keys='Resolution.legal_entity_id')
    documents = db.relationship('Document', lazy='dynamic')
    entity_roles = db.relationship('EntityRole', foreign_keys='EntityRole.legal_entity_id', lazy='dynamic',
                                   overlaps='legal_entity')
    alternate_names = db.relationship('AlternateName', lazy='dynamic')
    role_addresses = db.relationship('RoleAddress', lazy='dynamic')
    entity_delivery_address = db.relationship('Address', back_populates='legal_entity_delivery_address',
                                              foreign_keys=[delivery_address_id])
    entity_mailing_address = db.relationship('Address', back_populates='legal_entity_mailing_address',
                                             foreign_keys=[mailing_address_id])
    resolution_signing_legal_entity = db.relationship('Resolution',
                                                      back_populates='signing_legal_entity',
                                                      foreign_keys='Resolution.signing_legal_entity_id',
                                                      lazy='dynamic')

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
            raise BusinessException('invalid-identifier-format', 406)

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
        elif self.entity_type in [self.EntityTypes.BCOMP.value,
                                  self.EntityTypes.COMP.value,
                                  self.EntityTypes.BC_ULC_COMPANY.value,
                                  self.EntityTypes.BC_CCC.value]:
            # For BCOMP min date is next anniversary date.
            ar_min_date = datetime(next_ar_year, self.founding_date.month, self.founding_date.day).date()
            ar_max_date = ar_min_date + datedelta.datedelta(days=60)

        if ar_max_date > datetime.utcnow().date():
            ar_max_date = datetime.utcnow().date()

        return ar_min_date, ar_max_date

    @property
    def office_mailing_address(self):
        """Return the mailing address."""
        registered_office = db.session.query(Office).filter(Office.legal_entity_id == self.id).\
            filter(Office.office_type == 'registeredOffice').one_or_none()
        if registered_office:
            return registered_office.addresses.filter(Address.address_type == 'mailing')
        elif (business_office := db.session.query(Office)  # SP/GP
              .filter(Office.legal_entity_id == self.id)
              .filter(Office.office_type == 'businessOffice').one_or_none()):
            return business_office.addresses.filter(Address.address_type == 'mailing')

        return db.session.query(Address).filter(Address.legal_entity_id == self.id). \
            filter(Address.address_type == Address.MAILING)

    @property
    def office_delivery_address(self):
        """Return the delivery address."""
        registered_office = db.session.query(Office).filter(Office.legal_entity_id == self.id).\
            filter(Office.office_type == 'registeredOffice').one_or_none()
        if registered_office:
            return registered_office.addresses.filter(Address.address_type == 'delivery')
        elif (business_office := db.session.query(Office)  # SP/GP
              .filter(Office.legal_entity_id == self.id)
              .filter(Office.office_type == 'businessOffice').one_or_none()):
            return business_office.addresses.filter(Address.address_type == 'delivery')

        return db.session.query(Address).filter(Address.legal_entity_id == self.id).\
            filter(Address.address_type == Address.DELIVERY)

    @property
    def is_firm(self):
        """Return if is firm, otherwise false."""
        return self.entity_type in (self.EntityTypes.SOLE_PROP, self.EntityTypes.PARTNERSHIP)

    @property
    def good_standing(self):
        """Return true if in good standing, otherwise false."""
        # A firm is always in good standing
        if self.is_firm:
            return True
        # Date of last AR or founding date if they haven't yet filed one
        last_ar_date = self.last_ar_date or self.founding_date
        is_active = self.state.name == LegalEntity.State.ACTIVE.name
        # Good standing is if last AR was filed within the past 1 year, 2 months and 1 day and is in an active state
        return last_ar_date + datedelta.datedelta(years=1, months=2, days=1) > datetime.utcnow() if is_active else True

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
            'arMinDate': ar_min_date.isoformat(),
            'arMaxDate': ar_max_date.isoformat(),
            'foundingDate': self.founding_date.isoformat(),
            'hasRestrictions': self.restriction_ind,
            'complianceWarnings': self.compliance_warnings,
            'warnings': self.warnings,
            'lastAnnualGeneralMeetingDate': datetime.date(self.last_agm_date).isoformat() if self.last_agm_date else '',
            'lastAnnualReportDate': datetime.date(self.last_ar_date).isoformat() if self.last_ar_date else '',
            'lastLedgerTimestamp': self.last_ledger_timestamp.isoformat(),
            'lastAddressChangeDate': '',
            'lastDirectorChangeDate': '',
            'lastModified': self.last_modified.isoformat(),
            'naicsKey': self.naics_key,
            'naicsCode': self.naics_code,
            'naicsDescription': self.naics_description,
            'nextAnnualReport': LegislationDatetime.as_legislation_timezone_from_date(
                self.next_anniversary
            ).astimezone(timezone.utc).isoformat(),
            'associationType': self.association_type,
            'allowedActions': self.allowable_actions
        }
        self._extend_json(d)

        return d

    def _slim_json(self):
        """Return a smaller/faster version of the business json."""
        d = {
            'adminFreeze': self.admin_freeze or False,
            'goodStanding': self.good_standing,
            'identifier': self.identifier,
            'legalName': self.legal_name,
            'legalType': self.entity_type,
            'state': self.state.name if self.state else LegalEntity.State.ACTIVE.name
        }

        if self.tax_id:
            d['taxId'] = self.tax_id

        return d

    def _extend_json(self, d):
        """Include conditional fields to json."""
        base_url = current_app.config.get('LEGAL_API_BASE_URL')

        if self.last_coa_date:
            d['lastAddressChangeDate'] = datetime.date(
                LegislationDatetime.as_legislation_timezone(self.last_coa_date)
            ).isoformat()
        if self.last_cod_date:
            d['lastDirectorChangeDate'] = datetime.date(
                LegislationDatetime.as_legislation_timezone(self.last_cod_date)
            ).isoformat()

        if self.dissolution_date:
            d['dissolutionDate'] = datetime.date(self.dissolution_date).isoformat()
        if self.fiscal_year_end_date:
            d['fiscalYearEndDate'] = datetime.date(self.fiscal_year_end_date).isoformat()
        if self.state_filing_id:
            d['stateFiling'] = f'{base_url}/{self.identifier}/filings/{self.state_filing_id}'

        if self.start_date:
            d['startDate'] = datetime.date(
                LegislationDatetime.as_legislation_timezone(self.start_date)
            ).isoformat()

        if self.restoration_expiry_date:
            d['restorationExpiryDate'] = self.restoration_expiry_date.isoformat()
        if self.cco_expiry_date:
            d['ccoExpiryDate'] = self.cco_expiry_date.isoformat()

        if self.jurisdiction:
            d['jurisdiction'] = self.jurisdiction
            d['foreignIdentifier'] = self.foreign_identifier
            d['foreignLegalName'] = self.foreign_legal_name
            d['foreignLegalType'] = self.foreign_legal_type
            d['foreignIncorporationDate'] = datetime.date(
                LegislationDatetime.as_legislation_timezone(self.foreign_incorporation_date)
            ).isoformat()

        filings = self.filings.all()

        d['hasCorrections'] = any(x for x in filings if x.filing_type == 'correction' and
                                  x.status == 'COMPLETED')

        d['hasCourtOrders'] = any(x for x in filings if x.filing_type == 'courtOrder' and
                                  x.status == 'COMPLETED')

    @property
    def party_json(self) -> dict:
        """Return the party member as a json object."""
        if self.entity_type == LegalEntity.EntityTypes.PERSON.value:
            member = {
                'officer': {
                    'id': self.id,
                    'partyType': self.entity_type,
                    'firstName': self.first_name,
                    'lastName': self.last_name
                }
            }
            if self.title:
                member['title'] = self.title
            if self.middle_initial:
                member['officer']['middleInitial'] = self.middle_initial
        else:
            member = {
                'officer': {
                    'id': self.id,
                    'partyType': self.entity_type,
                    'organizationName': self.legal_name,
                    'identifier': self.identifier
                }
            }
        member['officer']['email'] = self.email
        if self.entity_delivery_address:
            member_address = self.entity_delivery_address.json
            if 'addressType' in member_address:
                del member_address['addressType']
            member['deliveryAddress'] = member_address
        if self.entity_mailing_address:
            member_mailing_address = self.entity_mailing_address.json
            if 'addressType' in member_mailing_address:
                del member_mailing_address['addressType']
            member['mailingAddress'] = member_mailing_address
        else:
            if self.entity_delivery_address:
                member['mailingAddress'] = member['deliveryAddress']

        return member

    @property
    def compliance_warnings(self):
        """Return compliance warnings."""
        if not hasattr(self, '_compliance_warnings'):
            return []

        return self._compliance_warnings

    @compliance_warnings.setter
    def compliance_warnings(self, value):
        """Set compliance warnings."""
        self._compliance_warnings = value

    @property
    def warnings(self):
        """Return warnings."""
        if not hasattr(self, '_warnings'):
            return []

        return self._warnings

    @warnings.setter
    def warnings(self, value):
        """Set warnings."""
        self._warnings = value

    @property
    def allowable_actions(self):
        """Return warnings."""
        if not hasattr(self, '_allowable_actions'):
            return {}

        return self._allowable_actions

    @property
    def name(self) -> str:
        """Return the full name of the party for comparison."""
        if self.entity_type == LegalEntity.EntityTypes.PERSON.value:
            if self.middle_initial:
                return ' '.join((self.first_name, self.middle_initial, self.last_name)).strip().upper()
            return ' '.join((self.first_name, self.last_name)).strip().upper()
        return self.legal_name

    @allowable_actions.setter
    def allowable_actions(self, value):
        """Set warnings."""
        self._allowable_actions = value

    @classmethod
    def find_by_legal_name(cls, legal_name: str = None):
        """Given a legal_name, this will return an Active LegalEntity."""
        legal_entity = None
        if legal_name:
            try:
                legal_entity = cls.query.filter_by(legal_name=legal_name).\
                    filter_by(dissolution_date=None).one_or_none()
            except (OperationalError, ResourceClosedError):
                # TODO: This usually means a misconfigured database.
                # This is not a business error if the cache is unavailable.
                return None
        return legal_entity

    @classmethod
    def find_by_identifier(cls, identifier: str = None):
        """Return a Business by the id assigned by the Registrar."""
        legal_entity = None
        if identifier:
            legal_entity = cls.query.filter_by(identifier=identifier).one_or_none()
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
        ]
        legal_entities = cls.query.filter(~LegalEntity.entity_type.in_(no_tax_id_types)).filter_by(tax_id=None).all()
        return legal_entities

    @classmethod
    def get_filing_by_id(cls, legal_entity_identifier: int, filing_id: str):
        """Return the filings for a specific business and filing_id."""
        filing = db.session.query(LegalEntity, Filing). \
            filter(LegalEntity.id == Filing.legal_entity_id). \
            filter(LegalEntity.identifier == legal_entity_identifier). \
            filter(Filing.id == filing_id). \
            one_or_none()
        return None if not filing else filing[1]

    @classmethod
    def get_next_value_from_sequence(cls, business_type: str) -> Optional[int]:
        """Return the next value from the sequence."""
        sequence_mapping = {
            'CP': 'legal_entity_identifier_coop',
            'FM': 'legal_entity_identifier_sp_gp',
        }
        if sequence_name := sequence_mapping.get(business_type, None):
            return db.session.execute(f"SELECT nextval('{sequence_name}')").scalar()
        return None

    @staticmethod
    def validate_identifier(entity_type: EntityTypes, identifier: str) -> bool:
        """Validate the identifier meets the Registry naming standards.

        All legal entities with BC Reg are PREFIX + 7 digits

        CP = BC COOPS prefix;
        XCP = Expro COOP prefix

        Examples:
            ie: CP1234567 or XCP1234567

        """
        if entity_type and entity_type == LegalEntity.EntityTypes.PERSON.value:
            return True

        if identifier[:2] == 'NR':
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
        if identifier[:-7] not in ('CP', 'XCP', 'BC', 'FM'):
            return False

        return True

    @property
    def valid_party_type_data(self) -> bool:
        """Validate the model based on the party type (person/organization)."""
        if self.entity_type != LegalEntity.EntityTypes.PERSON.value:
            if self.first_name or self.middle_initial or self.last_name:
                return False

        if self.entity_type == LegalEntity.EntityTypes.PERSON.value:
            if not (self.first_name or self.middle_initial or self.last_name):
                return False
        return True

    @classmethod
    def find_by_id(cls, legal_entity_id: int):
        """Return a legal enntity by the internal id."""
        legal_entity = None
        if legal_entity_id:
            legal_entity = cls.query.filter_by(id=legal_entity_id).one_or_none()
        return legal_entity


@event.listens_for(LegalEntity, 'before_insert')
@event.listens_for(LegalEntity, 'before_update')
def receive_before_change(mapper, connection, target):  # pylint: disable=unused-argument; SQLAlchemy callback signature
    """Run checks/updates before adding/changing the party model data."""
    party = target

    # skip this party updater if the flag is set
    # Scenario: data loading party data that is missing required party information
    if hasattr(party, 'skip_party_listener') and party.skip_party_listener:
        return

    if not party.valid_party_type_data:
        raise BusinessException(
            error=f'Attempt to change/add {party.entity_type} had invalid data.',
            status_code=HTTPStatus.BAD_REQUEST
        )


ASSOCIATION_TYPE_DESC: Final = {
    LegalEntity.AssociationTypes.CP_COOPERATIVE.value: 'Ordinary Cooperative',
    LegalEntity.AssociationTypes.CP_HOUSING_COOPERATIVE.value: 'Housing Cooperative',
    LegalEntity.AssociationTypes.CP_COMMUNITY_SERVICE_COOPERATIVE.value: 'Community Service Cooperative',

    LegalEntity.AssociationTypes.SP_SOLE_PROPRIETORSHIP.value: 'Sole Proprietorship',
    LegalEntity.AssociationTypes.SP_DOING_BUSINESS_AS.value: 'Sole Proprietorship (DBA)'
}
