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
import re
from enum import Enum, auto
from typing import Final, Optional

import datedelta
import pytz
from flask import current_app
from sql_versioning import Versioned
from sqlalchemy.exc import OperationalError, ResourceClosedError
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import aliased, backref
from sqlalchemy.sql import and_, exists, func, not_, text

from legal_api.exceptions import BusinessException
from legal_api.utils.base import BaseEnum
from legal_api.utils.datetime import datetime, timezone
from legal_api.utils.legislation_datetime import LegislationDatetime

from .amalgamation import Amalgamation  # noqa: F401, I001, I003 pylint: disable=unused-import
from .batch import Batch  # noqa: F401, I001, I003 pylint: disable=unused-import
from .batch_processing import BatchProcessing  # noqa: F401, I001, I003 pylint: disable=unused-import
from .db import db, VersioningProxy  # noqa: I001
from .party import Party
from .share_class import ShareClass  # noqa: F401,I001,I003 pylint: disable=unused-import


from .address import Address  # noqa: F401,I003 pylint: disable=unused-import; needed by the SQLAlchemy relationship
from .alias import Alias  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy relationship
from .filing import Filing  # noqa: F401, I003 pylint: disable=unused-import; needed by the SQLAlchemy backref
from .office import Office  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy relationship
from .party_role import PartyRole  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy relationship
from .resolution import Resolution  # noqa: F401 pylint: disable=unused-import; needed by the SQLAlchemy backref
from .user import User  # noqa: F401,I003 pylint: disable=unused-import; needed by the SQLAlchemy backref


