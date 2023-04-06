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
from sqlalchemy.exc import OperationalError, ResourceClosedError
from sqlalchemy.ext.hybrid import hybrid_property

from legal_api.exceptions import BusinessException
from legal_api.utils.base import BaseEnum
from legal_api.utils.datetime import datetime

from .db import db  # noqa: I001
from .filing import Filing  # noqa: F401 I001 pylint: disable=unused-import;


class ShadowBusiness(db.Model):  # pylint: disable=too-many-instance-attributes,disable=too-many-public-methods
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

    __versioned__ = {}
    __tablename__ = 'shadow_businesses'
    __mapper_args__ = {
        'include_properties': [
            'id',
            'founding_date',
            'identifier',
            'legal_name',
            'legal_type',
            'state',
            'state_filing_id',
        ]
    }

    id = db.Column(db.Integer, primary_key=True)
    _identifier = db.Column('identifier', db.String(10), index=True)
    legal_type = db.Column('legal_type', db.String(10))
    legal_name = db.Column('legal_name', db.String(1000), index=True)
    founding_date = db.Column('founding_date', db.DateTime(timezone=True), default=datetime.utcnow)
    state = db.Column('state', db.Enum(State), default=State.ACTIVE.value)
    state_filing_id = db.Column('state_filing_id', db.Integer)

    @hybrid_property
    def identifier(self):
        """Return the unique business identifier."""
        return self._identifier

    @identifier.setter
    def identifier(self, value: str):
        """Set the business identifier."""
        if ShadowBusiness.validate_identifier(value):
            self._identifier = value
        else:
            raise BusinessException('invalid-identifier-format', 406)

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
        elif self.legal_type in [self.LegalTypes.BCOMP.value,
                                 self.LegalTypes.COMP.value,
                                 self.LegalTypes.BC_ULC_COMPANY.value,
                                 self.LegalTypes.BC_CCC.value]:
            # For BCOMP min date is next anniversary date.
            ar_min_date = datetime(next_ar_year, self.founding_date.month, self.founding_date.day).date()
            ar_max_date = ar_min_date + datedelta.datedelta(days=60)

        if ar_max_date > datetime.utcnow().date():
            ar_max_date = datetime.utcnow().date()

        return ar_min_date, ar_max_date

    def is_firm(self):
        """Return if is firm, otherwise false."""
        return self.legal_type in (self.LegalTypes.SOLE_PROP, self.LegalTypes.PARTNERSHIP)

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
    def get_filing_by_id(cls, business_identifier: int, filing_id: str):
        """Return the filings for a specific business and filing_id."""
        filing = db.session.query(ShadowBusiness, Filing). \
            filter(ShadowBusiness.id == Filing.business_id). \
            filter(ShadowBusiness.identifier == business_identifier). \
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
    ShadowBusiness.AssociationTypes.CP_COOPERATIVE.value: 'Ordinary Cooperative',
    ShadowBusiness.AssociationTypes.CP_HOUSING_COOPERATIVE.value: 'Housing Cooperative',
    ShadowBusiness.AssociationTypes.CP_COMMUNITY_SERVICE_COOPERATIVE.value: 'Community Service Cooperative',

    ShadowBusiness.AssociationTypes.SP_SOLE_PROPRIETORSHIP.value: 'Sole Proprietorship',
    ShadowBusiness.AssociationTypes.SP_DOING_BUSINESS_AS.value: 'Sole Proprietorship (DBA)'
}
