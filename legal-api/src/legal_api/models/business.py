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
"""This module holds all of the basic data about a business.

The Business class and Schema are held in this module
"""
from enum import Enum, auto
from typing import Final, Optional

import datedelta
from flask import current_app
from sqlalchemy.exc import OperationalError, ResourceClosedError
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref

from legal_api.exceptions import BusinessException
from legal_api.utils.base import BaseEnum
from legal_api.utils.datetime import datetime, timezone
from legal_api.utils.legislation_datetime import LegislationDatetime

from .db import db  # noqa: I001
from .share_class import ShareClass  # noqa: F401,I001,I003 pylint: disable=unused-import


from .address import Address  # noqa: F401,I003 pylint: disable=unused-import; needed by the SQLAlchemy relationship
from .alias import Alias  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy relationship
from .filing import Filing  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy backref
from .office import Office  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy relationship
from .party_role import PartyRole  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy relationship
from .resolution import Resolution  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy backref
from .user import User  # noqa: F401,I003 pylint: disable=unused-import; needed by the SQLAlchemy backref


class Business(db.Model):  # pylint: disable=too-many-instance-attributes
    """This class manages all of the base data about a business.

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
    class LegalTypes(str, Enum):
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
        # *** The following are not yet supported by legal-api: ***
        # DOING_BUSINESS_AS = 'DBA'
        # XPRO_CORPORATION = 'XCR'
        # XPRO_UNLIMITED_LIABILITY_COMPANY = 'XUL'

    LIMITED_COMPANIES: Final = [LegalTypes.COMP,
                                LegalTypes.CONTINUE_IN,
                                LegalTypes.CO_1860,
                                LegalTypes.CO_1862,
                                LegalTypes.CO_1878,
                                LegalTypes.CO_1890,
                                LegalTypes.CO_1897]

    UNLIMITED_COMPANIES: Final = [LegalTypes.BC_ULC_COMPANY,
                                  LegalTypes.ULC_CONTINUE_IN,
                                  LegalTypes.ULC_CO_1860,
                                  LegalTypes.ULC_CO_1862,
                                  LegalTypes.ULC_CO_1878,
                                  LegalTypes.ULC_CO_1890,
                                  LegalTypes.ULC_CO_1897]

    class AssociationTypes(Enum):
        """Render an Enum of the Business Association Types."""

        CP_COOPERATIVE = 'CP'
        CP_HOUSING_COOPERATIVE = 'HC'
        CP_COMMUNITY_SERVICE_COOPERATIVE = 'CSC'

        SP_SOLE_PROPRIETORSHIP = 'SP'
        SP_DOING_BUSINESS_AS = 'DBA'

    __versioned__ = {}
    __tablename__ = 'businesses'
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
            'last_coa_date',
            'last_cod_date',
            'last_ledger_id',
            'last_ledger_timestamp',
            'last_modified',
            'last_remote_ledger_id',
            'legal_name',
            'legal_type',
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
            'foreignIdentifier',
            'foreignLegalName',
            'foreignLegalType',
            'foreignIncorporationDate'
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
    legal_type = db.Column('legal_type', db.String(10))
    founding_date = db.Column('founding_date', db.DateTime(timezone=True), default=datetime.utcnow)
    start_date = db.Column('start_date', db.DateTime(timezone=True))
    dissolution_date = db.Column('dissolution_date', db.DateTime(timezone=True), default=None)
    _identifier = db.Column('identifier', db.String(10), index=True)
    tax_id = db.Column('tax_id', db.String(15), index=True)
    fiscal_year_end_date = db.Column('fiscal_year_end_date', db.DateTime(timezone=True), default=datetime.utcnow)
    restriction_ind = db.Column('restriction_ind', db.Boolean, unique=False, default=False)
    last_ar_year = db.Column('last_ar_year', db.Integer)
    association_type = db.Column('association_type', db.String(50))
    state = db.Column('state', db.Enum(State), default=State.ACTIVE.value)
    state_filing_id = db.Column('state_filing_id', db.Integer)
    admin_freeze = db.Column('admin_freeze', db.Boolean, unique=False, default=False)
    submitter_userid = db.Column('submitter_userid', db.Integer, db.ForeignKey('users.id'))
    submitter = db.relationship('User', backref=backref('submitter', uselist=False), foreign_keys=[submitter_userid])

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
    party_roles = db.relationship('PartyRole', lazy='dynamic')
    share_classes = db.relationship('ShareClass', lazy='dynamic', cascade='all, delete, delete-orphan')
    aliases = db.relationship('Alias', lazy='dynamic')
    resolutions = db.relationship('Resolution', lazy='dynamic')
    documents = db.relationship('Document', lazy='dynamic')

    @hybrid_property
    def identifier(self):
        """Return the unique business identifier."""
        return self._identifier

    @identifier.setter
    def identifier(self, value: str):
        """Set the business identifier."""
        if Business.validate_identifier(value):
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

        if self.legal_type == self.LegalTypes.COOP.value:
            # This could extend by moving it into a table with start and end date against each year when extension
            # is required. We need more discussion to understand different scenario's which can come across in future.
            if next_ar_year == 2020:
                # For year 2020, set the max date as October 31th next year (COVID extension).
                ar_max_date = datetime(next_ar_year + 1, 10, 31).date()
            else:
                # If this is a CO-OP, set the max date as April 30th next year.
                ar_max_date = datetime(next_ar_year + 1, 4, 30).date()
        elif self.legal_type == self.LegalTypes.BCOMP.value:
            # For BCOMP min date is next anniversary date.
            ar_min_date = datetime(next_ar_year, self.founding_date.month, self.founding_date.day).date()
            ar_max_date = ar_min_date + datedelta.datedelta(days=60)

        if ar_max_date > datetime.utcnow().date():
            ar_max_date = datetime.utcnow().date()

        return ar_min_date, ar_max_date

    @property
    def mailing_address(self):
        """Return the mailing address."""
        registered_office = db.session.query(Office).filter(Office.business_id == self.id).\
            filter(Office.office_type == 'registeredOffice').one_or_none()
        if registered_office:
            return registered_office.addresses.filter(Address.address_type == 'mailing')
        elif (business_office := db.session.query(Office)  # SP/GP
              .filter(Office.business_id == self.id)
              .filter(Office.office_type == 'businessOffice').one_or_none()):
            return business_office.addresses.filter(Address.address_type == 'mailing')

        return db.session.query(Address).filter(Address.business_id == self.id). \
            filter(Address.address_type == Address.MAILING)

    @property
    def delivery_address(self):
        """Return the delivery address."""
        registered_office = db.session.query(Office).filter(Office.business_id == self.id).\
            filter(Office.office_type == 'registeredOffice').one_or_none()
        if registered_office:
            return registered_office.addresses.filter(Address.address_type == 'delivery')
        elif (business_office := db.session.query(Office)  # SP/GP
              .filter(Office.business_id == self.id)
              .filter(Office.office_type == 'businessOffice').one_or_none()):
            return business_office.addresses.filter(Address.address_type == 'delivery')

        return db.session.query(Address).filter(Address.business_id == self.id).\
            filter(Address.address_type == Address.DELIVERY)

    @property
    def is_firm(self):
        """Return if is firm, otherwise false."""
        return self.legal_type in (self.LegalTypes.SOLE_PROP, self.LegalTypes.PARTNERSHIP)

    @property
    def good_standing(self):
        """Return true if in good standing, otherwise false."""
        # A firm is always in good standing
        if self.is_firm:
            return True
        # Date of last AR or founding date if they haven't yet filed one
        last_ar_date = self.last_ar_date or self.founding_date
        is_active = self.state.name == Business.State.ACTIVE.name
        # Good standing is if last AR was filed within the past 1 year, 2 months and 1 day and is in an active state
        return last_ar_date + datedelta.datedelta(years=1, months=2, days=1) > datetime.utcnow() and is_active

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

    def json(self):
        """Return the Business as a json object.

        None fields are not included.
        """
        base_url = current_app.config.get('LEGAL_API_BASE_URL')
        ar_min_date, ar_max_date = self.get_ar_dates(
            (self.last_ar_year if self.last_ar_year else self.founding_date.year) + 1
        )
        d = {
            'arMinDate': ar_min_date.isoformat(),
            'arMaxDate': ar_max_date.isoformat(),
            'adminFreeze': self.admin_freeze or False,
            'state': self.state.name if self.state else Business.State.ACTIVE.name,
            'foundingDate': self.founding_date.isoformat(),
            'goodStanding': self.good_standing,
            'hasRestrictions': self.restriction_ind,
            'identifier': self.identifier,
            'complianceWarnings': self.compliance_warnings,
            'warnings': self.warnings,
            'lastAnnualGeneralMeetingDate': datetime.date(self.last_agm_date).isoformat() if self.last_agm_date else '',
            'lastAnnualReportDate': datetime.date(self.last_ar_date).isoformat() if self.last_ar_date else '',
            'lastLedgerTimestamp': self.last_ledger_timestamp.isoformat(),
            'lastAddressChangeDate': '',
            'lastDirectorChangeDate': '',
            'lastModified': self.last_modified.isoformat(),
            'legalName': self.legal_name,
            'legalType': self.legal_type,
            'naicsKey': self.naics_key,
            'naicsCode': self.naics_code,
            'naicsDescription': self.naics_description,
            'nextAnnualReport': LegislationDatetime.as_legislation_timezone_from_date(
                self.next_anniversary
            ).astimezone(timezone.utc).isoformat(),
            'associationType': self.association_type
        }

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
        if self.tax_id:
            d['taxId'] = self.tax_id
        if self.state_filing_id:
            d['stateFiling'] = f'{base_url}/{self.identifier}/filings/{self.state_filing_id}'

        if self.start_date:
            d['startDate'] = datetime.date(
                LegislationDatetime.as_legislation_timezone(self.start_date)
            ).isoformat()

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
        return d

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

    @classmethod
    def find_by_legal_name(cls, legal_name: str = None):
        """Given a legal_name, this will return an Active Business."""
        business = None
        if legal_name:
            try:
                business = cls.query.filter_by(legal_name=legal_name).\
                    filter_by(dissolution_date=None).one_or_none()
            except (OperationalError, ResourceClosedError):
                # TODO: This usually means a misconfigured database.
                # This is not a business error if the cache is unavailable.
                return None
        return business

    @classmethod
    def find_by_identifier(cls, identifier: str = None):
        """Return a Business by the id assigned by the Registrar."""
        business = None
        if identifier:
            business = cls.query.filter_by(identifier=identifier).one_or_none()
        return business

    @classmethod
    def find_by_internal_id(cls, internal_id: int = None):
        """Return a Business by the internal id."""
        business = None
        if internal_id:
            business = cls.query.filter_by(id=internal_id).one_or_none()
        return business

    @classmethod
    def find_by_tax_id(cls, tax_id: str):
        """Return a Business by the tax_id."""
        business = None
        if tax_id:
            business = cls.query.filter_by(tax_id=tax_id).one_or_none()
        return business

    @classmethod
    def get_all_by_no_tax_id(cls):
        """Return all businesses with no tax_id."""
        no_tax_id_types = [
            Business.LegalTypes.COOP.value,
            Business.LegalTypes.SOLE_PROP.value,
            Business.LegalTypes.PARTNERSHIP.value,
        ]
        businesses = cls.query.filter(~Business.legal_type.in_(no_tax_id_types)).filter_by(tax_id=None).all()
        return businesses

    @classmethod
    def get_filing_by_id(cls, business_identifier: int, filing_id: str):
        """Return the filings for a specific business and filing_id."""
        filing = db.session.query(Business, Filing). \
            filter(Business.id == Filing.business_id). \
            filter(Business.identifier == business_identifier). \
            filter(Filing.id == filing_id). \
            one_or_none()
        return None if not filing else filing[1]

    @classmethod
    def get_next_value_from_sequence(cls, business_type: str) -> Optional[int]:
        """Return the next value from the sequence."""
        sequence_mapping = {
            'CP': 'business_identifier_coop',
            'FM': 'business_identifier_sp_gp',
        }
        if sequence_name := sequence_mapping.get(business_type, None):
            return db.session.execute(f"SELECT nextval('{sequence_name}')").scalar()
        return None

    @staticmethod
    def validate_identifier(identifier: str) -> bool:
        """Validate the identifier meets the Registry naming standards.

        All legal entities with BC Reg are PREFIX + 7 digits

        CP = BC COOPS prefix;
        XCP = Expro COOP prefix

        Examples:
            ie: CP1234567 or XCP1234567

        """
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


ASSOCIATION_TYPE_DESC: Final = {
    Business.AssociationTypes.CP_COOPERATIVE.value: 'Ordinary Cooperative',
    Business.AssociationTypes.CP_HOUSING_COOPERATIVE.value: 'Housing Cooperative',
    Business.AssociationTypes.CP_COMMUNITY_SERVICE_COOPERATIVE.value: 'Community Service Cooperative',

    Business.AssociationTypes.SP_SOLE_PROPRIETORSHIP.value: 'Sole Proprietorship',
    Business.AssociationTypes.SP_DOING_BUSINESS_AS.value: 'Sole Proprietorship (DBA)'
}
