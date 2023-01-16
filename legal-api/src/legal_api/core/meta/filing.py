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
from legal_api.services import VersionedBusinessDetailsService as VersionService  # noqa: I005


class AutoName(str, Enum):
    """Replace autoname from Enum class."""

    # pragma warning disable S5720; # noqa: E265
    # disable sonar cloud complaining about this signature
    def _generate_next_value_(name, start, count, last_values):  # pylint: disable=W0221,E0213 # noqa: N805
        """Return the name of the key, but in lowercase."""
        names = name.split('_')
        return ''.join([x.lower() if i == 0 else x.capitalize() for i, x in enumerate(names)])
    # pragma warning enable S5720; # noqa: E265


class ReportTitles(str, Enum):
    """Enum of the report titles."""

    ALTERATION_NOTICE = 'Alteration Notice'
    CERTIFICATE = 'Certificate'
    CERTIFICATE_OF_NAME_CHANGE = 'Certificate Of Name Change'
    CERTIFIED_MEMORANDUM = 'Certified Memorandum'
    CERTIFIED_RULES = 'Certified Rules'
    NOTICE_OF_ARTICLES = 'Notice of Articles'
    AMENDED_REGISTRATION_STATEMENT = 'Amended Registration Statement'
    CORRECTED_REGISTRATION_STATEMENT = 'Corrected Registration Statement'


class ReportNames(AutoName):
    """Enum of the report names."""

    ALTERATION_NOTICE = auto()
    CERTIFICATE = auto()
    CERTIFICATE_OF_NAME_CHANGE = auto()
    CERTIFIED_MEMORANDUM = auto()
    CERTIFIED_RULES = auto()
    NOTICE_OF_ARTICLES = auto()
    AMENDED_REGISTRATION_STATEMENT = auto()


