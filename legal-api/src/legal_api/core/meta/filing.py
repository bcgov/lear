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
import re
from contextlib import suppress
from enum import Enum, auto
from typing import Final, MutableMapping, Optional

from legal_api.models import Business
from legal_api.models import Filing as FilingStorage
from legal_api.services.namex import NameXService
from legal_api.utils.datetime import date


class AutoName(str, Enum):
    """Replace autoname from Enum class."""

    #pragma warning disable S5720; # noqa: E265
    # disable sonar cloud complaining about this signature
    def _generate_next_value_(name, start, count, last_values):  # pylint: disable=W0221,E0213 # noqa: N805
        """Return the name of the key, but in lowercase."""
        names = name.split('_')
        return ''.join([x.lower() if i == 0 else x.capitalize() for i, x in enumerate(names)])
    #pragma warning enable S5720; # noqa: E265


class ReportTitles(str, Enum):
    """Enum of the system error codes."""

    ALTERATION_NOTICE = 'Alteration Notice'
    CERTIFICATE = 'Certificate'
    CERTIFICATE_OF_NAME_CHANGE = 'Certificate Of Name Change'
    CERTIFIED_MEMORANDUM = 'Certified Memorandum'
    CERTIFIED_RULES = 'Certified Rules'
    NOTICE_OF_ARTICLES = 'Notice of Articles'


class ReportNames(AutoName):
    """Enum of the system error codes."""

    ALTERATION_NOTICE = auto()
    CERTIFICATE = auto()
    CERTIFICATE_OF_NAME_CHANGE = auto()
    CERTIFIED_MEMORANDUM = auto()
    CERTIFIED_RULES = auto()
    NOTICE_OF_ARTICLES = auto()


class FilingTitles(str, Enum):
    """Enum of the system error codes."""

    INCORPORATION_APPLICATION_DEFAULT = 'Incorporation Application'


FILINGS: Final = {
    'affidavit': {
        'name': 'affidavit',
        'title': 'Affidavit',
        'codes': {
            'CP': 'AFDVT'
        }
    },
    'alteration': {
        'name': 'alteration',
        'title': 'Notice of Alteration Filing',
        'displayName': 'Alteration',
        'codes': {
            'BC': 'ALTER',
            'BEN': 'ALTER'
        },
        'additional': [
            {'types': 'BC,BEN', 'outputs': ['noticeOfArticles', ]},
        ],
        'hasConditionalOutputs': True
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
        },
        'additional': [
            {'types': 'BEN', 'outputs': ['noticeOfArticles', ]},
        ]
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
        },
        'additional': [
            {'types': 'BEN', 'outputs': ['noticeOfArticles', ]},
        ]
    },
    'changeOfName': {
        'name': 'changeOfName',
        'title': 'Change of Name Filing',
        'displayName': 'Legal Name Change',
        'additional': [
            {'types': 'BEN', 'outputs': ['noticeOfArticles', ]},
        ]
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
        },
        'additional': [
            {'types': 'CP,BEN', 'outputs': ['noticeOfArticles', ]},
        ],
        'hasConditionalOutputs': True
    },
    'courtOrder': {
        'name': 'courtOrder',
        'title': 'Court Order',
        'displayName': 'Court Order',
        'code': 'NOFEE'},
    'dissolution': {
        'name': 'dissolution',
        'title': 'Voluntary dissolution',
        'displayName': 'Voluntary dissolution',
        'codes': {
            'CP': 'DIS_VOL',
            'BC': 'DIS_VOL',
            'BEN': 'DIS_VOL',
            'ULC': 'DIS_VOL',
            'CC': 'DIS_VOL',
            'LLC': 'DIS_VOL'
        }
    },
    'incorporationApplication': {
        'name': 'incorporationApplication',
        'title': FilingTitles.INCORPORATION_APPLICATION_DEFAULT,
        'displayName': {
            'BC': FilingTitles.INCORPORATION_APPLICATION_DEFAULT,
            'BEN': 'BC Benefit Company Incorporation Application',
            'CP': FilingTitles.INCORPORATION_APPLICATION_DEFAULT,
        },
        'codes': {
            'BEN': 'BCINC'
        },
        'additional': [
            {'types': 'CP', 'outputs': ['certificate']},
            {'types': 'BC,BEN', 'outputs': ['noticeOfArticles', 'certificate']},
        ]
    },
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
            'CP': 'SPRLN'}},
    'transition': {
        'name': 'transition',
        'title': 'Transition',
        'displayName': 'Transition Application',
        'codes': {
            'BC': 'TRANS',
            'BEN': 'TRANS'
        },
        'additional': [
            {'types': 'BC,BEN', 'outputs': ['noticeOfArticles', ]},
        ]
    },
}


