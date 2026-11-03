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
"""Valid business designation strings, formatting rules, and entity markers.

Designation Rules:
- suffix: The designation must sit strictly at the very end of the legal name,
  separated by whitespace or punctuation (e.g., 'ACME SERVICES INC.', '1234567 B.C. LTD.').
  It cannot appear at the beginning or in the middle.
- non_prefix: The designation may appear anywhere within the legal name except
  as the first word (e.g., 'COMMUNITY COOPERATIVE BAKERY' is valid, but 'COOPERATIVE BAKERY' is rejected).
- none: No designation is legally required or enforced for this entity type.

Markers:
- 'markers' declares statutory identifiers that must be preserved if they already
  exist in the registered legal name (e.g., 'COMMUNITY CONTRIBUTION COMPANY' or 'BENEFIT COMPANY').
- Structured as a tuple of tuples: outer groups are evaluated independently (AND),
  while inner tuples represent statutory interchangeable equivalents (OR)
  (e.g., ('COMMUNITY CONTRIBUTION COMPANY', 'CCC') per s. 51.921(2) BCBCA).
- Markers are only enforced conditionally: if present in the existing registered
  name, they cannot be dropped, but they are not forced upon grandfathered names that lack them.
"""
# Ref: https://github.com/bcgov/namerequest/blob/f94717bcb8bebc6284489abb290b1c231c064513/app/src/list-data/designations.ts
# Ref https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/02057_02#division_d2e4529

from typing import Final, Literal, TypedDict

from business_model.models import Business

LegalTypes = Business.LegalTypes

DesignationRule = Literal["suffix", "non_prefix", "none"]

class DesignationRules(TypedDict, total=False):
    rule: DesignationRule
    allowed: tuple[str, ...]
    markers: tuple[tuple[str, ...], ...]

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

SOCIETY_DESIGNATIONS: Final[tuple[str, ...]] = (
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

BENEFIT_COMPANY_RULES: Final[DesignationRules] = {
    **CORP_RULES,
    "markers": (("BENEFIT COMPANY",),),
}

COMMUNITY_CONTRIBUTION_RULES: Final[DesignationRules] = {
    "rule": "suffix",
    "allowed": (
        *NUMBERED_CC_DESIGNATIONS,
        "CCC",
        "COMMUNITY CONTRIBUTION COMPANY",
        *CORP_DESIGNATIONS,
    ),
    "markers": (("CCC", "COMMUNITY CONTRIBUTION COMPANY"),),
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
    "allowed": SOCIETY_DESIGNATIONS,
}

# No designation enforced
NO_DESIGNATION_RULES: Final[DesignationRules] = {
    "rule": "none",
    "allowed": (),
}

DESIGNATION_RULES: Final[dict[str, DesignationRules]] = {
    # Corporations / Limited Companies
    LegalTypes.COMP.value: CORP_RULES,                               # 'BC'
    LegalTypes.CONTINUE_IN.value: CORP_RULES,                        # 'C'
    LegalTypes.BCOMP.value: BENEFIT_COMPANY_RULES,                   # 'BEN'
    LegalTypes.BCOMP_CONTINUE_IN.value: BENEFIT_COMPANY_RULES,       # 'CBEN'

    # Community Contribution Companies
    LegalTypes.BC_CCC.value: COMMUNITY_CONTRIBUTION_RULES,           # 'CC'
    LegalTypes.CCC_CONTINUE_IN.value: COMMUNITY_CONTRIBUTION_RULES,  # 'CCC'

    # Unlimited Liability Companies
    LegalTypes.BC_ULC_COMPANY.value: ULC_RULES,                      # 'ULC'
    LegalTypes.ULC_CONTINUE_IN.value: ULC_RULES,                     # 'CUL'

    # Cooperatives
    LegalTypes.COOP.value: COOPERATIVE_RULES,                        # 'CP'
    LegalTypes.XPRO_COOP.value: COOPERATIVE_RULES,                   # 'XCP'

    # Partnerships
    LegalTypes.LL_PARTNERSHIP.value: LLP_RULES,                      # 'LL'
    LegalTypes.XPRO_LL_PARTNR.value: LLP_RULES,                      # 'XL'
    LegalTypes.LIM_PARTNERSHIP.value: LP_RULES,                      # 'LP'
    LegalTypes.XPRO_LIM_PARTNR.value: LP_RULES,                      # 'XP'

    # Societies
    LegalTypes.SOCIETY.value: SOCIETY_RULES,                         # 'S'
    LegalTypes.XPRO_SOCIETY.value: SOCIETY_RULES,                    # 'XS'
    LegalTypes.CONT_IN_SOCIETY.value: SOCIETY_RULES,                 # 'CS'

    # Limited Liability Company
    LegalTypes.LIMITED_CO.value: RLC_RULES,                          # 'LLC'

    # Entities with No Designation Required
    LegalTypes.SOLE_PROP.value: NO_DESIGNATION_RULES,                 # 'SP'
    LegalTypes.PARTNERSHIP.value: NO_DESIGNATION_RULES,               # 'GP'
    LegalTypes.FINANCIAL.value: NO_DESIGNATION_RULES,                 # 'FI'
    LegalTypes.PRIVATE_ACT.value: NO_DESIGNATION_RULES,               # 'PA'
    LegalTypes.PARISHES.value: NO_DESIGNATION_RULES,                  # 'PAR'
    LegalTypes.MISC_FIRM.value: NO_DESIGNATION_RULES,                 # 'MF'
}