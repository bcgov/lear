# Copyright © 2021 Province of British Columbia
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
# limitations under the License
"""The business and its historical values.
This is the core business class.
It is used to represent a business and its historical values.
"""
from enum import Enum, auto
from typing import Final

import datedelta
from sql_versioning import history_cls

from legal_api.utils.base import BaseEnum
from legal_api.utils.datetime import datetime

from .db import db


# pylint: disable=no-member,import-outside-toplevel,protected-access
class BusinessCommon:
    """This class is used to share common properties and functions between LegalEntity and AlternateName."""

    class State(BaseEnum):
        """Enum for the Business state."""

        ACTIVE = auto()
        HISTORICAL = auto()

    # NB: commented out items that exist in namex but are not yet supported by Lear
    class EntityTypes(str, Enum):
        """Render an Enum of the Business Legal Types."""

        BCOMP = "BEN"  # aka BENEFIT_COMPANY in namex
        BC_CCC = "CC"
        BC_ULC_COMPANY = "ULC"
        CCC_CONTINUE_IN = "CCC"
        CEMETARY = "CEM"
        CO_1860 = "QA"
        CO_1862 = "QB"
        CO_1878 = "QC"
        CO_1890 = "QD"
        CO_1897 = "QE"
        COMP = "BC"  # aka CORPORATION in namex
        CONT_IN_SOCIETY = "CS"
        CONTINUE_IN = "C"
        COOP = "CP"  # aka COOPERATIVE in namex
        EXTRA_PRO_A = "A"
        EXTRA_PRO_B = "B"
        EXTRA_PRO_REG = "EPR"
        FINANCIAL = "FI"
        FOREIGN = "FOR"
        LIBRARY = "LIB"
        LICENSED = "LIC"
        LIM_PARTNERSHIP = "LP"
        LIMITED_CO = "LLC"
        LL_PARTNERSHIP = "LL"
        MISC_FIRM = "MF"
        ORGANIZATION = "organization"
        PARISHES = "PAR"
        PARTNERSHIP = "GP"
        PENS_FUND_SOC = "PFS"
        PERSON = "person"
        PRIVATE_ACT = "PA"
        RAILWAYS = "RLY"
        REGISTRATION = "REG"
        SOCIETY = "S"
        SOCIETY_BRANCH = "SB"
        SOLE_PROP = "SP"
        TRAMWAYS = "TMY"
        TRUST = "T"
        ULC_CONTINUE_IN = "CUL"
        ULC_CO_1860 = "UQA"
        ULC_CO_1862 = "UQB"
        ULC_CO_1878 = "UQC"
        ULC_CO_1890 = "UQD"
        ULC_CO_1897 = "UQE"
        XPRO_COOP = "XCP"
        XPRO_LIM_PARTNR = "XP"
        XPRO_LL_PARTNR = "XL"
        XPRO_SOCIETY = "XS"
        # *** The following are not yet supported by legal-api: ***
        # DOING_BUSINESS_AS = 'DBA'
        # XPRO_CORPORATION = 'XCR'
        # XPRO_UNLIMITED_LIABILITY_COMPANY = 'XUL'

    LIMITED_COMPANIES: Final = [
        EntityTypes.COMP,
        EntityTypes.CONTINUE_IN,
        EntityTypes.CO_1860,
        EntityTypes.CO_1862,
        EntityTypes.CO_1878,
        EntityTypes.CO_1890,
        EntityTypes.CO_1897,
    ]

    UNLIMITED_COMPANIES: Final = [
        EntityTypes.BC_ULC_COMPANY,
        EntityTypes.ULC_CONTINUE_IN,
        EntityTypes.ULC_CO_1860,
        EntityTypes.ULC_CO_1862,
        EntityTypes.ULC_CO_1878,
        EntityTypes.ULC_CO_1890,
        EntityTypes.ULC_CO_1897,
    ]

    NON_BUSINESS_ENTITY_TYPES: Final = [EntityTypes.PERSON, EntityTypes.ORGANIZATION]

    @property
    def is_alternate_name_entity(self):
        """Return True if the entity is an AlternateName."""
        from legal_api.models import AlternateName

        return isinstance(self, (AlternateName, history_cls(AlternateName)))

    @property
    def is_legal_entity(self):
        """Return True if the entity is a LegalEntity."""
        from legal_api.models import LegalEntity

        return isinstance(self, (LegalEntity, history_cls(LegalEntity)))

    @property
    def compliance_warnings(self):
        """Return compliance warnings."""
        if not hasattr(self, "_compliance_warnings"):
            return []

        return self._compliance_warnings

    @compliance_warnings.setter
    def compliance_warnings(self, value):
        """Set compliance warnings."""
        self._compliance_warnings = value

    @property
    def warnings(self):
        """Return warnings."""
        if not hasattr(self, "_warnings"):
            return []

        return self._warnings

    @warnings.setter
    def warnings(self, value):
        """Set warnings."""
        self._warnings = value

    @property
    def allowable_actions(self):
        """Return warnings."""
        if not hasattr(self, "_allowable_actions"):
            return {}

        return self._allowable_actions

    @allowable_actions.setter
    def allowable_actions(self, value):
        """Set warnings."""
        self._allowable_actions = value

    @property
    def is_firm(self):
        """Return if is firm, otherwise false."""
        return self.entity_type in [
            self.EntityTypes.SOLE_PROP.value,
            self.EntityTypes.PARTNERSHIP.value,
        ]

    @property
    def legal_name(self):
        """Return legal name.
        For SP individual, return person LE's legal name.
        For SP DBA where owner is in LEAR, return firm owner LE's legal name.
        For SP DBA where owner is in COLIN, return firm owner's CE's organization name.
        For others, return LE's legal name.
        """
        from . import ColinEntity, LegalEntity

        if self.is_alternate_name_entity:
            if self.legal_entity_id:
                owner = LegalEntity.find_by_id(self.legal_entity_id)
                return owner._legal_name if owner else None
            else:
                owner = ColinEntity.find_by_id(self.colin_entity_id)
                return owner.organization_name if owner else None

        return self._legal_name

    @property
    def business_name(self):
        """Return operating name for firms and legal name for non-firm entities.

        For SP, returns its operating name from AlternateName.
        For GP, returns its primary operating name from AlternateName.
        """
        from legal_api.models import AlternateName

        if not self.is_firm:
            return self._legal_name

        if alternate_name := AlternateName.find_by_identifier(identifier=self.identifier):
            return alternate_name.name

        return None

    @property
    def good_standing(self):
        """Return true if in good standing, otherwise false."""
        # A firm is always in good standing
        # from legal_api.models import LegalEntity

        if self.is_firm:
            return True
        # Date of last AR or founding date if they haven't yet filed one
        last_ar_date = self.last_ar_date or self.founding_date
        # Good standing is if last AR was filed within the past 1 year, 2 months and 1 day and is in an active state
        if self.state == BusinessCommon.State.ACTIVE:
            if self.restoration_expiry_date:
                return False  # A business in limited restoration is not in good standing
            else:
                return last_ar_date + datedelta.datedelta(years=1, months=2, days=1) > datetime.utcnow()
        return True

    def get_filing_by_id(self, filing_id: int):
        """Return the filings for a specific business and filing_id."""
        from legal_api.models import AlternateName, Filing, LegalEntity

        # Determine the model to query based on is_legal_entity property
        if self.is_legal_entity:
            entity_model = LegalEntity
            filing_filter = LegalEntity.id == Filing.legal_entity_id
            entity_filter = LegalEntity.id == self.id
        else:
            entity_model = AlternateName
            filing_filter = AlternateName.id == Filing.alternate_name_id
            entity_filter = AlternateName.id == self.id

        filing = (
            db.session.query(entity_model, Filing)
            .filter(filing_filter)
            .filter(Filing.id == filing_id)
            .filter(entity_filter)
            .one_or_none()
        )

        return None if not filing else filing[1]
