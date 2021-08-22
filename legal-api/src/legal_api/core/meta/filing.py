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
from contextlib import suppress
from typing import Final, Optional

from legal_api.models import Filing as FilingStorage
from legal_api.utils.datetime import date


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
    'conversion': {
        'name': 'conversion',
        'title': 'Conversion Ledger',
        'displayName': 'Conversion'
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
    'courtOrder': {
        'name': 'courtOrder',
        'title': 'Court Order',
        'displayName': 'Court Order',
        'code': 'NOFEE'},
    'dissolution': {
        'name': 'dissolution',
        'title': 'Dissolution',
        'displayName': 'Dissolution',
        'code': 'NOT_IMPLEMENTED_YET'},
    'incorporationApplication': {
        'name': 'incorporationApplication',
        'title': 'Incorporation Application',
        'displayName': 'Incorporation Application',
        'codes': {
            'BEN': 'BCINC'
        }
    },
    # changing the structure of fee code in courtOrder/registrarsNotation/registrarsOrder
    # for all the business the fee code remain same as NOFEE (Staff)
    'registrarsNotation': {
        'name': 'registrarsNotation',
        'title': 'Registrars Notation',
        'displayName': "Registrar's Notation",
        'code': 'NOFEE'},
    'registrarsOrder': {
        'name': 'registrarsOrder',
        'title': 'Registrars Order',
        'displayName': "Registrar's Order",
        'code': 'NOFEE'},
    'specialResolution': {
        'name': 'specialResolution',
        'title': 'Special Resolution',
        'displayName': 'Special Resolution',
        'codes': {
            'CP': 'RES'}},
    'transition': {
        'name': 'transition',
        'title': 'Transition',
        'displayName': 'Transition Application',
        'codes': {
            'BC': 'TRANS',
            'BEN': 'TRANS'
        }
    },
    'voluntaryDissolution': {
        'name': 'voluntaryDissolution',
        'title': 'Voluntary Dissolution',
        'displayName': 'Voluntary Dissolution'
        }
}


class FilingMeta:  # pylint: disable=too-few-public-methods
    """Create all the information about a filing."""

    @staticmethod
    def display_name(filing: FilingStorage, full_name: bool = True) -> Optional[str]:
        """Return the name of the filing to display on outputs."""
        name = FILINGS.get(filing.filing_type, {}).get('displayName', filing.filing_type)

        if filing.filing_type in ('annualReport') and (year := FilingMeta.get_effective_display_year(filing.meta_data)):
            name = f'{name} ({year})'

        if filing.filing_type in ('correction') and filing.meta_data:
            with suppress(Exception):
                name = f'{name} - {FilingMeta.display_name(filing.children[0], False)}'

        if full_name and filing.parent_filing_id and filing.status == FilingStorage.Status.CORRECTED:
            name = f'{name} - Corrected'
        return name

    @staticmethod
    def get_effective_display_year(filing_meta_data: dict) -> Optional[str]:
        """Render a year as a string, given all filing mechanisms."""
        with suppress(IndexError, KeyError, TypeError):
            application_date = filing_meta_data['applicationDate']
            return str(date.fromisoformat(application_date).year)
        return None
