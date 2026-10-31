# Copyright © 2026 Province of British Columbia
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
"""
  This file contains all valid business designation strings and their matching allowed legal types.
  Including:
    - All variations (Abbreviations, French, etc).
    - Designation rule: 'suffix', 'non_prefix' or 'none'
      - suffix: Designation be strictly at the very end of the legal name, separated from the entity title by whitespace (e.g., ACME SERVICES INC. or 1234567 B.C. LTD.). It cannot appear at the beginning or in the middle of the name.
      - non_prefix: Designation must appear within the legal name, but forbids it from being the first word. It must be preceded by at least one non-whitespace word and separated by appropriate spacing (e.g., COMMUNITY COOPERATIVE BAKERY is valid, but COOPERATIVE BAKERY is rejected).
      - none: No designation is legally required or enforced for this entity type.
"""
# Ref: https://github.com/bcgov/namerequest/blob/f94717bcb8bebc6284489abb290b1c231c064513/app/src/list-data/designations.ts

from typing import Final, TypedDict, Literal
from business_model.models import Business

LegalTypes = Business.LegalTypes

DesignationRule = Literal["suffix", "non_prefix", "none"]

class DesignationRules(TypedDict):
    rule: DesignationRule
    allowed: tuple[str, ...]

CORP_DESIGNATIONS: Final[tuple[str, ...]] = (
    "CORP.",
    "CORPORATION",
    "INC.",
    "INCORPORATED",
    "LIMITED",
    "LTD.",
    "INCORPOREE",
    "LIMITEE",
    "LTEE.",
)

NUMBERED_CORP_DESIGNATIONS: Final[tuple[str, ...]] = ("B.C. LTD.",)

ULC_DESIGNATIONS: Final[tuple[str, ...]] = (
    "UNLIMITED LIABILITY COMPANY",
    "ULC",
)

NUMBERED_ULC_DESIGNATIONS: Final[tuple[str, ...]] = ("B.C. UNLIMITED LIABILITY COMPANY",)

NUMBERED_CC_DESIGNATIONS: Final[tuple[str, ...]] = ("B.C. COMMUNITY CONTRIBUTION COMPANY LTD.",)

COOP_DESIGNATIONS: Final[tuple[str, ...]] = (
    "CO-OPERATIVE",
    "COOPERATIVE",
    "CO-OP.",
    "COOP",
)

# Designations where trailing dot is optional
ABBREVIATIONS: Final[frozenset[str]] = frozenset({
    "LTD.",
    "INC.",
    "CORP.",
    "LTEE.",
    "ASSN.",
    "CO-OP.",
    "B.C. LTD.",
    "B.C. COMMUNITY CONTRIBUTION COMPANY LTD.",
    "L.L.C.",
    "LIMITED LIABILITY CO.",
})

CORP_RULES: Final[DesignationRules] = {
    "rule": "suffix",
    "allowed": (
        *NUMBERED_CORP_DESIGNATIONS,
        *CORP_DESIGNATIONS,
    ),
}

COMMUNITY_CONTRIBUTION_RULES: Final[DesignationRules] = {
    "rule": "suffix",
    "allowed": (
        *NUMBERED_CC_DESIGNATIONS,
        "CCC",
        "COMMUNITY CONTRIBUTION COMPANY",
        *CORP_DESIGNATIONS,
    ),
}

COOPERATIVE_RULES: Final[DesignationRules] = {
    "rule": "non_prefix",
    "allowed": COOP_DESIGNATIONS,
}

ULC_RULES: Final[DesignationRules] = {
    "rule": "suffix",
    "allowed": (
        *NUMBERED_ULC_DESIGNATIONS,
        *ULC_DESIGNATIONS,
    ),
}

LLP_RULES: Final[DesignationRules] = {
    "rule": "suffix",
    "allowed": (
        "LIMITED LIABILITY PARTNERSHIP",
        "LLP",
        "SENCRL",
        "SRL",
        "SOCIETE A RESPONSABILITE LIMITEE",
        "SOCIETE EN NOM COLLECTIF A RESPONSABILITE LIMITEE",
    ),
}

