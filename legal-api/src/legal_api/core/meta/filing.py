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
# limitations under the License.
"""Meta Filing support for the core domain used by the application."""
from typing import Final, Optional


FILINGS: Final = {
    'alteration': {
        'name': 'alteration',
        'title': 'Notice of Alteration Filing',
        'displayName': 'Alteration',
        'codes': {
            'BC': 'ALTER',
            'BEN': 'ALTER'
        }
    },
    'annualReport': {
        'name': 'annualReport',
        'title': 'Annual Report Filing',
        'displayName': 'Annual Report',
        'codes': {
            'CP': 'OTANN',
            'BEN': 'BCANN'
        }
    },
    'changeOfAddress': {
        'name': 'changeOfAddress',
        'title': 'Change of Address Filing',
        'displayName': 'Address Change',
        'codes': {
            'CP': 'OTADD',
            'BEN': 'BCADD'
        }
    },
    'changeOfDirectors': {
        'name': 'changeOfDirectors',
        'title': 'Change of Directors Filing',
        'displayName': 'Director Change',
        'codes': {
            'CP': 'OTCDR',
            'BEN': 'BCCDR'
        },
        'free': {
            'codes': {
                'CP': 'OTFDR',
                'BEN': 'BCFDR'
            }
        }
    },
    'changeOfName': {
        'name': 'changeOfName',
        'title': 'Change of Name Filing',
        'displayName': 'Legal Name Change'
    },
    'correction': {
        'name': 'correction',
        'title': 'Correction',
        'displayName': 'Correction',
        'codes': {
            'BEN': 'CRCTN',
            'CP': 'CRCTN'
        }
    },
    'incorporationApplication': {
        'name': 'incorporationApplication',
        'title': 'Incorporation Application',
        'displayName': 'Incorporation Application',
        'codes': {
            'BEN': 'BCINC'
        }
    },
    'conversion': {
        'name': 'conversion',
        'title': 'Conversion Ledger',
        'displayName': 'Conversion'
    },
    'specialResolution': {
        'name': 'specialResolution',
        'title': 'Special Resolution',
        'displayName': 'Special Resolution',
        'codes': {
            'CP': 'RES'}},
    'voluntaryDissolution': {
        'name': 'voluntaryDissolution',
        'title': 'Voluntary Dissolution',
        'displayName': 'Voluntary Dissolution'
        },
    'transition': {
        'name': 'transition',
        'title': 'Transition',
        'displayName': 'Transition Application',
        'codes': {
            'BC': 'TRANS',
            'BEN': 'TRANS'
        }
    },
    # changing the structure of fee code in courtOrder/registrarsNotation/registrarsOrder
    # for all the business the fee code remain same as NOFEE (Staff)
    'courtOrder': {
        'name': 'courtOrder',
        'title': 'Court Order',
        'displayName': 'Court Order',
        'code': 'NOFEE'},
    'registrarsNotation': {
        'name': 'registrarsNotation',
        'title': 'Registrars Notation',
        'displayName': "Registrar's Notation",
        'code': 'NOFEE'},
    'registrarsOrder': {
        'name': 'registrarsOrder',
        'title': 'Registrars Order',
        'displayName': "Registrar's Order",
        'code': 'NOFEE'}
}


class FilingMeta:  # pylint: disable=too-few-public-methods
    """Create all the information about a filing."""

    @staticmethod
    def display_name(filing_name: str = None) -> Optional[str]:
        """Return the name of the filing to display on outputs."""
        return FILINGS.get(filing_name, {}).get('displayName')
