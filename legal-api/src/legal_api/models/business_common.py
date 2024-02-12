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
from enum import Enum


class BusinessCommon:
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

    @property
    def is_alternate_name_entity(self):
        from legal_api.models import AlternateName

        return isinstance(self, AlternateName)

    @property
    def is_legal_entity(self):
        from legal_api.models import LegalEntity

        return isinstance(self, LegalEntity)

    @property
    def entity_type(self):
        """Return entity_type."""

        if self.is_legal_entity:
            return self._entity_type

        # TODO flesh this logic out fully
        return "SP"

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

        if self.entity_type == self.EntityTypes.SOLE_PROP:
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
