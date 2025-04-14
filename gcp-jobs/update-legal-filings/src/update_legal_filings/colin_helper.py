# Copyright © 2025 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
""" Helper data for the COLIN API. """
from enum import Enum

class ColinApiTypeCodes(Enum):
    """Render an Enum of the Corporation Type Codes."""

    EXTRA_PRO_A = "A"
    COOP = "CP"
    BCOMP = "BEN"
    BC_COMP = "BC"
    ULC_COMP = "ULC"
    CCC_COMP = "CC"
    BCOMP_CONTINUE_IN = "CBEN"
    CONTINUE_IN = "C"
    CCC_CONTINUE_IN = "CCC"
    ULC_CONTINUE_IN = "CUL"


COLIN_FILING_TYPES = {
        'agmExtension': {
            'type_code_list': ['AGMDT'],
            ColinApiTypeCodes.BCOMP.value: 'AGMDT',
            ColinApiTypeCodes.BC_COMP.value: 'AGMDT',
            ColinApiTypeCodes.ULC_COMP.value: 'AGMDT',
            ColinApiTypeCodes.CCC_COMP.value: 'AGMDT',
            ColinApiTypeCodes.BCOMP_CONTINUE_IN.value: 'AGMDT',
            ColinApiTypeCodes.CONTINUE_IN.value: 'AGMDT',
            ColinApiTypeCodes.ULC_CONTINUE_IN.value: 'AGMDT',
            ColinApiTypeCodes.CCC_CONTINUE_IN.value: 'AGMDT',
        },
        'agmLocationChange': {
            'type_code_list': ['AGMLC'],
            ColinApiTypeCodes.BCOMP.value: 'AGMLC',
            ColinApiTypeCodes.BC_COMP.value: 'AGMLC',
            ColinApiTypeCodes.ULC_COMP.value: 'AGMLC',
            ColinApiTypeCodes.CCC_COMP.value: 'AGMLC',
            ColinApiTypeCodes.BCOMP_CONTINUE_IN.value: 'AGMLC',
            ColinApiTypeCodes.CONTINUE_IN.value: 'AGMLC',
            ColinApiTypeCodes.ULC_CONTINUE_IN.value: 'AGMLC',
            ColinApiTypeCodes.CCC_CONTINUE_IN.value: 'AGMLC',
        },
        'annualReport': {
            'type_code_list': ['OTANN', 'ANNBC'],
            ColinApiTypeCodes.COOP.value: 'OTANN',
            ColinApiTypeCodes.BCOMP.value: 'ANNBC',
            ColinApiTypeCodes.BC_COMP.value: 'ANNBC',
            ColinApiTypeCodes.ULC_COMP.value: 'ANNBC',
            ColinApiTypeCodes.CCC_COMP.value: 'ANNBC',
            ColinApiTypeCodes.BCOMP_CONTINUE_IN.value: 'ANNBC',
            ColinApiTypeCodes.CONTINUE_IN.value: 'ANNBC',
            ColinApiTypeCodes.ULC_CONTINUE_IN.value: 'ANNBC',
            ColinApiTypeCodes.CCC_CONTINUE_IN.value: 'ANNBC',
        },
        'changeOfDirectors': {
            'type_code_list': ['OTCDR', 'NOCDR'],
            ColinApiTypeCodes.COOP.value: 'OTCDR',
            ColinApiTypeCodes.BCOMP.value: 'NOCDR',
            ColinApiTypeCodes.BC_COMP.value: 'NOCDR',
            ColinApiTypeCodes.ULC_COMP.value: 'NOCDR',
            ColinApiTypeCodes.CCC_COMP.value: 'NOCDR',
            ColinApiTypeCodes.BCOMP_CONTINUE_IN.value: 'NOCDR',
            ColinApiTypeCodes.CONTINUE_IN.value: 'NOCDR',
            ColinApiTypeCodes.ULC_CONTINUE_IN.value: 'NOCDR',
            ColinApiTypeCodes.CCC_CONTINUE_IN.value: 'NOCDR',
        },
        'changeOfAddress': {
            'type_code_list': ['OTADD', 'NOCAD'],
            ColinApiTypeCodes.COOP.value: 'OTADD',
            ColinApiTypeCodes.BCOMP.value: 'NOCAD',
            ColinApiTypeCodes.BC_COMP.value: 'NOCAD',
            ColinApiTypeCodes.ULC_COMP.value: 'NOCAD',
            ColinApiTypeCodes.CCC_COMP.value: 'NOCAD',
            ColinApiTypeCodes.BCOMP_CONTINUE_IN.value: 'NOCAD',
            ColinApiTypeCodes.CONTINUE_IN.value: 'NOCAD',
            ColinApiTypeCodes.ULC_CONTINUE_IN.value: 'NOCAD',
            ColinApiTypeCodes.CCC_CONTINUE_IN.value: 'NOCAD',
        },
        'incorporationApplication': {
            'type_code_list': ['OTINC', 'BEINC', 'ICORP', 'ICORU', 'ICORC'],
            ColinApiTypeCodes.COOP.value: 'OTINC',
            ColinApiTypeCodes.BCOMP.value: 'BEINC',
            ColinApiTypeCodes.BC_COMP.value: 'ICORP',
            ColinApiTypeCodes.ULC_COMP.value: 'ICORU',
            ColinApiTypeCodes.CCC_COMP.value: 'ICORC',
        },
        'continuationIn': {
            'type_code_list': ['CONTB', 'CONTI', 'CONTU', 'CONTC'],
            ColinApiTypeCodes.BCOMP_CONTINUE_IN.value: 'CONTB',
            ColinApiTypeCodes.CONTINUE_IN.value: 'CONTI',
            ColinApiTypeCodes.ULC_CONTINUE_IN.value: 'CONTU',
            ColinApiTypeCodes.CCC_CONTINUE_IN.value: 'CONTC',
        },
        'conversion': {
            'type_code_list': ['CONVL'],
            ColinApiTypeCodes.BC_COMP.value: 'CONVL',
            ColinApiTypeCodes.ULC_COMP.value: 'CONVL',
            ColinApiTypeCodes.CCC_COMP.value: 'CONVL'
        },
        'alteration': {
            'type_code_list': ['NOABE', 'NOALE', 'NOALR', 'NOALD', 'NOALA', 'NOALB', 'NOALU', 'NOALC'],
            ColinApiTypeCodes.BCOMP.value: 'NOABE',  # No corp type change
            ColinApiTypeCodes.BC_COMP.value: 'NOALA',  # No corp type change
            ColinApiTypeCodes.ULC_COMP.value: 'NOALA',  # No corp type change
            ColinApiTypeCodes.CCC_COMP.value: 'NOALA',  # No corp type change
            ColinApiTypeCodes.BCOMP_CONTINUE_IN.value: 'NOABE',  # No corp type change
            ColinApiTypeCodes.CONTINUE_IN.value: 'NOALA',  # No corp type change
            ColinApiTypeCodes.ULC_CONTINUE_IN.value: 'NOALA',  # No corp type change
            ColinApiTypeCodes.CCC_CONTINUE_IN.value: 'NOALA',  # No corp type change
            'BC_TO_BEN': 'NOALE',
            'BEN_TO_BC': 'NOALR',
            'ULC_TO_BEN': 'NOALD',
            'ULC_TO_BC': 'NOALB',
            'BC_TO_ULC': 'NOALU',
            'BC_TO_CC': 'NOALC',
            'C_TO_CBEN': 'NOALE',
            'CBEN_TO_C': 'NOALR',
            'CUL_TO_CBEN': 'NOALD',
            'CUL_TO_C': 'NOALB',
            'C_TO_CUL': 'NOALU',
            'C_TO_CCC': 'NOALC',
        },
        'correction': {
            'type_code_list': ['CO_BC', 'CO_DI', 'CO_RR', 'CO_SS'],
            'CORPS_NAME': 'CO_BC',  # company name/translated name
            'CORPS_DIRECTOR': 'CO_DI',
            'CORPS_OFFICE': 'CO_RR',  # registered and record offices
            'CORPS_SHARE': 'CO_SS',
            'CORPS_COMMENT_ONLY': 'CO_LI'  # Called local correction (adding a comment only)
        },
        'specialResolution': {
            'type_code_list': ['OTSPE'],
            ColinApiTypeCodes.COOP.value: 'OTSPE',
        },
        'amalgamationApplication': {
            'sub_type_property': 'type',
            'sub_type_list': ['regular', 'horizontal', 'vertical'],
            'type_code_list': ['OTAMA',
                               'AMLRB', 'AMALR', 'AMLRU', 'AMLRC',
                               'AMLHB', 'AMALH', 'AMLHU', 'AMLHC',
                               'AMLVB', 'AMALV', 'AMLVU', 'AMLVC'],
            'regular': {
                ColinApiTypeCodes.COOP.value: 'OTAMA',
                ColinApiTypeCodes.BCOMP.value: 'AMLRB',
                ColinApiTypeCodes.BC_COMP.value: 'AMALR',
                ColinApiTypeCodes.ULC_COMP.value: 'AMLRU',
                ColinApiTypeCodes.CCC_COMP.value: 'AMLRC'
            },
            'horizontal': {
                ColinApiTypeCodes.COOP.value: 'OTAMA',
                ColinApiTypeCodes.BCOMP.value: 'AMLHB',
                ColinApiTypeCodes.BC_COMP.value: 'AMALH',
                ColinApiTypeCodes.ULC_COMP.value: 'AMLHU',
                ColinApiTypeCodes.CCC_COMP.value: 'AMLHC'
            },
            'vertical': {
                ColinApiTypeCodes.COOP.value: 'OTAMA',
                ColinApiTypeCodes.BCOMP.value: 'AMLVB',
                ColinApiTypeCodes.BC_COMP.value: 'AMALV',
                ColinApiTypeCodes.ULC_COMP.value: 'AMLVU',
                ColinApiTypeCodes.CCC_COMP.value: 'AMLVC'
            }
        },
        'dissolved': {
            'type_code_list': ['OTDIS'],
            ColinApiTypeCodes.COOP.value: 'OTDIS',
        },
        'amendedAGM': {
            'type_code_list': ['OTCGM'],
            ColinApiTypeCodes.COOP.value: 'OTCGM',
        },
        'voluntaryDissolution': {
            'type_code_list': ['OTVDS'],
            ColinApiTypeCodes.COOP.value: 'OTVDS'
        },
        # Note: this should take care of voluntary dissolution filings now but leaving above
        # `voluntaryDissolution filing type in place as unsure if it is being used in other places
        'dissolution': {
            'sub_type_property': 'dissolutionType',
            'sub_type_list': ['voluntary', 'administrative', 'involuntary'],
            'type_code_list': ['OTVDS', 'ADVD2'],
            'voluntary': {
                ColinApiTypeCodes.COOP.value: 'OTVDS',
                ColinApiTypeCodes.BCOMP.value: 'ADVD2',
                ColinApiTypeCodes.BC_COMP.value: 'ADVD2',
                ColinApiTypeCodes.ULC_COMP.value: 'ADVD2',
                ColinApiTypeCodes.CCC_COMP.value: 'ADVD2',
                ColinApiTypeCodes.BCOMP_CONTINUE_IN.value: 'ADVD2',
                ColinApiTypeCodes.CONTINUE_IN.value: 'ADVD2',
                ColinApiTypeCodes.ULC_CONTINUE_IN.value: 'ADVD2',
                ColinApiTypeCodes.CCC_CONTINUE_IN.value: 'ADVD2',
            }
        },
        'consentContinuationOut': {
            'type_code_list': ['CONTO'],
            ColinApiTypeCodes.BCOMP.value: 'CONTO',
            ColinApiTypeCodes.BC_COMP.value: 'CONTO',
            ColinApiTypeCodes.ULC_COMP.value: 'CONTO',
            ColinApiTypeCodes.CCC_COMP.value: 'CONTO',
            ColinApiTypeCodes.BCOMP_CONTINUE_IN.value: 'CONTO',
            ColinApiTypeCodes.CONTINUE_IN.value: 'CONTO',
            ColinApiTypeCodes.ULC_CONTINUE_IN.value: 'CONTO',
            ColinApiTypeCodes.CCC_CONTINUE_IN.value: 'CONTO',
        },
        'continuationOut': {
            'type_code_list': ['COUTI'],
            ColinApiTypeCodes.BCOMP.value: 'COUTI',
            ColinApiTypeCodes.BC_COMP.value: 'COUTI',
            ColinApiTypeCodes.ULC_COMP.value: 'COUTI',
            ColinApiTypeCodes.CCC_COMP.value: 'COUTI',
            ColinApiTypeCodes.BCOMP_CONTINUE_IN.value: 'COUTI',
            ColinApiTypeCodes.CONTINUE_IN.value: 'COUTI',
            ColinApiTypeCodes.ULC_CONTINUE_IN.value: 'COUTI',
            ColinApiTypeCodes.CCC_CONTINUE_IN.value: 'COUTI',
        },
        'changeOfName': {
            'type_code_list': ['OTNCN'],
            ColinApiTypeCodes.COOP.value: 'OTNCN',
        },
        'restoration': {
            'sub_type_property': 'type',
            'sub_type_list': ['fullRestoration',
                              'limitedRestoration',
                              'limitedRestorationExtension',
                              'limitedRestorationToFull'],
            'type_code_list': ['RESTF', 'RESTL', 'RESXL', 'RESXF'],
            'fullRestoration': {
                ColinApiTypeCodes.BCOMP.value: 'RESTF',
                ColinApiTypeCodes.BC_COMP.value: 'RESTF',
                ColinApiTypeCodes.ULC_COMP.value: 'RESTF',
                ColinApiTypeCodes.CCC_COMP.value: 'RESTF',
                ColinApiTypeCodes.BCOMP_CONTINUE_IN.value: 'RESTF',
                ColinApiTypeCodes.CONTINUE_IN.value: 'RESTF',
                ColinApiTypeCodes.ULC_CONTINUE_IN.value: 'RESTF',
                ColinApiTypeCodes.CCC_CONTINUE_IN.value: 'RESTF',
            },
            'limitedRestoration': {
                ColinApiTypeCodes.BCOMP.value: 'RESTL',
                ColinApiTypeCodes.BC_COMP.value: 'RESTL',
                ColinApiTypeCodes.ULC_COMP.value: 'RESTL',
                ColinApiTypeCodes.CCC_COMP.value: 'RESTL',
                ColinApiTypeCodes.BCOMP_CONTINUE_IN.value: 'RESTL',
                ColinApiTypeCodes.CONTINUE_IN.value: 'RESTL',
                ColinApiTypeCodes.ULC_CONTINUE_IN.value: 'RESTL',
                ColinApiTypeCodes.CCC_CONTINUE_IN.value: 'RESTL',
            },
            'limitedRestorationExtension': {
                ColinApiTypeCodes.BCOMP.value: 'RESXL',
                ColinApiTypeCodes.BC_COMP.value: 'RESXL',
                ColinApiTypeCodes.ULC_COMP.value: 'RESXL',
                ColinApiTypeCodes.CCC_COMP.value: 'RESXL',
                ColinApiTypeCodes.BCOMP_CONTINUE_IN.value: 'RESXL',
                ColinApiTypeCodes.CONTINUE_IN.value: 'RESXL',
                ColinApiTypeCodes.ULC_CONTINUE_IN.value: 'RESXL',
                ColinApiTypeCodes.CCC_CONTINUE_IN.value: 'RESXL',
            },
            'limitedRestorationToFull': {
                ColinApiTypeCodes.BCOMP.value: 'RESXF',
                ColinApiTypeCodes.BC_COMP.value: 'RESXF',
                ColinApiTypeCodes.ULC_COMP.value: 'RESXF',
                ColinApiTypeCodes.CCC_COMP.value: 'RESXF',
                ColinApiTypeCodes.BCOMP_CONTINUE_IN.value: 'RESXF',
                ColinApiTypeCodes.CONTINUE_IN.value: 'RESXF',
                ColinApiTypeCodes.ULC_CONTINUE_IN.value: 'RESXF',
                ColinApiTypeCodes.CCC_CONTINUE_IN.value: 'RESXF',
            }
        },
        'restorationApplication': {
            'type_code_list': ['OTRES'],
            ColinApiTypeCodes.COOP.value: 'OTRES',
        },
        'amendedAnnualReport': {
            'type_code_list': ['OTAMR'],
            ColinApiTypeCodes.COOP.value: 'OTAMR',
        },
        'amendedChangeOfDirectors': {
            'type_code_list': ['OTADR'],
            ColinApiTypeCodes.COOP.value: 'OTADR',
        },
        'voluntaryLiquidation': {
            'type_code_list': ['OTVLQ'],
            ColinApiTypeCodes.COOP.value: 'OTVLQ',
        },
        'appointReceiver': {
            'type_code_list': ['OTNRC'],
            ColinApiTypeCodes.COOP.value: 'OTNRC',
        },
        'continuedOut': {
            'type_code_list': ['OTCON'],
            ColinApiTypeCodes.COOP.value: 'OTCON'
        },
        'transition': {
            'type_code_list': ['TRANS'],
            ColinApiTypeCodes.BC_COMP.value: 'TRANS'
        },
        'registrarsNotation': {
            'type_code_list': ['REGSN'],
            ColinApiTypeCodes.BC_COMP.value: 'REGSN'
        },
        'registrarsOrder': {
            'type_code_list': ['REGSO'],
            ColinApiTypeCodes.BC_COMP.value: 'REGSO'
        },
        'courtOrder': {
            'type_code_list': ['COURT'],
            ColinApiTypeCodes.BC_COMP.value: 'COURT'
        },
        'putBackOn': {
            'type_code_list': ['CO_PO'],
            ColinApiTypeCodes.COOP.value: 'CO_PO',
            ColinApiTypeCodes.BCOMP.value: 'CO_PO',
            ColinApiTypeCodes.BC_COMP.value: 'CO_PO',
            ColinApiTypeCodes.ULC_COMP.value: 'CO_PO',
            ColinApiTypeCodes.CCC_COMP.value: 'CO_PO',
            ColinApiTypeCodes.BCOMP_CONTINUE_IN.value: 'CO_PO',
            ColinApiTypeCodes.CONTINUE_IN.value: 'CO_PO',
            ColinApiTypeCodes.ULC_CONTINUE_IN.value: 'CO_PO',
            ColinApiTypeCodes.CCC_CONTINUE_IN.value: 'CO_PO',
        },
        'putBackOff': {
            'type_code_list': ['CO_PF'],
            ColinApiTypeCodes.COOP.value: 'CO_PF',
            ColinApiTypeCodes.BCOMP.value: 'CO_PF',
            ColinApiTypeCodes.BC_COMP.value: 'CO_PF',
            ColinApiTypeCodes.ULC_COMP.value: 'CO_PF',
            ColinApiTypeCodes.CCC_COMP.value: 'CO_PF',
            ColinApiTypeCodes.BCOMP_CONTINUE_IN.value: 'CO_PF',
            ColinApiTypeCodes.CONTINUE_IN.value: 'CO_PF',
            ColinApiTypeCodes.ULC_CONTINUE_IN.value: 'CO_PF',
            ColinApiTypeCodes.CCC_CONTINUE_IN.value: 'CO_PF',
        }
    }