class Business(db.Model, Versioned):  # pylint: disable=too-many-instance-attributes,disable=too-many-public-methods
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
        BCOMP_CONTINUE_IN = 'CBEN'
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
        CCC_CONTINUE_IN = 'CCC'
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

    CORPS: Final = [
        LegalTypes.BCOMP.value,
        LegalTypes.COMP.value,
        LegalTypes.BC_CCC.value,
        LegalTypes.BC_ULC_COMPANY.value,
        LegalTypes.BCOMP_CONTINUE_IN.value,
        LegalTypes.CONTINUE_IN.value,
        LegalTypes.CCC_CONTINUE_IN.value,
        LegalTypes.ULC_CONTINUE_IN.value,
    ]

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

    BUSINESSES = {
        LegalTypes.BCOMP: {
            'numberedLegalNameSuffix': 'B.C. LTD.',
            'numberedDescription': 'Numbered Benefit Company'
        },
        LegalTypes.COMP: {
            'numberedLegalNameSuffix': 'B.C. LTD.',
            'numberedDescription': 'Numbered Limited Company'
        },
        LegalTypes.BC_ULC_COMPANY: {
            'numberedLegalNameSuffix': 'B.C. UNLIMITED LIABILITY COMPANY',
            'numberedDescription': 'Numbered Unlimited Liability Company'
        },
        LegalTypes.BC_CCC: {
            'numberedLegalNameSuffix': 'B.C. COMMUNITY CONTRIBUTION COMPANY LTD.',
            'numberedDescription': 'Numbered Community Contribution Company'
        }
    }

    # CORPS Continuation In has the same suffix and desc
    BUSINESSES[LegalTypes.BCOMP_CONTINUE_IN] = BUSINESSES[LegalTypes.BCOMP]
    BUSINESSES[LegalTypes.CONTINUE_IN] = BUSINESSES[LegalTypes.COMP]
    BUSINESSES[LegalTypes.ULC_CONTINUE_IN] = BUSINESSES[LegalTypes.BC_ULC_COMPANY]
    BUSINESSES[LegalTypes.CCC_CONTINUE_IN] = BUSINESSES[LegalTypes.BC_CCC]

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
            'last_ar_reminder_year',
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
            'no_dissolution',
            'start_date',
            'jurisdiction',
            'foreign_jurisdiction_region',
            'foreign_legal_name',
            'send_ar_ind',
            'restoration_expiry_date',
            'continuation_out_date'
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
    restoration_expiry_date = db.Column('restoration_expiry_date', db.DateTime(timezone=True))
    dissolution_date = db.Column('dissolution_date', db.DateTime(timezone=True), default=None)
    continuation_out_date = db.Column('continuation_out_date', db.DateTime(timezone=True))
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
    no_dissolution = db.Column('no_dissolution', db.Boolean, unique=False, default=False)

    naics_key = db.Column(db.String(50))
    naics_code = db.Column(db.String(10))
    naics_description = db.Column(db.String(150))

    jurisdiction = db.Column('foreign_jurisdiction', db.String(10))
    foreign_jurisdiction_region = db.Column('foreign_jurisdiction_region', db.String(10))
    foreign_legal_name = db.Column(db.String(1000))

    # relationships
    filings = db.relationship('Filing', lazy='dynamic')
    offices = db.relationship('Office', backref='business', lazy='dynamic', cascade='all, delete, delete-orphan')
    party_roles = db.relationship('PartyRole', lazy='dynamic')
    share_classes = db.relationship('ShareClass', backref='business', lazy='dynamic',
                                    cascade='all, delete, delete-orphan')
    aliases = db.relationship('Alias', lazy='dynamic')
    resolutions = db.relationship('Resolution', lazy='dynamic')
    documents = db.relationship('Document', lazy='dynamic')
    consent_continuation_outs = db.relationship('ConsentContinuationOut', lazy='dynamic')
    amalgamating_businesses = db.relationship('AmalgamatingBusiness', lazy='dynamic')
    amalgamation = db.relationship('Amalgamation', lazy='dynamic')
    batch_processing = db.relationship('BatchProcessing', lazy='dynamic')
    jurisdictions = db.relationship('Jurisdiction', lazy='dynamic')

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

    @hybrid_property
    def business_legal_name(self):
        """
        Return correct legal name based on feature flag.

        Legal Name Easy Fix
        """
        if self.is_firm:
            sort_name = func.trim(
                func.coalesce(Party.organization_name, '') +
                func.coalesce(Party.last_name + ' ', '') +
                func.coalesce(Party.first_name + ' ', '') +
                func.coalesce(Party.middle_initial, '')
            )

            parties_query = self.party_roles.join(Party).filter(
                func.lower(PartyRole.role).in_([
                    PartyRole.RoleTypes.PARTNER.value,
                    PartyRole.RoleTypes.PROPRIETOR.value
                ]),
                PartyRole.cessation_date.is_(None)
            ).order_by(sort_name)

            parties = [party_role.party for party_role in parties_query.all()]

            legal_names = ', '.join(party.name for party in parties[:2])
            if len(parties) > 2:
                legal_names += ', et al'
            return legal_names

        return self.legal_name

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
        elif self.legal_type in self.CORPS:
            # For BCOMP min date is next anniversary date.
            no_of_years_to_add = next_ar_year - self.founding_date.year
            ar_min_date = self.founding_date.date() + datedelta.datedelta(years=no_of_years_to_add)
            ar_max_date = ar_min_date + datedelta.datedelta(days=60)

        ar_max_date = min(ar_max_date, datetime.utcnow().date())  # ar_max_date cannot be in future

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
        from legal_api.services import flags  # pylint: disable=import-outside-toplevel

        # A firm is always in good standing
        if self.is_firm:
            return True
        # When involuntary dissolution feature flag is on, check transition filing
        if flags.is_on('enable_involuntary_dissolution'):
            if self._has_no_transition_filed_after_restoration():
                return False
        # Date of last AR or founding date if they haven't yet filed one
        last_ar_date = self.last_ar_date or self.founding_date
        # Good standing is if last AR was filed within the past 1 year, 2 months and 1 day and is in an active state
        if self.state == Business.State.ACTIVE:
            if self.restoration_expiry_date:
                return False  # A business in limited restoration is not in good standing
            else:
                # This cutoff date is a naive datetime. We need to use replace to make it timezone aware
                date_cutoff = last_ar_date + datedelta.datedelta(years=1, months=2, days=1)
                return date_cutoff.replace(tzinfo=pytz.UTC) > datetime.utcnow()
        return True

    def _has_no_transition_filed_after_restoration(self) -> bool:
        """Return True for no transition filed after restoration check. Otherwise, return False.

        Check whether the business needs to file Transition but does not file it within 12 months after restoration.
        """
        from legal_api.core.filing import Filing as CoreFiling  # pylint: disable=import-outside-toplevel

        new_act_date = func.date('2004-03-29 00:00:00+00:00')
        restoration_filing = aliased(Filing)
        transition_filing = aliased(Filing)

        restoration_filing_effective_cutoff = restoration_filing.effective_date + text("""INTERVAL '1 YEAR'""")
        condition = exists().where(
            and_(
                self.legal_type != Business.LegalTypes.EXTRA_PRO_A.value,
                self.founding_date < new_act_date,
                restoration_filing.business_id == self.id,
                restoration_filing._filing_type.in_([  # pylint: disable=protected-access
                    CoreFiling.FilingTypes.RESTORATION.value,
                    CoreFiling.FilingTypes.RESTORATIONAPPLICATION.value
                ]),
                restoration_filing._status == Filing.Status.COMPLETED.value,  # pylint: disable=protected-access
                restoration_filing_effective_cutoff <= func.timezone('UTC', func.now()),
                not_(
                    exists().where(
                        and_(
                            transition_filing.business_id == self.id,
                            transition_filing._filing_type == \
                            CoreFiling.FilingTypes.TRANSITION.value,  # pylint: disable=protected-access
                            transition_filing._status == \
                            Filing.Status.COMPLETED.value,  # pylint: disable=protected-access
                            transition_filing.effective_date.between(
                                restoration_filing.effective_date,
                                restoration_filing_effective_cutoff
                            )
                        )
                    )
                )
            )
        )
        return db.session.query(condition).scalar()

    @property
    def in_dissolution(self):
        """Return true if in dissolution, otherwise false."""
        # check a business has a batch_processing entry that matches business_id and status is not COMPLETED
        find_in_batch_processing = db.session.query(BatchProcessing, Batch).\
            filter(BatchProcessing.business_id == self.id).\
            filter(BatchProcessing.status.notin_([BatchProcessing.BatchProcessingStatus.COMPLETED,
                                                  BatchProcessing.BatchProcessingStatus.WITHDRAWN])). \
            filter(Batch.id == BatchProcessing.batch_id).\
            filter(Batch.status != Batch.BatchStatus.COMPLETED).\
            filter(Batch.batch_type == Batch.BatchType.INVOLUNTARY_DISSOLUTION).\
            one_or_none()
        return find_in_batch_processing is not None

    @property
    def is_tombstone(self):
        """Return True if it's a tombstone business, otherwise False."""
        tombstone_filing = Filing.get_filings_by_status(self.id, [Filing.Status.TOMBSTONE])
        return bool(tombstone_filing)

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
            'naicsKey': self.naics_key,
            'naicsCode': self.naics_code,
            'naicsDescription': self.naics_description,
            'nextAnnualReport': LegislationDatetime.as_legislation_timezone_from_date(
                self.next_anniversary
            ).astimezone(timezone.utc).isoformat(),
            'noDissolution': self.no_dissolution,
            'associationType': self.association_type,
            'allowedActions': self.allowable_actions,
            'alternateNames': self.get_alternate_names()
        }
        self._extend_json(d)

        return d

    def _slim_json(self):
        """Return a smaller/faster version of the business json."""
        d = {
            'adminFreeze': self.admin_freeze or False,
            'goodStanding': self.good_standing,
            'identifier': self.identifier,
            'inDissolution': self.in_dissolution,
            'legalName': self.business_legal_name,
            'legalType': self.legal_type,
            'state': self.state.name if self.state else Business.State.ACTIVE.name,
            'lastModified': self.last_modified.isoformat()
        }

        if self.tax_id:
            d['taxId'] = self.tax_id

        return d

    def _extend_json(self, d):
        """Include conditional fields to json."""
        base_url = current_app.config.get('LEGAL_API_BASE_URL')

        if self.last_coa_date:
            d['lastAddressChangeDate'] = LegislationDatetime.format_as_legislation_date(self.last_coa_date)
        if self.last_cod_date:
            d['lastDirectorChangeDate'] = LegislationDatetime.format_as_legislation_date(self.last_cod_date)

        if self.dissolution_date:
            d['dissolutionDate'] = LegislationDatetime.format_as_legislation_date(self.dissolution_date)

        if self.fiscal_year_end_date:
            d['fiscalYearEndDate'] = datetime.date(self.fiscal_year_end_date).isoformat()
        if self.state_filing_id:
            if (amalgamated_into := self.get_amalgamated_into()):
                d['amalgamatedInto'] = amalgamated_into
            else:
                d['stateFiling'] = f'{base_url}/{self.identifier}/filings/{self.state_filing_id}'

        if self.start_date:
            d['startDate'] = LegislationDatetime.format_as_legislation_date(self.start_date)

        if self.restoration_expiry_date:
            d['restorationExpiryDate'] = LegislationDatetime.format_as_legislation_date(self.restoration_expiry_date)
        if self.continuation_out_date:
            d['continuationOutDate'] = LegislationDatetime.format_as_legislation_date(self.continuation_out_date)

        if self.jurisdiction:
            d['jurisdiction'] = self.jurisdiction
            d['jurisdictionRegion'] = self.foreign_jurisdiction_region
            d['foreignLegalName'] = self.foreign_legal_name

        d['hasCorrections'] = Filing.has_completed_filing(self.id, 'correction')
        d['hasCourtOrders'] = Filing.has_completed_filing(self.id, 'courtOrder')

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

    @allowable_actions.setter
    def allowable_actions(self, value):
        """Set warnings."""
        self._allowable_actions = value

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
        businesses = (db.session.query(Business.identifier)
                      .filter(
                          ~Business.legal_type.in_(no_tax_id_types),
                          Business.tax_id == None)  # pylint: disable=singleton-comparison # noqa: E711;
                      .all())
        return businesses

    @classmethod
    def get_expired_restoration(cls):
        """Return all identifier with an expired restoration_expiry_date."""
        businesses = (db.session.query(Business.identifier)
                      .filter(Business.restoration_expiry_date <= datetime.utcnow())
                      .all())
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

    def get_alternate_names(self) -> dict:
        """Get alternate names for this business.

        - Return name translation (alias table) entries if any
        - Return SP DBA entries in alternate name entries if not SP
        - For SP or GP, also return an alternate name from existing business record
        - Return empty list if there are no alternate name entries
        """
        alternate_names = []

        # Fetch aliases and related filings in a single query
        alias_version = VersioningProxy.version_class(db.session(), Alias)
        filing_alias = aliased(Filing)
        aliases_query = db.session.query(
            alias_version.alias,
            alias_version.type,
            filing_alias.effective_date
        ).outerjoin(
            filing_alias, filing_alias.transaction_id == alias_version.transaction_id
        ).filter(
            alias_version.id.in_([a.id for a in self.aliases]),
            alias_version.end_transaction_id is None  # noqa: E711
        )

        for alias, alias_type, effective_date in aliases_query:
            alternate_names.append({
                'name': alias,
                'startDate': LegislationDatetime.format_as_legislation_date(effective_date),
                'type': alias_type
            })

        # Get SP DBA entries if not SP
        if self.legal_type != Business.LegalTypes.SOLE_PROP:
            proprietors_query = db.session.query(
                Business.legal_type,
                Business.identifier,
                Business.legal_name,
                Business.founding_date,
                Business.start_date
            ).join(
                PartyRole, PartyRole.business_id == Business.id
            ).join(
                Party, and_(
                    Party.id == PartyRole.party_id,
                    Party.identifier == self._identifier
                )
            ).filter(
                Party.party_type == Party.PartyTypes.ORGANIZATION.value,
                PartyRole.role == PartyRole.RoleTypes.PROPRIETOR.value
            )

            for legal_type, identifier, legal_name, founding_date, start_date in proprietors_query:
                alternate_names.append({
                    'entityType': legal_type,
                    'identifier': identifier,
                    'name': legal_name,
                    'registeredDate': founding_date.isoformat(),
                    'startDate': LegislationDatetime.format_as_legislation_date(start_date) if start_date else None,
                    'type': 'DBA'
                })

        # For firms also get existing business record
        if self.is_firm:
            alternate_names.append({
                'entityType': self.legal_type,
                'identifier': self.identifier,
                'name': self.legal_name,
                'registeredDate': self.founding_date.isoformat(),
                'startDate':
                    LegislationDatetime.format_as_legislation_date(self.start_date) if self.start_date else None,
                'type': 'DBA'
            })

        return alternate_names

    def get_amalgamated_into(self) -> dict:
        """Get amalgamated into if this business is part of an amalgamation.

        Return TED:
            1. TED is Active and TING is Historical
            2. TED is Historical and TING is Historical (Yet to be Active)
        Return None:
            1. Not a TING (not part of an amalgamation)
            2. TED is Historical and TING is Active (through putBackOn filing)
        """
        if (self.state == Business.State.HISTORICAL and
            self.state_filing_id and
            (state_filing := Filing.find_by_id(self.state_filing_id)) and
                state_filing.is_amalgamation_application):
            if not self.is_tombstone:
                return Amalgamation.get_revision_json(state_filing.transaction_id, state_filing.business_id)
            else:
                return {
                    'identifier': 'Not Available',
                    'legalName': 'Not Available',
                    'amalgamationDate': 'Not Available'
                }

        return None

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
    def generate_numbered_legal_name(cls, legal_type, identifier):
        """Generate legal name for a numbered business."""
        if legal_type not in Business.BUSINESSES:
            return None

        numbered_legal_name_suffix = Business.BUSINESSES[legal_type]['numberedLegalNameSuffix']
        numbered_legal_name_prefix = ''
        if legal_type in (Business.LegalTypes.BCOMP_CONTINUE_IN.value,
                          Business.LegalTypes.ULC_CONTINUE_IN.value,
                          Business.LegalTypes.CCC_CONTINUE_IN.value,
                          Business.LegalTypes.CONTINUE_IN.value):
            numbered_legal_name_prefix = identifier[1:]
        else:
            numbered_legal_name_prefix = identifier[2:]
        return f'{numbered_legal_name_prefix} {numbered_legal_name_suffix}'

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
        BC = BC CORPS (BEN, BC, CC, ULC)
        C = Continuation In BC CORPS (CBEN, C, CCC, CUL)
        FM = Firms (SP, GP)

        Examples:
            ie: CP1234567 or XCP1234567

        """
        if identifier[:2] == 'NR':
            return True

        if not re.match(r'^(CP|XCP|BC|C|FM)\d{7}$', identifier):
            return False

        try:
            d = int(identifier[-7:])
            if d == 0:
                return False
        except ValueError:
            return False

        return True


ASSOCIATION_TYPE_DESC: Final = {
    Business.AssociationTypes.CP_COOPERATIVE.value: 'Ordinary Cooperative',
    Business.AssociationTypes.CP_HOUSING_COOPERATIVE.value: 'Housing Cooperative',
    Business.AssociationTypes.CP_COMMUNITY_SERVICE_COOPERATIVE.value: 'Community Service Cooperative',

    Business.AssociationTypes.SP_SOLE_PROPRIETORSHIP.value: 'Sole Proprietorship',
    Business.AssociationTypes.SP_DOING_BUSINESS_AS.value: 'Sole Proprietorship (DBA)'
}