class FilingMeta:  # pylint: disable=too-few-public-methods
    """Create all the information about a filing."""

    @staticmethod
    def display_name(business: Business, filing: FilingStorage, full_name: bool = True) -> Optional[str]:
        """Return the name of the filing to display on outputs."""
        # if there is no lookup
        if not (names := FILINGS.get(filing.filing_type, {}).get('displayName')):
            return ' '.join(word.capitalize()
                            for word in
                            re.sub(r'([A-Z])', r':\1', filing.filing_type).split(':'))

        if isinstance(names, MutableMapping):
            name = names.get(business.legal_type)
        else:
            name = names

        if filing.filing_type in ('annualReport') and (year := FilingMeta.get_effective_display_year(filing.meta_data)):
            name = f'{name} ({year})'

        elif filing.filing_type in ('correction') and filing.meta_data:
            with suppress(Exception):
                name = f'{name} - {FilingMeta.display_name(business, filing.children[0], False)}'

        if full_name and filing.parent_filing_id and filing.status == FilingStorage.Status.CORRECTED:
            name = f'{name} - Corrected'
        return name

    @staticmethod
    def get_effective_display_year(filing_meta_data: dict) -> Optional[str]:
        """Render a year as a string, given all filing mechanisms."""
        with suppress(IndexError, KeyError, TypeError):
            report_date = filing_meta_data['annualReport']['annualReportDate']
            return str(date.fromisoformat(report_date).year)
        return None

    def get_conditional_alteration_outputs(filing: FilingStorage):  # pylint: disable=no-self-argument
        """Return conditional alteration outputs."""
        reports = []

        name_request = filing.filing_json \
            .get('filing', {}) \
            .get('alteration', {}) \
            .get('nameRequest', None)  # pylint: disable=no-member
        business = filing.filing_json.get('filing', {}).get('business', {})  # pylint: disable=no-member
        if name_request and 'legalName' in name_request and \
                name_request['legalName'] != business.get('legalName', None):
            reports.append('certificateOfNameChange')

        return reports

    def get_conditional_correction_outputs(filing: FilingStorage):  # pylint: disable=no-self-argument
        """Return conditional correction outputs."""
        reports = []

        if NameXService.has_correction_changed_name(filing.filing_json):  # pylint: disable=no-member
            reports.append('certificate')

        return reports

    CONDITIONAL_OUTPUTS: Final = {
        'alteration': get_conditional_alteration_outputs,
        'correction': get_conditional_correction_outputs
    }

    @staticmethod
    def get_all_outputs(business_type: str, filing_name: str, storage: FilingStorage) -> list:
        """Return list of all outputs."""
        outputs = []
        filing = FILINGS.get(filing_name)
        for docs in filing.get('additional', []):
            if business_type in docs.get('types'):
                outputs.extend(docs.get('outputs'))

        if filing.get('hasConditionalOutputs', False):
            conditional_outputs = FilingMeta.CONDITIONAL_OUTPUTS[filing_name](storage)
            outputs.extend(conditional_outputs)

        return outputs