class FilingTitles(str, Enum):
    """Enum of the filing titles."""

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
            'BEN': 'ALTER',
            'ULC': 'ALTER',
            'CC': 'ALTER'
        },
        'additional': [
            {'types': 'BC,BEN,BC,CC,ULC', 'outputs': ['noticeOfArticles', ]},
        ]
    },
    'annualReport': {
        'name': 'annualReport',
        'title': 'Annual Report Filing',
        'displayName': 'Annual Report',
        'codes': {
            'CP': 'OTANN',
            'BEN': 'BCANN',
            'BC': 'BCANN',
            'ULC': 'BCANN',
            'CC': 'BCANN'
        }
    },
    'changeOfAddress': {
        'name': 'changeOfAddress',
        'title': 'Change of Address Filing',
        'displayName': 'Address Change',
        'codes': {
            'CP': 'OTADD',
            'BEN': 'BCADD',
            'BC': 'BCADD',
            'ULC': 'BCADD',
            'CC': 'BCADD'
        },
        'additional': [
            {'types': 'BEN,BC,CC,ULC', 'outputs': ['noticeOfArticles', ]},
        ]
    },
    'changeOfDirectors': {
        'name': 'changeOfDirectors',
        'title': 'Change of Directors Filing',
        'displayName': 'Director Change',
        'codes': {
            'CP': 'OTCDR',
            'BEN': 'BCCDR',
            'BC': 'BCCDR',
            'ULC': 'BCCDR',
            'CC': 'BCCDR'
        },
        'free': {
            'codes': {
                'CP': 'OTFDR',
                'BEN': 'BCFDR',
                'BC': 'BCFDR',
                'ULC': 'BCFDR',
                'CC': 'BCFDR'
            }
        },
        'additional': [
            {'types': 'BEN,BC,CC,ULC', 'outputs': ['noticeOfArticles', ]},
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
        'displayName': {
            'BEN': 'Conversion',
            'SP': 'Record Conversion',
            'GP': 'Record Conversion',
        },
        'codes': {
            'SP': 'FMCONV',
            'GP': 'FMCONV'
        }
    },
    'correction': {
        'name': 'correction',
        'title': 'Correction',
        'displayName': 'Register Correction Application',
        'codes': {
            'BEN': 'CRCTN',
            'BC': 'CRCTN',
            'ULC': 'CRCTN',
            'CC': 'CRCTN',
            'CP': 'CRCTN',
            'SP': 'FMCORR',
            'GP': 'FMCORR'
        },
        'additional': [
            {'types': 'BEN,BC,CC,ULC', 'outputs': ['noticeOfArticles', ]},
            {'types': 'SP,GP', 'outputs': ['correctedRegistrationStatement', ]},
        ]
    },
    'courtOrder': {
        'name': 'courtOrder',
        'title': 'Court Order',
        'displayName': 'Court Order',
        'code': 'NOFEE'
    },
    'dissolution': {
        'name': 'dissolution',
        'title': 'Voluntary Dissolution',
        'displayName': {
            'CP': 'Voluntary Dissolution',
            'BC': 'Voluntary Dissolution',
            'BEN': 'Voluntary Dissolution',
            'ULC': 'Voluntary Dissolution',
            'CC': 'Voluntary Dissolution',
            'LLC': 'Voluntary Dissolution',
            'SP': 'Statement of Dissolution',
            'GP': 'Statement of Dissolution'
        },
        'codes': {
            'CP': 'DIS_VOL',
            'BC': 'DIS_VOL',
            'BEN': 'DIS_VOL',
            'ULC': 'DIS_VOL',
            'CC': 'DIS_VOL',
            'LLC': 'DIS_VOL',
            'SP': 'DIS_VOL',
            'GP': 'DIS_VOL'
        },
        'additional': [
            {'types': 'CP', 'outputs': ['certificateOfDissolution', 'affidavit']},
            {'types': 'BC,BEN,CC,ULC,LLC', 'outputs': ['certificateOfDissolution']},
        ]
    },
    'incorporationApplication': {
        'name': 'incorporationApplication',
        'title': 'Incorporation Application',
        'displayName': {
            'BC': 'BC Limited Company Incorporation Application',
            'ULC': 'BC Unlimited Liability Company Incorporation Application',
            'CC': 'BC Community Contribution Company Incorporation Application',
            'BEN': 'BC Benefit Company Incorporation Application',
            'CP': 'Incorporation Application',
        },
        'codes': {
            'BEN': 'BCINC',
            'BC': 'BCINC',
            'ULC': 'BCINC',
            'CC': 'BCINC',
            'CP': 'OTINC'
        },
        'additional': [
            {'types': 'CP', 'outputs': ['certificate', 'certifiedRules', 'certifiedMemorandum']},
            {'types': 'BC,BEN,ULC,CC', 'outputs': ['noticeOfArticles', 'certificate']},
        ]
    },
    'registrarsNotation': {
        'name': 'registrarsNotation',
        'title': 'Registrars Notation',
        'displayName': "Registrar's Notation",
        'code': 'NOFEE'
    },
    'registrarsOrder': {
        'name': 'registrarsOrder',
        'title': 'Registrars Order',
        'displayName': "Registrar's Order",
        'code': 'NOFEE'
    },
    'registration': {
        'name': 'registration',
        'title': 'Registration',
        'displayName': {
            'SP': 'BC Sole Proprietorship Registration',
            'GP': 'BC General Partnership Registration'
        },
        'codes': {
            'SP': 'FRREG',
            'GP': 'FRREG'
        },
    },
    'specialResolution': {
        'name': 'specialResolution',
        'title': 'Special Resolution',
        'displayName': 'Special Resolution',
        'codes': {
            'CP': 'SPRLN'
        }
    },
    'transition': {
        'name': 'transition',
        'title': 'Transition',
        'displayName': 'Transition Application',
        'codes': {
            'BC': 'TRANS',
            'BEN': 'TRANS',
            'ULC': 'TRANS',
            'CC': 'TRANS'
        },
        'additional': [
            {'types': 'BC,BEN', 'outputs': ['noticeOfArticles', ]},
        ]
    },
    'changeOfRegistration': {
        'name': 'changeOfRegistration',
        'title': 'Change of Registration',
        'displayName': {
            'SP': 'Change of Registration Application',
            'GP': 'Change of Registration Application'
        },
        'codes': {
            'SP': 'FMCHANGE',
            'GP': 'FMCHANGE'
        },
        'additional': [
            {'types': 'SP,GP', 'outputs': ['amendedRegistrationStatement', ]},
        ]
    },
    'putBackOn': {
        'name': 'putBackOn',
        'title': 'Put Back On',
        'displayName': 'Correction - Put Back On',
        'code': 'NOFEE'
    },
    'adminFreeze': {
        'name': 'adminFreeze',
        'title': 'Admin Freeze',
        'displayName': 'Admin Freeze',
        'code': 'NOFEE'
    }
}