LP_RULES: Final[DesignationRules] = {
    "rule": "suffix",
    "allowed": ("LIMITED PARTNERSHIP",),
}

RLC_RULES: Final[DesignationRules] = {
    "rule": "suffix",
    "allowed": (
        "L.L.C.",
        "LIMITED LIABILITY CO.",
        "LIMITED LIABILITY COMPANY",
        "LLC",
    ),
}

SOCIETY_RULES: Final[DesignationRules] = {
    "rule": "non_prefix",
    "allowed": (
        "ASSOCIATION",
        "ASSN.",
        "CHAMBER OF COMMERCE",
        "CHURCH",
        "EGLISE",
        "CLUB",
        "CHRISTIAN SCHOOL",
        "FELLOWSHIP",
        "FOUNDATION",
        "FONDATION",
        "GUILD",
        "PARISH",
        "SOCIETY",
        "SOCIETE",
        "WATERSHED",
    ),
}

# No designation enforced
NO_DESIGNATION_RULES: Final[DesignationRules] = {
    "rule": "none",
    "allowed": (),
}

DESIGNATION_RULES: Final[dict[str, DesignationRules]] = {
    # Corporations / Limited Companies
    LegalTypes.COMP.value: CORP_RULES,                # 'BC'
    LegalTypes.CONTINUE_IN.value: CORP_RULES,         # 'C'
    LegalTypes.BCOMP.value: CORP_RULES,               # 'BEN'
    LegalTypes.BCOMP_CONTINUE_IN.value: CORP_RULES,   # 'CBEN'

    # Community Contribution Companies
    LegalTypes.BC_CCC.value: COMMUNITY_CONTRIBUTION_RULES,           # 'CC'
    LegalTypes.CCC_CONTINUE_IN.value: COMMUNITY_CONTRIBUTION_RULES,  # 'CCC'

    # Unlimited Liability Companies
    LegalTypes.BC_ULC_COMPANY.value: ULC_RULES,                # 'ULC'
    LegalTypes.ULC_CONTINUE_IN.value: ULC_RULES,               # 'CUL'

    # Cooperatives
    LegalTypes.COOP.value: COOPERATIVE_RULES,                  # 'CP'
    LegalTypes.XPRO_COOP.value: COOPERATIVE_RULES,             # 'XCP'

    # Partnerships
    LegalTypes.LL_PARTNERSHIP.value: LLP_RULES,                # 'LL'
    LegalTypes.XPRO_LL_PARTNR.value: LLP_RULES,                # 'XL'
    LegalTypes.LIM_PARTNERSHIP.value: LP_RULES,                # 'LP'
    LegalTypes.XPRO_LIM_PARTNR.value: LP_RULES,                # 'XP'

    # Societies
    LegalTypes.SOCIETY.value: SOCIETY_RULES,                   # 'S'
    LegalTypes.XPRO_SOCIETY.value: SOCIETY_RULES,              # 'XS'
    LegalTypes.CONT_IN_SOCIETY.value: SOCIETY_RULES,           # 'CS'

    # Limited Liability Company
    LegalTypes.LIMITED_CO.value: RLC_RULES,                    # 'LLC'

    # Entities with No Designation Required
    LegalTypes.SOLE_PROP.value: NO_DESIGNATION_RULES,           # 'SP'
    LegalTypes.PARTNERSHIP.value: NO_DESIGNATION_RULES,         # 'GP'
    LegalTypes.FINANCIAL.value: NO_DESIGNATION_RULES,           # 'FI'
    LegalTypes.PRIVATE_ACT.value: NO_DESIGNATION_RULES,         # 'PA'
    LegalTypes.PARISHES.value: NO_DESIGNATION_RULES,            # 'PAR'
    LegalTypes.MISC_FIRM.value: NO_DESIGNATION_RULES,           # 'MF'
}