class FilingMeta:  # pylint: disable=too-few-public-methods
    """Create all the information about a filing."""

    @staticmethod
    def display_name(business: Business, filing: FilingStorage) -> Optional[str]:
        """Return the name of the filing to display on outputs."""
        # if there is no lookup
        if not (names := FILINGS.get(filing.filing_type, {}).get('displayName')):
            return ' '.join(word.capitalize()
                            for word in
                            re.sub(r'([A-Z])', r':\1', filing.filing_type).split(':'))

        business_revision = business
        # retrieve business revision at time of filing so legal type is correct when returned for display name
        if filing.transaction_id and \
                (bus_rev_temp := VersionService.get_business_revision_obj(filing.transaction_id, business)):
            business_revision = bus_rev_temp

        if isinstance(names, MutableMapping):
            name = names.get(business_revision.legal_type)
        else:
            name = names

        if filing.filing_type in ('annualReport') and (year := FilingMeta.get_effective_display_year(filing.meta_data)):
            name = f'{name} ({year})'

        elif filing.filing_type in ('correction') and filing.meta_data:
            with suppress(Exception):
                # Depending on filing_json to get corrected filing until changing the parent_filing logic.
                # Now staff can correct a filing multiple time and parent_filing in the original filing will be
                # overriden with the latest correction, which cause loosing the previous correction link.
                corrected_filing_type = filing.filing_json['filing']['correction']['correctedFilingType']
                corrected_filing_id = filing.filing_json['filing']['correction']['correctedFilingId']
                if corrected_filing_type in ['annualReport', 'changeOfAddress', 'changeOfDirectors']:
                    corrected_filing = FilingStorage.find_by_id(corrected_filing_id)
                    name = f'Correction - {FilingMeta.display_name(business_revision, corrected_filing)}'

        elif filing.filing_type in ('dissolution') and filing.meta_data:
            if filing.meta_data['dissolution'].get('dissolutionType') == 'administrative':
                name = 'Administrative Dissolution'

        elif filing.filing_type in ('adminFreeze') and filing.meta_data:
            if filing.meta_data['adminFreeze'].get('freeze') is False:
                name = 'Admin Unfreeze'

        return name

    @staticmethod
    def get_effective_display_year(filing_meta_data: dict) -> Optional[str]:
        """Render a year as a string, given all filing mechanisms."""
        with suppress(IndexError, KeyError, TypeError):
            return str(filing_meta_data['annualReport']['annualReportFilingYear'])
        return None

    @staticmethod
    def get_all_outputs(business_type: str, filing_name: str) -> list:
        """Return list of all outputs."""
        filing = FILINGS.get(filing_name)
        for docs in filing.get('additional', []):
            if business_type in docs.get('types'):
                return docs.get('outputs')
        return []

    @staticmethod
    def alter_outputs(filing: FilingStorage, outputs: set):
        """Add or remove outputs conditionally."""
        if filing.filing_type == 'alteration':
            if filing.meta_data.get('alteration', {}).get('toLegalName'):
                outputs.add('certificateOfNameChange')
        elif filing.filing_type == 'specialResolution' and 'changeOfName' in filing.meta_data.get('legalFilings', []):
            outputs.add('certificateOfNameChange')
