# Copyright © 2019 Province of British Columbia
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
"""Meta information about the service.

Currently this only provides API versioning information
"""
# pylint: disable=too-many-lines
from __future__ import annotations

import datetime
from enum import Enum
from http import HTTPStatus
from typing import Dict, List, Optional

from flask import current_app
from registry_schemas.utils import get_schema

from colin_api.exceptions import (  # noqa: I001
    FilingNotFoundException,  # noqa: I001
    GenericException,  # noqa: I001
    InvalidFilingTypeException,  # noqa: I001
    OfficeNotFoundException,  # noqa: I001
    PartiesNotFoundException,  # noqa: I001
    UnableToDetermineCorpTypeException,  # noqa: I001
)  # noqa: I001
from colin_api.models import (  # noqa: I001
    Business,  # noqa: I001
    ContOut,  # noqa: I001
    CorpInvolved,  # noqa: I001
    CorpName,  # noqa: I001
    FilingType,  # noqa: I001
    Jurisdiction,  # noqa: I001
    Office,  # noqa: I001
    Party,  # noqa: I001
    ShareObject,  # noqa: I001
)  # noqa: I001
from colin_api.resources.db import DB
from colin_api.services import flags
from colin_api.utils import convert_to_json_date, convert_to_json_datetime, convert_to_pacific_time, convert_to_snake


# Code smells:
# Cognitive Complexity acceptable for deep method on filing types
class Filing:  # pylint: disable=too-many-instance-attributes;
    """Class to contain all model-like functions for filings such as getting and setting from database."""

    class LearSource(Enum):
        """Temp class until we import from lear containing lear source types."""

        COLIN = 'COLIN'
        LEAR = 'LEAR'

    class FilingSource(Enum):
        """Enum that holds the sources of a filing."""

        BAR = 'BAR'
        LEAR = 'LEAR'

    FILING_TYPES = {
        'agmExtension': {
            'type_code_list': ['AGMDT'],
            Business.TypeCodes.BCOMP.value: 'AGMDT',
            Business.TypeCodes.BC_COMP.value: 'AGMDT',
            Business.TypeCodes.ULC_COMP.value: 'AGMDT',
            Business.TypeCodes.CCC_COMP.value: 'AGMDT',
            Business.TypeCodes.BCOMP_CONTINUE_IN.value: 'AGMDT',
            Business.TypeCodes.CONTINUE_IN.value: 'AGMDT',
            Business.TypeCodes.ULC_CONTINUE_IN.value: 'AGMDT',
            Business.TypeCodes.CCC_CONTINUE_IN.value: 'AGMDT',
        },
        'agmLocationChange': {
            'type_code_list': ['AGMLC'],
            Business.TypeCodes.BCOMP.value: 'AGMLC',
            Business.TypeCodes.BC_COMP.value: 'AGMLC',
            Business.TypeCodes.ULC_COMP.value: 'AGMLC',
            Business.TypeCodes.CCC_COMP.value: 'AGMLC',
            Business.TypeCodes.BCOMP_CONTINUE_IN.value: 'AGMLC',
            Business.TypeCodes.CONTINUE_IN.value: 'AGMLC',
            Business.TypeCodes.ULC_CONTINUE_IN.value: 'AGMLC',
            Business.TypeCodes.CCC_CONTINUE_IN.value: 'AGMLC',
        },
        'annualReport': {
            'type_code_list': ['OTANN', 'ANNBC'],
            Business.TypeCodes.COOP.value: 'OTANN',
            Business.TypeCodes.BCOMP.value: 'ANNBC',
            Business.TypeCodes.BC_COMP.value: 'ANNBC',
            Business.TypeCodes.ULC_COMP.value: 'ANNBC',
            Business.TypeCodes.CCC_COMP.value: 'ANNBC',
            Business.TypeCodes.BCOMP_CONTINUE_IN.value: 'ANNBC',
            Business.TypeCodes.CONTINUE_IN.value: 'ANNBC',
            Business.TypeCodes.ULC_CONTINUE_IN.value: 'ANNBC',
            Business.TypeCodes.CCC_CONTINUE_IN.value: 'ANNBC',
        },
        'changeOfDirectors': {
            'type_code_list': ['OTCDR', 'NOCDR'],
            Business.TypeCodes.COOP.value: 'OTCDR',
            Business.TypeCodes.BCOMP.value: 'NOCDR',
            Business.TypeCodes.BC_COMP.value: 'NOCDR',
            Business.TypeCodes.ULC_COMP.value: 'NOCDR',
            Business.TypeCodes.CCC_COMP.value: 'NOCDR',
            Business.TypeCodes.BCOMP_CONTINUE_IN.value: 'NOCDR',
            Business.TypeCodes.CONTINUE_IN.value: 'NOCDR',
            Business.TypeCodes.ULC_CONTINUE_IN.value: 'NOCDR',
            Business.TypeCodes.CCC_CONTINUE_IN.value: 'NOCDR',
        },
        'changeOfAddress': {
            'type_code_list': ['OTADD', 'NOCAD'],
            Business.TypeCodes.COOP.value: 'OTADD',
            Business.TypeCodes.BCOMP.value: 'NOCAD',
            Business.TypeCodes.BC_COMP.value: 'NOCAD',
            Business.TypeCodes.ULC_COMP.value: 'NOCAD',
            Business.TypeCodes.CCC_COMP.value: 'NOCAD',
            Business.TypeCodes.BCOMP_CONTINUE_IN.value: 'NOCAD',
            Business.TypeCodes.CONTINUE_IN.value: 'NOCAD',
            Business.TypeCodes.ULC_CONTINUE_IN.value: 'NOCAD',
            Business.TypeCodes.CCC_CONTINUE_IN.value: 'NOCAD',
        },
        'incorporationApplication': {
            'type_code_list': ['OTINC', 'BEINC', 'ICORP', 'ICORU', 'ICORC'],
            Business.TypeCodes.COOP.value: 'OTINC',
            Business.TypeCodes.BCOMP.value: 'BEINC',
            Business.TypeCodes.BC_COMP.value: 'ICORP',
            Business.TypeCodes.ULC_COMP.value: 'ICORU',
            Business.TypeCodes.CCC_COMP.value: 'ICORC',
        },
        'continuationIn': {
            'type_code_list': ['CONTB', 'CONTI', 'CONTU', 'CONTC'],
            Business.TypeCodes.BCOMP_CONTINUE_IN.value: 'CONTB',
            Business.TypeCodes.CONTINUE_IN.value: 'CONTI',
            Business.TypeCodes.ULC_CONTINUE_IN.value: 'CONTU',
            Business.TypeCodes.CCC_CONTINUE_IN.value: 'CONTC',
        },
        'conversion': {
            'type_code_list': ['CONVL'],
            Business.TypeCodes.BC_COMP.value: 'CONVL',
            Business.TypeCodes.ULC_COMP.value: 'CONVL',
            Business.TypeCodes.CCC_COMP.value: 'CONVL'
        },
        'alteration': {
            'type_code_list': ['NOABE', 'NOALE', 'NOALR', 'NOALD', 'NOALA', 'NOALB', 'NOALU', 'NOALC'],
            Business.TypeCodes.BCOMP.value: 'NOABE',  # No corp type change
            Business.TypeCodes.BC_COMP.value: 'NOALA',  # No corp type change
            Business.TypeCodes.ULC_COMP.value: 'NOALA',  # No corp type change
            Business.TypeCodes.CCC_COMP.value: 'NOALA',  # No corp type change
            Business.TypeCodes.BCOMP_CONTINUE_IN.value: 'NOABE',  # No corp type change
            Business.TypeCodes.CONTINUE_IN.value: 'NOALA',  # No corp type change
            Business.TypeCodes.ULC_CONTINUE_IN.value: 'NOALA',  # No corp type change
            Business.TypeCodes.CCC_CONTINUE_IN.value: 'NOALA',  # No corp type change
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
            Business.TypeCodes.COOP.value: 'OTSPE',
        },
        'amalgamationApplication': {
            'sub_type_property': 'type',
            'sub_type_list': ['regular', 'horizontal', 'vertical'],
            'type_code_list': ['OTAMA',
                               'AMLRB', 'AMALR', 'AMLRU', 'AMLRC',
                               'AMLHB', 'AMALH', 'AMLHU', 'AMLHC',
                               'AMLVB', 'AMALV', 'AMLVU', 'AMLVC'],
            'regular': {
                Business.TypeCodes.COOP.value: 'OTAMA',
                Business.TypeCodes.BCOMP.value: 'AMLRB',
                Business.TypeCodes.BC_COMP.value: 'AMALR',
                Business.TypeCodes.ULC_COMP.value: 'AMLRU',
                Business.TypeCodes.CCC_COMP.value: 'AMLRC'
            },
            'horizontal': {
                Business.TypeCodes.COOP.value: 'OTAMA',
                Business.TypeCodes.BCOMP.value: 'AMLHB',
                Business.TypeCodes.BC_COMP.value: 'AMALH',
                Business.TypeCodes.ULC_COMP.value: 'AMLHU',
                Business.TypeCodes.CCC_COMP.value: 'AMLHC'
            },
            'vertical': {
                Business.TypeCodes.COOP.value: 'OTAMA',
                Business.TypeCodes.BCOMP.value: 'AMLVB',
                Business.TypeCodes.BC_COMP.value: 'AMALV',
                Business.TypeCodes.ULC_COMP.value: 'AMLVU',
                Business.TypeCodes.CCC_COMP.value: 'AMLVC'
            }
        },
        'dissolved': {
            'type_code_list': ['OTDIS'],
            Business.TypeCodes.COOP.value: 'OTDIS',
        },
        'amendedAGM': {
            'type_code_list': ['OTCGM'],
            Business.TypeCodes.COOP.value: 'OTCGM',
        },
        'voluntaryDissolution': {
            'type_code_list': ['OTVDS'],
            Business.TypeCodes.COOP.value: 'OTVDS'
        },
        # Note: this should take care of voluntary dissolution filings now but leaving above
        # `voluntaryDissolution filing type in place as unsure if it is being used in other places
        'dissolution': {
            'sub_type_property': 'dissolutionType',
            'sub_type_list': ['voluntary', 'administrative', 'involuntary'],
            'type_code_list': ['OTVDS', 'ADVD2'],
            'voluntary': {
                Business.TypeCodes.COOP.value: 'OTVDS',
                Business.TypeCodes.BCOMP.value: 'ADVD2',
                Business.TypeCodes.BC_COMP.value: 'ADVD2',
                Business.TypeCodes.ULC_COMP.value: 'ADVD2',
                Business.TypeCodes.CCC_COMP.value: 'ADVD2',
                Business.TypeCodes.BCOMP_CONTINUE_IN.value: 'ADVD2',
                Business.TypeCodes.CONTINUE_IN.value: 'ADVD2',
                Business.TypeCodes.ULC_CONTINUE_IN.value: 'ADVD2',
                Business.TypeCodes.CCC_CONTINUE_IN.value: 'ADVD2',
            }
        },
        'consentContinuationOut': {
            'type_code_list': ['CONTO'],
            Business.TypeCodes.BCOMP.value: 'CONTO',
            Business.TypeCodes.BC_COMP.value: 'CONTO',
            Business.TypeCodes.ULC_COMP.value: 'CONTO',
            Business.TypeCodes.CCC_COMP.value: 'CONTO',
            Business.TypeCodes.BCOMP_CONTINUE_IN.value: 'CONTO',
            Business.TypeCodes.CONTINUE_IN.value: 'CONTO',
            Business.TypeCodes.ULC_CONTINUE_IN.value: 'CONTO',
            Business.TypeCodes.CCC_CONTINUE_IN.value: 'CONTO',
        },
        'continuationOut': {
            'type_code_list': ['COUTI'],
            Business.TypeCodes.BCOMP.value: 'COUTI',
            Business.TypeCodes.BC_COMP.value: 'COUTI',
            Business.TypeCodes.ULC_COMP.value: 'COUTI',
            Business.TypeCodes.CCC_COMP.value: 'COUTI',
            Business.TypeCodes.BCOMP_CONTINUE_IN.value: 'COUTI',
            Business.TypeCodes.CONTINUE_IN.value: 'COUTI',
            Business.TypeCodes.ULC_CONTINUE_IN.value: 'COUTI',
            Business.TypeCodes.CCC_CONTINUE_IN.value: 'COUTI',
        },
        'changeOfName': {
            'type_code_list': ['OTNCN'],
            Business.TypeCodes.COOP.value: 'OTNCN',
        },
        'restoration': {
            'sub_type_property': 'type',
            'sub_type_list': ['fullRestoration',
                              'limitedRestoration',
                              'limitedRestorationExtension',
                              'limitedRestorationToFull'],
            'type_code_list': ['RESTF', 'RESTL', 'RESXL', 'RESXF'],
            'fullRestoration': {
                Business.TypeCodes.BCOMP.value: 'RESTF',
                Business.TypeCodes.BC_COMP.value: 'RESTF',
                Business.TypeCodes.ULC_COMP.value: 'RESTF',
                Business.TypeCodes.CCC_COMP.value: 'RESTF',
                Business.TypeCodes.BCOMP_CONTINUE_IN.value: 'RESTF',
                Business.TypeCodes.CONTINUE_IN.value: 'RESTF',
                Business.TypeCodes.ULC_CONTINUE_IN.value: 'RESTF',
                Business.TypeCodes.CCC_CONTINUE_IN.value: 'RESTF',
            },
            'limitedRestoration': {
                Business.TypeCodes.BCOMP.value: 'RESTL',
                Business.TypeCodes.BC_COMP.value: 'RESTL',
                Business.TypeCodes.ULC_COMP.value: 'RESTL',
                Business.TypeCodes.CCC_COMP.value: 'RESTL',
                Business.TypeCodes.BCOMP_CONTINUE_IN.value: 'RESTL',
                Business.TypeCodes.CONTINUE_IN.value: 'RESTL',
                Business.TypeCodes.ULC_CONTINUE_IN.value: 'RESTL',
                Business.TypeCodes.CCC_CONTINUE_IN.value: 'RESTL',
            },
            'limitedRestorationExtension': {
                Business.TypeCodes.BCOMP.value: 'RESXL',
                Business.TypeCodes.BC_COMP.value: 'RESXL',
                Business.TypeCodes.ULC_COMP.value: 'RESXL',
                Business.TypeCodes.CCC_COMP.value: 'RESXL',
                Business.TypeCodes.BCOMP_CONTINUE_IN.value: 'RESXL',
                Business.TypeCodes.CONTINUE_IN.value: 'RESXL',
                Business.TypeCodes.ULC_CONTINUE_IN.value: 'RESXL',
                Business.TypeCodes.CCC_CONTINUE_IN.value: 'RESXL',
            },
            'limitedRestorationToFull': {
                Business.TypeCodes.BCOMP.value: 'RESXF',
                Business.TypeCodes.BC_COMP.value: 'RESXF',
                Business.TypeCodes.ULC_COMP.value: 'RESXF',
                Business.TypeCodes.CCC_COMP.value: 'RESXF',
                Business.TypeCodes.BCOMP_CONTINUE_IN.value: 'RESXF',
                Business.TypeCodes.CONTINUE_IN.value: 'RESXF',
                Business.TypeCodes.ULC_CONTINUE_IN.value: 'RESXF',
                Business.TypeCodes.CCC_CONTINUE_IN.value: 'RESXF',
            }
        },
        'restorationApplication': {
            'type_code_list': ['OTRES'],
            Business.TypeCodes.COOP.value: 'OTRES',
        },
        'amendedAnnualReport': {
            'type_code_list': ['OTAMR'],
            Business.TypeCodes.COOP.value: 'OTAMR',
        },
        'amendedChangeOfDirectors': {
            'type_code_list': ['OTADR'],
            Business.TypeCodes.COOP.value: 'OTADR',
        },
        'voluntaryLiquidation': {
            'type_code_list': ['OTVLQ'],
            Business.TypeCodes.COOP.value: 'OTVLQ',
        },
        'appointReceiver': {
            'type_code_list': ['OTNRC'],
            Business.TypeCodes.COOP.value: 'OTNRC',
        },
        'continuedOut': {
            'type_code_list': ['OTCON'],
            Business.TypeCodes.COOP.value: 'OTCON'
        },
        'transition': {
            'type_code_list': ['TRANS'],
            Business.TypeCodes.BC_COMP.value: 'TRANS'
        },
        'registrarsNotation': {
            'type_code_list': ['REGSN'],
            Business.TypeCodes.BC_COMP.value: 'REGSN'
        },
        'registrarsOrder': {
            'type_code_list': ['REGSO'],
            Business.TypeCodes.BC_COMP.value: 'REGSO'
        },
        'courtOrder': {
            'type_code_list': ['COURT'],
            Business.TypeCodes.BC_COMP.value: 'COURT'
        },
        'putBackOn': {
            'type_code_list': ['CO_PO'],
            Business.TypeCodes.COOP.value: 'CO_PO',
            Business.TypeCodes.BCOMP.value: 'CO_PO',
            Business.TypeCodes.BC_COMP.value: 'CO_PO',
            Business.TypeCodes.ULC_COMP.value: 'CO_PO',
            Business.TypeCodes.CCC_COMP.value: 'CO_PO',
            Business.TypeCodes.BCOMP_CONTINUE_IN.value: 'CO_PO',
            Business.TypeCodes.CONTINUE_IN.value: 'CO_PO',
            Business.TypeCodes.ULC_CONTINUE_IN.value: 'CO_PO',
            Business.TypeCodes.CCC_CONTINUE_IN.value: 'CO_PO',
        },
        'putBackOff': {
            'type_code_list': ['CO_PF'],
            Business.TypeCodes.COOP.value: 'CO_PF',
            Business.TypeCodes.BCOMP.value: 'CO_PF',
            Business.TypeCodes.BC_COMP.value: 'CO_PF',
            Business.TypeCodes.ULC_COMP.value: 'CO_PF',
            Business.TypeCodes.CCC_COMP.value: 'CO_PF',
            Business.TypeCodes.BCOMP_CONTINUE_IN.value: 'CO_PF',
            Business.TypeCodes.CONTINUE_IN.value: 'CO_PF',
            Business.TypeCodes.ULC_CONTINUE_IN.value: 'CO_PF',
            Business.TypeCodes.CCC_CONTINUE_IN.value: 'CO_PF',
        },
        'consentAmalgamationOut': {
            'type_code_list': ['IAMGO'],
            Business.TypeCodes.BCOMP.value: 'IAMGO',
            Business.TypeCodes.BC_COMP.value: 'IAMGO',
            Business.TypeCodes.ULC_COMP.value: 'IAMGO',
            Business.TypeCodes.CCC_COMP.value: 'IAMGO',
            Business.TypeCodes.BCOMP_CONTINUE_IN.value: 'IAMGO',
            Business.TypeCodes.CONTINUE_IN.value: 'IAMGO',
            Business.TypeCodes.ULC_CONTINUE_IN.value: 'IAMGO',
            Business.TypeCodes.CCC_CONTINUE_IN.value: 'IAMGO',
        },
        'amalgamationOut': {
            'type_code_list': ['AMALO'],
            Business.TypeCodes.BCOMP.value: 'AMALO',
            Business.TypeCodes.BC_COMP.value: 'AMALO',
            Business.TypeCodes.ULC_COMP.value: 'AMALO',
            Business.TypeCodes.CCC_COMP.value: 'AMALO',
            Business.TypeCodes.BCOMP_CONTINUE_IN.value: 'AMALO',
            Business.TypeCodes.CONTINUE_IN.value: 'AMALO',
            Business.TypeCodes.ULC_CONTINUE_IN.value: 'AMALO',
            Business.TypeCodes.CCC_CONTINUE_IN.value: 'AMALO',
        }
    }

    FILING_TYPE_TO_CORP_TYPE_CONVERSION = {
        'ICORP': Business.TypeCodes.BC_COMP.value,
        'ICORU': Business.TypeCodes.ULC_COMP.value,
        'ICORC': Business.TypeCodes.CCC_COMP.value,
        'NOALB': Business.TypeCodes.BC_COMP.value,
        'NOALC': Business.TypeCodes.CCC_COMP.value,
        'NOALU': Business.TypeCodes.ULC_COMP.value,
        'NOALR': Business.TypeCodes.BC_COMP.value,
    }

    USERS = {
        Business.TypeCodes.COOP.value: 'COOPER',
        Business.TypeCodes.BCOMP.value: 'BCOMPS',
        Business.TypeCodes.BC_COMP.value: 'BCOMPS',
        Business.TypeCodes.ULC_COMP.value: 'BCOMPS',
        Business.TypeCodes.CCC_COMP.value: 'BCOMPS',
        Business.TypeCodes.BCOMP_CONTINUE_IN.value: 'BCOMPS',
        Business.TypeCodes.CONTINUE_IN.value: 'BCOMPS',
        Business.TypeCodes.ULC_CONTINUE_IN.value: 'BCOMPS',
        Business.TypeCodes.CCC_CONTINUE_IN.value: 'BCOMPS'
    }
    # dicts
    body = None
    header = None
    # classes
    business = None
    # singular values
    effective_date = None
    event_id = None
    filing_type = None
    filing_sub_type = None
    filing_date = None
    paper_only = None
    colin_only = None
    user_id = None

    def __init__(self):
        """Initialize with all values None."""

    def get_corp_name(self) -> str:
        """Get corporation name, aka legal name."""
        return self.business.corp_name

    def get_corp_num(self) -> str:
        """Get corporation num, aka identifier."""
        return self.business.corp_num

    def get_corp_type(self) -> str:
        """Get corporation type."""
        return self.business.corp_type

    def get_certified_by(self) -> str:
        """Get last name; currently is whole name."""
        return self.header['certifiedBy']

    def get_email(self) -> str:
        """Get email address."""
        if self.body.get('contactPoint'):
            return self.body['contactPoint']['email']
        return self.header.get('email', '')

    def get_filing_type_code(self) -> Optional[str]:
        """Get filing type code."""
        if self.filing_type == 'alteration':
            corp_type_change = self.business.corp_type
            if ((to_type := self.body.get('business', {}).get('legalType')) and
                    to_type != self.business.corp_type):
                corp_type_change = f'{self.business.corp_type}_TO_{to_type}'
            return Filing.FILING_TYPES.get(self.filing_type, {}).get(corp_type_change, None)

        if self.filing_sub_type:
            return (Filing.FILING_TYPES.get(self.filing_type, {})
                    .get(self.filing_sub_type, {})
                    .get(self.business.corp_type, None))

        return Filing.FILING_TYPES.get(self.filing_type, {}).get(self.business.corp_type, None)

    def as_dict(self) -> Dict:
        """Return dict of object that can be json serialized and fits schema requirements."""
        filing = {
            'filing': {
                'header': self.header,
                **self.business.as_dict()
            }
        }
        entered_filings = [x for x in self.body if x in Filing.FILING_TYPES]

        if entered_filings:  # filing object possibly storing multiple filings
            for key in entered_filings:
                filing['filing'].update({key: self.body[key]})
        else:  # filing object storing 1 filing
            filing['filing'].update({self.filing_type: self.body})

        return filing

    @classmethod
    def _get_corp_type_for_event(cls, cursor, corp_num: str, event_id: str) -> Optional[str]:
        """Get corp type at time of a specific filing event for a given corp_num."""
        corp_type_related_filing_types = cls.FILING_TYPE_TO_CORP_TYPE_CONVERSION.keys()
        matching_filing_type = \
            FilingType.get_most_recent_match_before_event(corp_num=corp_num,
                                                          event_id=event_id,
                                                          matching_filing_types=corp_type_related_filing_types,
                                                          cursor=cursor)

        if matching_corp_type := cls.FILING_TYPE_TO_CORP_TYPE_CONVERSION.get(matching_filing_type.filing_typ_cd):
            return matching_corp_type

        return None

    @classmethod
    def _get_event_id(cls, cursor, corp_num: str, filing_dt: str, event_type: str = 'FILE') -> str:
        """Get next event ID for filing.

        :param cursor: oracle cursor
        :return: (int) event ID
        """
        try:
            if corp_num[:2] == 'CP':
                cursor.execute("""select noncorp_event_seq.NEXTVAL from dual""")
                row = cursor.fetchone()
                event_id = row[0]
            else:
                cursor.execute("""
                    SELECT id_num
                    FROM system_id
                    WHERE id_typ_cd = 'EV'
                    FOR UPDATE
                """)

                event_id = cursor.fetchone()[0]

                if event_id:
                    cursor.execute("""
                        UPDATE system_id
                        SET id_num = :new_num
                        WHERE id_typ_cd = 'EV'
                    """, new_num=event_id + 1)
            cursor.execute(
                """
                INSERT INTO event (event_id, corp_num, event_typ_cd, event_timestmp, trigger_dts)
                VALUES (:event_id, :corp_num, :event_type,
                    TO_TIMESTAMP_TZ(:filing_dt,'YYYY-MM-DD"T"HH24:MI:SS.FFTZH:TZM'), NULL)
                """,
                event_id=event_id,
                corp_num=corp_num,
                filing_dt=filing_dt,
                event_type=event_type
            )
            cursor.execute(
                """
                INSERT INTO event_insert (event_id, corp_num, insert_date)
                VALUES (:event_id, :corp_num, sysdate)
                """,
                event_id=event_id,
                corp_num=corp_num
            )
        except Exception as err:
            current_app.logger.error('Error in filing: Failed to create new event.')
            raise err
        return event_id

    @classmethod
    def _get_events(cls, cursor, corp_num: str, filing_type_code: str) -> List:
        """Get all event ids of filings for given filing type for this corp."""
        try:
            if not cursor:
                cursor = DB.connection.cursor()
            cursor.execute(
                """
                select event.event_id, event.event_timestmp, filing.period_end_dt
                from event
                left join filing on event.event_id = filing.event_id
                where corp_num=:corp_num and filing_typ_cd=:filing_type
                """,
                filing_type=filing_type_code,
                corp_num=corp_num
            )

            events = cursor.fetchall()
            event_list = []
            for row in events:
                row = dict(zip([x[0].lower() for x in cursor.description], row))
                item = {'id': row['event_id'], 'date': row['event_timestmp']}

                # if filing type is an AR include the period_end_dt info
                if filing_type_code in cls.FILING_TYPES['annualReport']['type_code_list']:
                    item['annualReportDate'] = row['period_end_dt']

                event_list.append(item)

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            current_app.logger.error(f'error getting events for {corp_num}')
            raise err

        return event_list

    @classmethod
    def _get_filing_type(cls, filing_type_code: str) -> Optional[str]:
        for filing_type in cls.FILING_TYPES:  # pylint: disable=consider-using-dict-items
            if filing_type_code in cls.FILING_TYPES[filing_type]['type_code_list']:
                return filing_type
        return None

    @classmethod
    def _insert_filing(cls, cursor, filing,  # pylint: disable=too-many-statements, too-many-arguments;
                       ar_date: str = None, agm_date: str = None,
                       filing_type_code: str = None):
        """Add record to FILING."""
        try:
            insert_stmnt = (
                """
                INSERT INTO filing (event_id, filing_typ_cd, effective_dt
                """
            )
            values_stmnt = (
                """
                VALUES (:event_id, :filing_type_code,
                    TO_TIMESTAMP_TZ(:effective_dt,'YYYY-MM-DD"T"HH24:MI:SS.FFTZH:TZM')
                """
            )
            filing_type_code = filing_type_code or filing.get_filing_type_code()
            if filing_type_code in ['OTANN']:
                insert_stmnt = insert_stmnt + ', period_end_dt, agm_date, arrangement_ind, ods_typ_cd) '
                values_stmnt = values_stmnt + \
                    ", TO_DATE(:period_end_date, 'YYYY-mm-dd'), TO_DATE(:agm_date, 'YYYY-mm-dd'), 'N', 'P')"
                cursor.execute(
                    insert_stmnt + values_stmnt,
                    event_id=filing.event_id,
                    filing_type_code=filing_type_code,
                    effective_dt=filing.effective_date,
                    period_end_date=ar_date if not agm_date else agm_date,
                    agm_date=agm_date
                )
            elif filing_type_code in ['OTADD', 'OTCDR', 'OTINC']:
                insert_stmnt = insert_stmnt + ', arrangement_ind, ods_typ_cd) '
                values_stmnt = values_stmnt + ", 'N', 'P')"
                cursor.execute(
                    insert_stmnt + values_stmnt,
                    event_id=filing.event_id,
                    filing_type_code=filing_type_code,
                    effective_dt=filing.effective_date
                )
            elif filing_type_code in ['ANNBC']:
                insert_stmnt = insert_stmnt + ', period_end_dt, arrangement_ind, ods_typ_cd) '
                values_stmnt = values_stmnt + ", TO_DATE(:period_end_date, 'YYYY-mm-dd'), 'N', 'F')"
                cursor.execute(
                    insert_stmnt + values_stmnt,
                    event_id=filing.event_id,
                    filing_type_code=filing_type_code,
                    effective_dt=filing.effective_date,
                    period_end_date=ar_date
                )
            elif filing_type_code in ['NOCDR']:
                insert_stmnt = insert_stmnt + ', change_dt, arrangement_ind, ods_typ_cd) '
                values_stmnt = values_stmnt + ", TO_DATE(:filing_date, 'YYYY-mm-dd'), 'N', 'F')"
                cursor.execute(
                    insert_stmnt + values_stmnt,
                    event_id=filing.event_id,
                    filing_type_code=filing_type_code,
                    effective_dt=filing.effective_date,
                    filing_date=filing.filing_date[:10]
                )
            elif filing_type_code in ['NOCAD', 'TRANS',
                                      'CO_BC', 'CO_DI', 'CO_RR', 'CO_SS', 'CO_LI',
                                      'BEINC', 'ICORP', 'ICORU', 'ICORC',
                                      'AMLRB', 'AMALR', 'AMLRU', 'AMLRC',
                                      'AMLHB', 'AMALH', 'AMLHU', 'AMLHC',
                                      'AMLVB', 'AMALV', 'AMLVU', 'AMLVC',
                                      'CONTB', 'CONTI', 'CONTU', 'CONTC',
                                      'NOABE', 'NOALE', 'NOALR', 'NOALD',
                                      'NOALA', 'NOALB', 'NOALU', 'NOALC',
                                      'CONTO', 'COUTI', 'CO_PO', 'CO_PF',
                                      'AGMDT', 'AGMLC', 'IAMGO', 'AMALO',
                                      'RESTF', 'RESTL', 'RESXL', 'RESXF',
                                      'REGSN', 'REGSO', 'COURT']:
                arrangement_ind = 'N'
                court_order_num = None
                if filing_type_code in ['REGSN', 'REGSO', 'COURT']:
                    arrangement_ind = 'Y' if filing.body.get('effectOfOrder', '') == 'planOfArrangement' else 'N'
                    court_order_num = filing.body.get('fileNumber', None)
                elif court_order := filing.body.get('courtOrder', None):
                    arrangement_ind = 'Y' if court_order.get('effectOfOrder', None) else 'N'
                    court_order_num = court_order.get('fileNumber', None)

                insert_stmnt = insert_stmnt + ', arrangement_ind, court_order_num, ods_typ_cd) '
                values_stmnt = values_stmnt + ", :arrangement_ind, :court_order_num, 'F')"
                cursor.execute(
                    insert_stmnt + values_stmnt,
                    event_id=filing.event_id,
                    filing_type_code=filing_type_code,
                    effective_dt=filing.effective_date,
                    arrangement_ind=arrangement_ind,
                    court_order_num=court_order_num
                )
            elif filing_type_code in ['OTSPE']:
                insert_stmnt = insert_stmnt + ', arrangement_ind, ods_typ_cd) '
                values_stmnt = values_stmnt + ", 'N', 'S')"
                cursor.execute(
                    insert_stmnt + values_stmnt,
                    event_id=filing.event_id,
                    filing_type_code=filing_type_code,
                    effective_dt=filing.effective_date
                )
            elif filing_type_code in ['OTVDS', 'ADVD2']:
                insert_stmnt = insert_stmnt + ', arrangement_ind, ods_typ_cd) '
                values_stmnt = values_stmnt + ", 'N', 'F')"
                cursor.execute(
                    insert_stmnt + values_stmnt,
                    event_id=filing.event_id,
                    filing_type_code=filing_type_code,
                    effective_dt=filing.effective_date
                )
            else:
                current_app.logger.error(f'error in filing: Did not recognize filing type code: {filing_type_code}')
                raise InvalidFilingTypeException(filing_type=filing_type_code)
        except Exception as err:
            current_app.logger.error(
                f'error in filing: could not create filing {filing_type_code} for {filing.get_corp_num()}')
            raise err

    @classmethod
    def _insert_filing_user(cls, cursor, filing):
        """Add to the FILING_USER table."""
        try:
            cursor.execute(
                """
                INSERT INTO filing_user (event_id, user_id, last_nme, first_nme, middle_nme, email_addr, party_typ_cd,
                    role_typ_cd)
                VALUES (:event_id, :user_id, :last_name, NULL, NULL, :email_address, NULL, NULL)
                """,
                event_id=filing.event_id,
                user_id=filing.user_id,
                last_name=filing.get_certified_by(),
                email_address=filing.get_email()
            )
        except Exception as err:
            current_app.logger.error(err.with_traceback(None))
            raise err

    @classmethod
    def _insert_ledger_text(cls, cursor, filing, text: str):
        """Add note to ledger test table."""
        try:
            cursor.execute(
                """
                INSERT INTO ledger_text (event_id, ledger_text_dts, notation, dd_event_id, user_id)
                VALUES (:event_id, TO_TIMESTAMP_TZ(:ledger_text_dts, 'YYYY-MM-DD"T"HH24:MI:SS.FFTZH:TZM'), :notation,
                        :dd_event_id, :user_id)
                """,
                event_id=filing.event_id,
                ledger_text_dts=filing.effective_date,
                notation=text,
                dd_event_id=filing.event_id,
                user_id=filing.user_id
            )
        except Exception as err:
            current_app.logger.error(f'Failed to add ledger text: "{text}" for event {filing.event_id}')
            raise err

    @classmethod
    # pylint: disable=too-many-branches;
    def _get_filing_event_info(cls, cursor, filing: Filing, year: int = None) -> Dict:
        """Get the basic filing info that we care about for all filings."""
        # build base querystring
        querystring = """
            select event.event_id, event_timestmp, first_nme, middle_nme, last_nme, email_addr, period_end_dt,
            agm_date, effective_dt, event.corp_num, user_id, filing_typ_cd, arrangement_ind, court_order_num, nr_num
            from event
            join filing on filing.event_id = event.event_id
            left join filing_user on event.event_id = filing_user.event_id
            where
            """
        if filing.event_id:
            querystring += ' event.event_id=:event_id'
        else:
            querystring += ' filing_typ_cd=:filing_type_cd'
        if filing.business.corp_num:
            querystring += ' AND event.corp_num=:corp_num'
        if year:
            querystring += ' AND extract(year from PERIOD_END_DT)=:year'

        querystring += ' order by EVENT_TIMESTMP desc'
        try:
            if not cursor:
                cursor = DB.connection.cursor()
            if filing.event_id:
                if year:
                    cursor.execute(
                        querystring,
                        corp_num=filing.business.corp_num,
                        event_id=filing.event_id,
                        year=year
                    )
                else:
                    cursor.execute(
                        querystring,
                        corp_num=filing.business.corp_num,
                        event_id=filing.event_id
                    )
            else:
                filing_type_cd = filing.get_filing_type_code()
                if year:
                    cursor.execute(
                        querystring,
                        corp_num=filing.business.corp_num,
                        filing_type_cd=filing_type_cd,
                        year=year
                    )
                else:
                    cursor.execute(
                        querystring,
                        corp_num=filing.business.corp_num,
                        filing_type_cd=filing_type_cd
                    )
            event_info = cursor.fetchone()

            if not event_info:
                raise FilingNotFoundException(
                    identifier=filing.business.corp_num,
                    filing_type=filing.filing_type
                )
            event_info = dict(zip([x[0].lower() for x in cursor.description], event_info))
            # build filing user name from first, middle, last name
            filing_user_name = ' '.join(
                filter(None, [event_info['first_nme'], event_info['middle_nme'], event_info['last_nme']]))
            filing_email = event_info['email_addr']

            if not filing_user_name:
                filing_user_name = 'N/A'

            # if email is blank, set as empty tring
            if not filing_email:
                filing_email = ''

            event_info['certifiedBy'] = filing_user_name
            event_info['email'] = filing_email
            event_info['filing_type_code'] = event_info['filing_typ_cd']
            return event_info

        except Exception as err:
            if filing.business.corp_num:
                current_app.logger.error(f'error getting filing event info for corp {filing.business.corp_num}')
            else:
                current_app.logger.error('error getting filing event info')
            raise err

    @classmethod
    def _get_notation(cls, cursor, corp_num: str, filing_event_info: Dict) -> Dict:
        """Get notation for the corresponding event id."""
        querystring = 'select notation from ledger_text where event_id=:event_id'
        try:
            cursor.execute(querystring, event_id=filing_event_info['event_id'])
            notation = cursor.fetchone()
            if not notation:
                raise FilingNotFoundException(
                    identifier=corp_num,
                    filing_type=filing_event_info['filing_typ_cd']
                )

            notation = dict(zip([x[0].lower() for x in cursor.description], notation))

            return notation['notation']

        except Exception as err:
            current_app.logger.error(f'error getting special resolution filing for corp: {corp_num}')
            raise err

    @classmethod
    # pylint: disable=too-many-arguments; one extra
    def _create_party_roles(cls, cursor, party: Dict, business: Dict, event_id: str, corrected_id: str = None):
        """Create a corp_party for each role."""
        for role in party['roles']:
            party['role_type'] = Party.role_types[(role['roleType'])]
            if party['role_type'] == 'CPRTY' and corrected_id:
                # set to old event id for update
                party['prev_event_id'] = corrected_id
            party['appointmentDate'] = role['appointmentDate']
            Party.create_new_corp_party(cursor, event_id, party, business)

    @classmethod
    def _get_ar_component_event(cls, cursor, corp_num: str, type_code: str, ar_filing_event_info: Dict) -> str:
        """Get the event id for the corresponding component included in the AR."""
        events = cls._get_events(cursor=cursor, corp_num=corp_num, filing_type_code=type_code)
        event_id = None
        tmp_timestamp = datetime.datetime.fromtimestamp(0)
        for event in events:
            if ar_filing_event_info['event_timestmp'] >= event['date'] > tmp_timestamp:
                event_id = event['id']
                tmp_timestamp = event['date']
        return event_id if event_id else ar_filing_event_info['event_id']

    # pylint: disable=too-many-branches, too-many-locals, too-many-statements, too-many-nested-blocks;
    @classmethod
    def get_filing(cls, filing: Filing, con=None, year: int = None) -> Dict:
        """Get a Filing."""
        try:
            if not con:
                con = DB.connection
                # con.begin()
            cursor = con.cursor()
            corp_num = filing.business.corp_num
            # get the filing event info
            filing_event_info = cls._get_filing_event_info(filing=filing, year=year, cursor=cursor)
            if not filing_event_info:
                raise FilingNotFoundException(
                    identifier=corp_num,
                    filing_type=filing.filing_type
                )
            filing.paper_only = False
            filing.colin_only = False
            filing.effective_date = filing_event_info['effective_dt'] or filing_event_info['event_timestmp']
            filing.body = {
                'eventId': filing_event_info['event_id']
            }

            # TODO: simplify after consolidating schema
            schema_name = convert_to_snake(filing.filing_type)
            schema = get_schema(f'{schema_name}.json')
            # schema = get_schema(f'{schema_name.replace("_application", "")}.json')
            components = schema.get('properties').keys()

            if filing.filing_type in components:
                if filing.filing_type == 'changeOfAddress':
                    components = ['legalType', 'offices']
                else:
                    components = schema['properties'][filing.filing_type].get('properties').keys()

            if filing_event_info['filing_type_code'] == 'CO_DI':
                components = ['parties']

            if 'annualReportDate' in components:
                filing.body['annualReportDate'] = convert_to_json_date(filing_event_info['period_end_dt'])
                filing.effective_date = filing_event_info['period_end_dt']

            if 'annualGeneralMeetingDate' in components:
                filing.body['annualGeneralMeetingDate'] = convert_to_json_date(filing_event_info.get('agm_date', None))

            if filing.filing_type == 'annualReport' and filing.business.corp_type == 'BC':
                if parties := Party.get_by_event(cursor=cursor, corp_num=corp_num,
                                                 event_id=filing_event_info['event_id'], role_type='Officer'):
                    filing.body['parties'] = [x.as_dict() for x in parties]

            if 'offices' in components:
                event_id = filing_event_info['event_id']
                # special rules for ARs with offices included
                if filing.filing_type == 'annualReport':
                    event_id = cls._get_ar_component_event(
                        cursor=cursor, corp_num=corp_num, type_code='OTADD', ar_filing_event_info=filing_event_info)
                office_obj_list = Office.get_by_event(cursor=cursor, event_id=event_id)
                if not office_obj_list:
                    if filing.filing_type != 'annualReport':
                        raise OfficeNotFoundException(identifier=corp_num)
                    filing.paper_only = True
                    office_obj_list = Office.get_current(identifier=corp_num, cursor=cursor)

                filing.body['offices'] = Office.convert_obj_list(office_obj_list)

            if 'custodialOffice' in components:
                event_id = filing_event_info['event_id']
                office_obj_list = Office.get_by_event(cursor, event_id)
                converted_offices_list = Office.convert_obj_list(office_obj_list)
                filing.body['custodialOffice'] = converted_offices_list.get('custodialOffice')
                filing.paper_only = True

            if 'directors' in components:
                event_id = filing_event_info['event_id']
                # special rules for coop ARs with directors included
                if filing.filing_type == 'annualReport':
                    event_id = cls._get_ar_component_event(
                        cursor=cursor, corp_num=corp_num, type_code='OTCDR', ar_filing_event_info=filing_event_info)
                directors = Party.get_by_event(cursor=cursor, corp_num=corp_num, event_id=event_id)
                if not directors:
                    if filing.filing_type != 'annualReport':
                        raise PartiesNotFoundException(identifier=corp_num)
                    filing.paper_only = True
                    directors = Party.get_current(corp_num=corp_num, cursor=cursor)

                filing.body['directors'] = [x.as_dict() for x in directors]

            if 'parties' in components:
                parties = []
                if Filing.is_filing_type_match(filing, 'dissolution', 'voluntary'):
                    parties = Party.get_by_event(
                        cursor=cursor, corp_num=corp_num, event_id=filing_event_info['event_id'], role_type='Custodian')
                elif filing_event_info['filing_type_code'] == 'CO_DI':
                    parties = Party.get_by_event(
                        cursor=cursor, corp_num=corp_num, event_id=filing_event_info['event_id'], role_type='Director')

                    filing.body['comment'] = cls._get_notation(cursor=cursor,
                                                               corp_num=corp_num,
                                                               filing_event_info=filing_event_info)
                else:
                    parties = Party.get_by_event(
                        cursor=cursor, corp_num=corp_num, event_id=filing_event_info['event_id'], role_type=None)
                if not parties:
                    raise PartiesNotFoundException(identifier=corp_num)
                filing.body['parties'] = [x.as_dict() for x in parties]

            if 'shareStructure' in components:
                share_structure = ShareObject.get_all(cursor, corp_num, filing_event_info['event_id'])
                if share_structure:
                    filing.body['shareStructure'] = share_structure.to_dict()

                if resolution_dates := Business.get_resolutions(
                        cursor=cursor, corp_num=corp_num, event_id=filing_event_info['event_id']):
                    filing.body['shareStructure']['resolutionDates'] = resolution_dates

            if 'nameTranslations' in components:
                translations = CorpName.get_by_event(
                    cursor=cursor,
                    corp_num=corp_num,
                    event_id=filing_event_info['event_id'],
                    type_code='TR'
                )
                filing.body['nameTranslations'] = []
                for translation in translations:
                    if translation.event_id == filing_event_info['event_id']:
                        filing.body['nameTranslations'].append({'name': translation.corp_name, 'new': True})
                    elif translation.end_event_id == filing_event_info['event_id']:
                        filing.body['nameTranslations'].append({'name': translation.corp_name, 'ceased': True})
                if not filing.body['nameTranslations']:
                    del filing.body['nameTranslations']

            if 'nameRequest' in components or 'legalName' in components:
                names = CorpName.get_by_event(corp_num=corp_num, event_id=filing_event_info['event_id'], cursor=cursor)
                for name in names:
                    if name.event_id == filing_event_info['event_id']:
                        if 'nameRequest' in components:
                            filing.body['nameRequest'] = {
                                'legalName': name.corp_name,
                                'legalType': filing.business.corp_type
                            }
                            if nr_num := filing_event_info.get('nr_num'):
                                filing.body['nameRequest']['nrNumber'] = nr_num
                        else:
                            filing.body['legalName'] = name.corp_name
                        # should only ever be 1 active name for any given event
                        break

            if 'business' in components and schema_name == 'alteration':
                is_corp_num_decimal = corp_num.isdecimal()   # valid only for BC
                filing.body['business'] = {}
                if filing_event_info['filing_type_code'] in ['NOALR', 'NOALB']:
                    filing.body['business']['legalType'] = (
                        Business.TypeCodes.BC_COMP.value if is_corp_num_decimal
                        else Business.TypeCodes.CONTINUE_IN.value
                    )
                elif filing_event_info['filing_type_code'] in ['NOALE', 'NOALD', 'NOABE']:
                    filing.body['business']['legalType'] = (
                        Business.TypeCodes.BCOMP.value if is_corp_num_decimal
                        else Business.TypeCodes.BCOMP_CONTINUE_IN.value
                    )
                elif filing_event_info['filing_type_code'] == 'NOALU':
                    filing.body['business']['legalType'] = (
                        Business.TypeCodes.ULC_COMP.value if is_corp_num_decimal
                        else Business.TypeCodes.ULC_CONTINUE_IN.value
                    )
                elif filing_event_info['filing_type_code'] == 'NOALC':
                    filing.body['business']['legalType'] = (
                        Business.TypeCodes.CCC_COMP.value if is_corp_num_decimal
                        else Business.TypeCodes.CCC_CONTINUE_IN.value
                    )
                elif filing_event_info['filing_type_code'] == 'NOALA':
                    corp_type = cls._get_corp_type_for_event(corp_num=corp_num,
                                                             event_id=filing_event_info['event_id'],
                                                             cursor=cursor)
                    if corp_type:
                        filing.body['business']['legalType'] = corp_type
                    else:
                        raise UnableToDetermineCorpTypeException(filing_type=filing.filing_type)
                else:
                    raise InvalidFilingTypeException(filing_type=filing_event_info['filing_type_code'])
                if is_corp_num_decimal:
                    filing.body['business']['identifier'] = f'BC{filing.business.corp_num}'
                else:
                    filing.body['business']['identifier'] = filing.business.corp_num

            if 'provisionsRemoved' in components:
                provisions = Business.get_corp_restriction(
                    cursor=cursor, event_id=filing_event_info['event_id'], corp_num=corp_num)
                if provisions and provisions['end_event_id'] == filing_event_info['event_id']:
                    filing.body['provisionsRemoved'] = provisions['restriction_ind'] == 'Y'
                else:
                    filing.body['provisionsRemoved'] = False

            if 'hasProvisions' in components:
                provisions = Business.get_corp_restriction(
                    cursor=cursor,
                    event_id=filing_event_info['event_id'],
                    corp_num=corp_num
                )
                if provisions and provisions['restriction_ind'] == 'Y':
                    filing.body['hasProvisions'] = True
                else:
                    filing.body['hasProvisions'] = False

            if 'resolution' in components:
                filing.body['meetingDate'] = convert_to_json_datetime(filing.effective_date)
                filing.body['resolution'] = cls._get_notation(
                    cursor=cursor, corp_num=corp_num, filing_event_info=filing_event_info)
                filing.paper_only = True

            if 'dissolutionType' in components:
                filing.body['dissolutionType'] = filing.filing_sub_type

            if 'dissolutionDate' in components:
                filing.body['dissolutionDate'] = convert_to_json_datetime(filing.effective_date)
                filing.paper_only = True

            if 'contactPoint' in components:
                filing.body['contactPoint'] = {'email': filing_event_info['email']}

            if 'legalType' in components:
                filing.body['legalType'] = filing.business.corp_type

            if 'courtOrder' in components and filing_event_info.get('court_order_num', None):
                effect_of_order = 'planOfArrangement' if filing_event_info['arrangement_ind'] == 'Y' else ''
                filing.body['courtOrder'] = {'fileNumber': filing_event_info['court_order_num'],
                                             'effectOfOrder': effect_of_order}

            if filing.filing_type == 'incorporationApplication' and \
                    filing.business.corp_type == Business.TypeCodes.COOP.value:
                filing.paper_only = True

            filing.header = {
                'availableOnPaperOnly': filing.paper_only,
                'inColinOnly': filing.colin_only,
                'certifiedBy': filing_event_info['certifiedBy'],
                'colinIds': [filing.body['eventId']],
                'date': convert_to_json_date(filing_event_info['event_timestmp']),
                'colinDate': convert_to_json_datetime(filing_event_info['event_timestmp']),
                'effectiveDate': convert_to_json_datetime(filing.effective_date),
                'email': filing_event_info['email'],
                'name': filing.filing_type,
                'source': cls.LearSource.COLIN.value
            }
            if not filing.header['email']:
                del filing.header['email']

            return filing

        except FilingNotFoundException as err:
            # pass through exception to caller
            raise err

        except Exception as err:
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))
            raise err

    @classmethod
    def get_historic_filings(cls, business: Business) -> List:
        """Get list all filings from before the bob-date=2019-03-08."""
        try:
            historic_filings = []
            cursor = DB.connection.cursor()
            cursor.execute(
                """
                select event.event_id, event_timestmp, filing_typ_cd, effective_dt, period_end_dt, agm_date
                from event join filing on event.event_id = filing.event_id
                where corp_num=:identifier
                order by event_timestmp
                """,
                identifier=business.corp_num
            )
            filings_info_list = []

            legal_type = business.corp_type

            for filing_info in cursor:
                filings_info_list.append(dict(zip([x[0].lower() for x in cursor.description], filing_info)))
            for filing_info in filings_info_list:
                filing_info['filing_type'] = cls._get_filing_type(filing_info['filing_typ_cd'])
                date = convert_to_json_date(filing_info['event_timestmp'])
                if date < '2019-03-08' or legal_type != Business.TypeCodes.COOP.value:
                    filing = Filing()
                    filing.business = business
                    filing.header = {
                        'date': date,
                        'name': filing_info['filing_type'],
                        'effectiveDate': convert_to_json_date(filing_info['effective_dt']),
                        'historic': True,
                        'availableOnPaperOnly': True,
                        'colinIds': [filing_info['event_id']]
                    }
                    filing.body = {
                        filing_info['filing_type']: {
                            'annualReportDate': convert_to_json_date(filing_info['period_end_dt']),
                            'annualGeneralMeetingDate': convert_to_json_date(filing_info['agm_date'])
                        }
                    }
                    historic_filings.append(filing.as_dict())
            return historic_filings

        except InvalidFilingTypeException as err:
            current_app.logger.error('Unknown filing type found when getting historic filings for '
                                     f'{business.get_corp_num()}.')
            # pass through exception to caller
            raise err

        except Exception as err:
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))

            # pass through exception to caller
            raise err

    @classmethod
    def get_future_effective_filings(cls, business: Business) -> List:
        """Get the list of all future effective filings for a business."""
        try:
            future_effective_filings = []
            current_date = datetime.datetime.utcnow().strftime('%Y-%m-%d')
            cursor = DB.connection.cursor()
            cursor.execute(
                """
                select event.event_id, event_timestmp, filing_typ_cd, effective_dt, period_end_dt, agm_date
                from event join filing on event.event_id = filing.event_id
                where corp_num=:identifier
                and filing.effective_dt > TO_DATE(:current_date, 'YYYY-mm-dd')
                order by event_timestmp
                """,
                identifier=business.corp_num,
                current_date=current_date
            )
            filings_info_list = []

            for filing_info in cursor:
                filings_info_list.append(dict(zip([x[0].lower() for x in cursor.description], filing_info)))
            for filing_info in filings_info_list:
                filing_info['filing_type'] = cls._get_filing_type(filing_info['filing_typ_cd'])
                date = convert_to_json_date(filing_info['event_timestmp'])
                filing = Filing()
                filing.business = business
                filing.header = {
                    'date': date,
                    'name': filing_info['filing_type'],
                    'effectiveDate': convert_to_json_date(filing_info['effective_dt']),
                    'availableOnPaperOnly': True,
                    'colinIds': [filing_info['event_id']]
                }
                filing.body = {
                    filing_info['filing_type']: {
                    }
                }
                future_effective_filings.append(filing.as_dict())
            return future_effective_filings

        except InvalidFilingTypeException as err:
            current_app.logger.error('Unknown filing type found when getting future effective filings for '
                                     f'{business.get_corp_num()}.')
            raise err

        except Exception as err:
            current_app.logger.error(err.with_traceback(None))
            raise err

    @classmethod
    def add_administrative_dissolution_event(cls, con, corp_num, filing_dt) -> int:
        """Add administrative dissolution event."""
        cursor = con.cursor()
        event_id = cls._get_event_id(cursor=cursor, corp_num=corp_num, filing_dt=filing_dt, event_type='SYSDA')
        Business.update_corp_state(cursor, event_id, corp_num,
                                   Business.CorpStateTypes.ADMINISTRATIVE_DISSOLUTION.value)
        return event_id

    @classmethod
    def add_involuntary_dissolution_event(cls, con, corp_num, filing_dt, filing_body) -> int:
        """Add involuntary dissolution event."""
        if not (filing_meta_data := filing_body.get('metaData')):
            return None

        event_type = None
        corp_state = None
        if filing_meta_data.get('overdueARs'):
            event_type = 'SYSDF'
            corp_state = Business.CorpStateTypes.INVOLUNTARY_DISSOLUTION_NO_AR.value
        elif filing_meta_data.get('overdueTransition'):
            event_type = 'SYSDT'
            corp_state = Business.CorpStateTypes.INVOLUNTARY_DISSOLUTION_NO_TR.value

        if event_type:
            cursor = con.cursor()
            event_id = cls._get_event_id(cursor=cursor, corp_num=corp_num,
                                         filing_dt=filing_dt, event_type=event_type)
            Business.update_corp_state(cursor, event_id, corp_num, corp_state)
            return event_id

        return None

    @classmethod
    def add_limited_restoration_expiration_event(cls, con, corp_num, filing_dt) -> int:
        """Add limited restoration expiration event ."""
        cursor = con.cursor()
        event_id = cls._get_event_id(cursor=cursor, corp_num=corp_num, filing_dt=filing_dt, event_type='SYSDL')
        Business.update_corp_state(cursor, event_id, corp_num,
                                   Business.CorpStateTypes.RESTORATION_EXPIRATION.value)
        return event_id

    # pylint: disable=too-many-locals,too-many-statements,too-many-branches,too-many-nested-blocks;
    @classmethod
    def add_filing(cls, con, filing: Filing, lear_identifier: str) -> int:
        """Add new filing to COLIN tables."""
        try:
            if filing.filing_type not in ['agmExtension', 'agmLocationChange', 'alteration',
                                          'amalgamationApplication', 'amalgamationOut', 'annualReport',
                                          'changeOfAddress', 'changeOfDirectors', 'consentAmalgamationOut',
                                          'consentContinuationOut', 'continuationIn', 'continuationOut', 'courtOrder',
                                          'dissolution', 'incorporationApplication', 'putBackOn', 'putBackOff',
                                          'registrarsNotation', 'registrarsOrder', 'restoration', 'specialResolution',
                                          'transition']:
                raise InvalidFilingTypeException(filing_type=filing.filing_type)

            if filing.filing_sub_type \
                    and not Filing.is_supported_filing_sub_type(filing.filing_type, filing.filing_sub_type):
                current_app.logger.\
                    error(f'Filing type of {filing.filing_type} does not support sub type: {filing.filing_sub_type}')
                raise InvalidFilingTypeException(filing_type=filing.filing_type)

            legal_type = filing.business.corp_type
            corp_num = filing.business.corp_num

            filing.user_id = Filing.USERS[legal_type]
            business = filing.business.as_dict()
            cursor = con.cursor()
            # create new event record, return event ID
            filing.event_id = cls._get_event_id(cursor=cursor, corp_num=corp_num, filing_dt=filing.filing_date)
            # create new filing user
            cls._insert_filing_user(cursor=cursor, filing=filing)

            filing_source = filing.header.get('source')
            # annualReportDate and annualGeneralMeetingDate will be available in annualReport
            ar_date = filing.body.get('annualReportDate', None)
            agm_date = filing.body.get('annualGeneralMeetingDate', None)
            # create new filing
            cls._insert_filing(cursor=cursor, filing=filing, ar_date=ar_date, agm_date=agm_date)

            new_corp_type = None

            if filing.filing_type == 'amalgamationApplication':
                cls._process_amalgamating_businesses(cursor, filing)
            elif filing.filing_type == 'amalgamationOut':
                cls._process_amalgamation_out(cursor, filing)
            elif filing.filing_type == 'continuationIn':
                cls._process_continuation_in(cursor, filing)
            elif filing.filing_type == 'continuationOut':
                cls._process_continuation_out(cursor, filing)
            elif filing.filing_type == 'restoration':
                cls._process_restoration(cursor, filing)
            elif filing.filing_type == 'putBackOn':
                cls._process_put_back_on(cursor, filing)
            elif filing.filing_type == 'putBackOff':
                cls._process_put_back_off(cursor, filing)
            elif filing.filing_type == 'alteration':
                # alter corp type
                if (
                    (to_type := filing.body.get('business', {}).get('legalType')) and
                    to_type != filing.business.corp_type
                ):
                    new_corp_type = to_type
                    Business.update_corp_type(cursor=cursor, corp_num=corp_num, corp_type=new_corp_type)

            ar_text = cls._process_ar(cursor, filing, corp_num, ar_date, agm_date, filing_source)
            dir_text = cls._process_directors(cursor, filing, business, corp_num)
            office_text = cls._process_office(cursor=cursor, filing=filing)

            if parties := filing.body.get('parties', []):
                for party in parties:
                    cls._create_party_roles(cursor=cursor,
                                            party=party,
                                            business=business,
                                            event_id=filing.event_id)
            # add shares if not coop
            cls._process_share_structure(cursor, filing, corp_num)
            if filing.body.get('nameRequest'):
                cls._create_corp_name(cursor,
                                      filing,
                                      corp_num,
                                      new_corp_type or filing.business.corp_type)

            # add name translations
            cls._process_name_translations(cursor, filing, corp_num)

            if filing.body.get('provisionsRemoved'):
                provisions = Business.get_corp_restriction(cursor=cursor, event_id=None, corp_num=corp_num)
                if provisions and provisions['restriction_ind'] == 'Y':
                    Business.end_current_corp_restriction(
                        cursor=cursor, event_id=filing.event_id, corp_num=corp_num)

            if filing.body.get('hasProvisions'):
                provisions = Business.get_corp_restriction(cursor=cursor, event_id=None, corp_num=corp_num)
                if provisions and provisions['restriction_ind'] == 'N':
                    Business.end_current_corp_restriction(
                        cursor=cursor, event_id=filing.event_id, corp_num=corp_num)
                    Business.create_corp_restriction(
                        cursor=cursor, event_id=filing.event_id, corp_num=corp_num, provisions=True)
                elif not provisions:
                    Business.create_corp_restriction(
                        cursor=cursor, event_id=filing.event_id, corp_num=corp_num, provisions=True)

            ledger_text = f'{ar_text}{dir_text}{office_text}'.replace('  ', '')
            if ledger_text != '':
                cls._insert_ledger_text(cursor, filing, ledger_text)

            # add registrarsNotation, registrarsOrder or courtOrder ledger text record
            if filing.filing_type in ['registrarsNotation', 'registrarsOrder', 'courtOrder']:
                order_details = filing.body.get('orderDetails')
                cls._insert_ledger_text(cursor, filing, order_details)
            elif filing.filing_type == 'specialResolution':
                resolution_text = filing.body.get('resolution')
                cls._insert_ledger_text(cursor, filing, resolution_text)
            elif filing.filing_type == 'consentContinuationOut':
                authorization_text = 'AUTHORIZATION TO CONTINUE OUT TO '
                foreign_jurisdiction = filing.body.get('foreignJurisdiction')
                country_code = foreign_jurisdiction.get('country').upper()
                region_code = (foreign_jurisdiction.get('region') or '').upper()
                authorization_text += (f'{country_code}, {region_code}'
                                       if region_code
                                       else country_code)
                cls._insert_ledger_text(cursor, filing, authorization_text)
            elif filing.filing_type == 'agmLocationChange':
                year = filing.body.get('year')
                agm_location = filing.body.get('agmLocation')
                agm_location_text = f'OKAY TO HOLD {year} AGM IN {agm_location}.'
                cls._insert_ledger_text(cursor, filing, agm_location_text)
            elif filing.filing_type == 'agmExtension':
                year = filing.body.get('year')
                agm_ext_dt = filing.body.get('expireDateApprovedExt')
                agm_ext_str = datetime.datetime.fromisoformat(agm_ext_dt).strftime('%B %-d, %Y')
                agm_extension_text = f'The {year} AGM must be held by {agm_ext_str} at 11:59 pm Pacific time.'
                cls._insert_ledger_text(cursor, filing, agm_extension_text)
            elif filing.filing_type == 'consentAmalgamationOut':
                authorization_text = 'AUTHORIZATION TO AMALGAMATE TO '
                foreign_jurisdiction = filing.body.get('foreignJurisdiction')
                country_code = foreign_jurisdiction.get('country').upper()
                region_code = (foreign_jurisdiction.get('region') or '').upper()
                authorization_text += (f'{country_code}, {region_code}'
                                       if region_code
                                       else country_code)
                cls._insert_ledger_text(cursor, filing, authorization_text)

            # process voluntary dissolution
            if Filing.is_filing_type_match(filing, 'dissolution', 'voluntary'):
                Business.update_corp_state(cursor,
                                           filing.event_id,
                                           corp_num,
                                           Business.CorpStateTypes.VOLUNTARY_DISSOLUTION.value)

            # update corporation record
            is_annual_report = filing.filing_type == 'annualReport'
            if filing_source == cls.FilingSource.BAR.value:
                last_ar_filed_dt = Filing._get_last_ar_filed_date(filing.header, business)
            else:
                last_ar_filed_dt = ar_date

            Business.update_corporation(
                cursor=cursor, corp_num=corp_num, date=agm_date, annual_report=is_annual_report,
                last_ar_filed_dt=last_ar_filed_dt)

            is_new_ben = (filing.filing_type in ['incorporationApplication', 'amalgamationApplication'] and
                          business['business']['legalType'] == Business.TypeCodes.BCOMP.value)
            is_new_cben = (filing.filing_type == 'continuationIn' and
                           business['business']['legalType'] == Business.TypeCodes.BCOMP_CONTINUE_IN.value)
            is_alteration_to_ben_or_cben = (filing.filing_type == 'alteration' and
                                            new_corp_type in [
                                                Business.TypeCodes.BCOMP.value,
                                                Business.TypeCodes.BCOMP_CONTINUE_IN.value,
                                            ])

            # Freeze all entities except CP if business exists in lear and
            # 'enable-bc-ccc-ulc' flag is on else just freeze BEN
            is_frozen_condition = (
                flags.is_on('enable-bc-ccc-ulc') and
                business['business']['legalType'] != Business.TypeCodes.COOP.value and
                filing_source == cls.FilingSource.LEAR.value
            )
            current_app.logger.debug(f'Business {lear_identifier}, is_frozen_condition:{is_frozen_condition}')

            is_new_or_altered_ben = is_new_ben or is_new_cben or is_alteration_to_ben_or_cben

            if is_frozen_condition or is_new_or_altered_ben:
                Business.update_corp_frozen_type(cursor, corp_num, Business.CorpFrozenTypes.COMPANY_FROZEN.value)

            return filing.event_id

        except Exception as err:
            # something went wrong, roll it all back
            current_app.logger.error(err.with_traceback(None))
            raise err

    @classmethod
    def _get_last_ar_filed_date(cls, header: dict, business: dict):
        filing_year = header.get('filingYear')
        founding_date_str = business.get('business').get('foundingDate')

        # If the founding date has `-00:00`, replace it with `+00:00` before passing to the function
        if '-00:00' in founding_date_str:
            founding_date_str = founding_date_str.replace('-00:00', '+00:00')

        pacific_founding_date = datetime.datetime.fromisoformat(
            convert_to_pacific_time(founding_date_str)
        ).date()

        # Handle February 29 leap year edge case
        month = pacific_founding_date.month
        day = pacific_founding_date.day

        # If it's February 29 and the filing year is not a leap year, use February 28 instead
        if month == 2 and day == 29:
            is_leap_year = int(filing_year) % 4 == 0 and (int(filing_year) % 100 != 0 or (int(filing_year) % 400 == 0))
            if not is_leap_year:
                day = 28

        last_ar_filed_dt = f'{filing_year}-{month:02}-{day:02}'
        return last_ar_filed_dt

    @classmethod
    def get_filing_sub_type(cls, filing_type: str, filing_body: dict) -> Optional[str]:
        """Retrieve filing sub-type if available."""
        if filing_body \
            and filing_type \
            and (sub_type_property := Filing.FILING_TYPES
                 .get(filing_type, {})
                 .get('sub_type_property', None)):
            return filing_body.get(sub_type_property, None)
        return None

    @classmethod
    def is_supported_filing_sub_type(cls, filing_type: str, filing_sub_type: str):
        """Return whether filing type has filing sub-type."""
        sub_type_list = Filing.FILING_TYPES.get(filing_type, {}).get('sub_type_list', [])
        return filing_sub_type in sub_type_list

    @classmethod
    def is_filing_type_match(cls, filing: Filing, filing_type: str, filing_sub_type: str):
        """Return whether filing has specificed filing type and filing sub-type."""
        return filing.filing_type == filing_type and filing.filing_sub_type == filing_sub_type

    @classmethod
    def _process_restoration(cls, cursor, filing):
        """Process restoration."""
        corp_num = filing.get_corp_num()

        Office.end_office(cursor=cursor,
                          event_id=filing.event_id,
                          corp_num=corp_num,
                          office_code=Office.OFFICE_TYPES_CODES['custodialOffice'])

        Party.end_current(cursor, filing.event_id, corp_num, 'Custodian')

        approval_type = filing.body.get('approvalType')
        if approval_type == 'registrar':
            for party in filing.body['parties']:
                for role in party['roles']:
                    party['role_type'] = Party.role_types[(role['roleType'])]
                    if party['role_type'] == 'APP':
                        party['officeNotificationDt'] = filing.body.get('applicationDate')
                        role['appointmentDate'] = filing.body.get('noticeDate')

        corp_state = Business.CorpStateTypes.ACTIVE.value  # Active for fullRestoration and limitedRestorationToFull
        if filing.filing_sub_type in ['limitedRestoration', 'limitedRestorationExtension']:
            expiry_date = filing.body.get('expiry')
            cursor.execute("""UPDATE event SET trigger_dts=TO_DATE(:trigger_dts, 'YYYY-mm-dd')
                           WHERE event_id=:event_id""",
                           event_id=filing.event_id,
                           trigger_dts=expiry_date
                           )
            corp_state = Business.CorpStateTypes.LIMITED_RESTORATION.value
        Business.update_corp_state(cursor, filing.event_id, corp_num, corp_state)

    @classmethod
    def _process_put_back_on(cls, cursor, filing):
        """Process Put Back On."""
        corp_num = filing.get_corp_num()

        Office.end_office(cursor=cursor,
                          event_id=filing.event_id,
                          corp_num=corp_num,
                          office_code=Office.OFFICE_TYPES_CODES['custodialOffice'])

        Party.end_current(cursor, filing.event_id, corp_num, 'Custodian')

        corp_state = Business.CorpStateTypes.ACTIVE.value  # Active for Put Back On
        Business.update_corp_state(cursor, filing.event_id, corp_num, corp_state)

    @classmethod
    def _process_put_back_off(cls, cursor, filing):
        """Process Put Back Off."""
        corp_num = filing.get_corp_num()

        corp_state = Business.CorpStateTypes.INVOLUNTARY_DISSOLUTION_NO_AR.value
        Business.update_corp_state(cursor, filing.event_id, corp_num, corp_state)

    @classmethod
    def _process_continuation_out(cls, cursor, filing):
        """Process continuation out."""
        corp_num = filing.get_corp_num()

        cont_out = ContOut()
        cont_out.corp_num = corp_num
        cont_out.start_event_id = filing.event_id
        cont_out.cont_out_dt = filing.body.get('continuationOutDate')
        cont_out.home_company_nme = filing.body.get('legalName')

        foreign_jurisdiction = filing.body.get('foreignJurisdiction')
        country_code = foreign_jurisdiction.get('country').upper()
        region_code = (foreign_jurisdiction.get('region') or '').upper()
        if country_code == 'CA':
            if region_code == 'FEDERAL':
                cont_out.can_jur_typ_cd = 'FD'
            else:
                cont_out.can_jur_typ_cd = region_code
        else:
            cont_out.can_jur_typ_cd = 'OT'
            cont_out.othr_juri_desc = \
                f'{country_code}, {region_code}' if region_code else country_code

        ContOut.create_cont_out(cursor, cont_out)

        continued_to = cont_out.othr_juri_desc if cont_out.can_jur_typ_cd == 'OT' else cont_out.can_jur_typ_cd
        cont_out_dt_str = datetime.datetime.fromisoformat(cont_out.cont_out_dt).strftime('%B %-d, %Y')
        cls._insert_ledger_text(
            cursor,
            filing,
            f'CONTINUED TO {continued_to} EFFECTIVE {cont_out_dt_str} UNDER THE NAME "{cont_out.home_company_nme}"'
        )

        Business.update_corp_state(cursor, filing.event_id, corp_num, Business.CorpStateTypes.CONTINUE_OUT.value)

    @classmethod
    def _process_continuation_in(cls, cursor, filing):
        """Process continuation in."""
        foreign_jurisdiction = filing.body.get('foreignJurisdiction')
        jurisdiction = Jurisdiction()
        jurisdiction.corp_num = filing.get_corp_num()
        jurisdiction.start_event_id = filing.event_id

        country_code = foreign_jurisdiction.get('country').upper()
        region_code = (foreign_jurisdiction.get('region') or '').upper()
        if country_code == 'CA':
            if region_code == 'FEDERAL':
                jurisdiction.can_jur_typ_cd = 'FD'
            else:
                jurisdiction.can_jur_typ_cd = region_code
        else:
            jurisdiction.can_jur_typ_cd = 'OT'
            jurisdiction.othr_juris_desc = \
                f'{country_code}, {region_code}' if region_code else country_code

        jurisdiction.home_recogn_dt = foreign_jurisdiction.get('incorporationDate')
        jurisdiction.home_juris_num = foreign_jurisdiction.get('identifier')
        jurisdiction.home_company_nme = foreign_jurisdiction.get('legalName')

        if expro_business := filing.body.get('business'):
            # jurisdiction.xpro_typ_cd = 'COR'
            jurisdiction.bc_xpro_num = expro_business.get('identifier')

            Business.update_corp_state(cursor,
                                       filing.event_id,
                                       jurisdiction.bc_xpro_num,
                                       Business.CorpStateTypes.CONTINUE_IN.value)

        Jurisdiction.create_jurisdiction(cursor, jurisdiction)

    @classmethod
    def _process_amalgamating_businesses(cls, cursor, filing):
        """Process amalgamating businesses."""
        for index, amalgamating_business in enumerate(filing.body.get('amalgamatingBusinesses', [])):
            corp_involved = CorpInvolved()
            corp_involved.event_id = filing.event_id
            corp_involved.corp_involve_id = index

            identifier = amalgamating_business.get('identifier')

            if ((foreign_jurisdiction := amalgamating_business.get('foreignJurisdiction', {})) and
                not (identifier.startswith('A') and  # is expro
                     foreign_jurisdiction.get('country') == 'CA' and
                     foreign_jurisdiction.get('region') == 'BC')):
                corp_involved.home_juri_num = identifier
                corp_involved.foreign_nme = amalgamating_business.get('legalName')

                country_code = foreign_jurisdiction.get('country').upper()
                region_code = (foreign_jurisdiction.get('region') or '').upper()
                if country_code == 'CA':
                    if region_code == 'FEDERAL':
                        corp_involved.can_jur_typ_cd = 'FD'
                    else:
                        corp_involved.can_jur_typ_cd = region_code
                else:
                    corp_involved.can_jur_typ_cd = 'OT'
                    corp_involved.othr_juri_desc = \
                        f'{country_code}, {region_code}' if region_code else country_code
            else:
                # strip prefix BC
                if identifier.startswith('BC'):
                    identifier = identifier[2:]
                corp_involved.corp_num = identifier

                if amalgamating_business['role'] in ['holding', 'primary']:
                    corp_involved.adopted_corp_ind = 'Y'

                Business.update_corp_state(cursor,
                                           filing.event_id,
                                           identifier,
                                           Business.CorpStateTypes.AMALGAMATED.value)

            CorpInvolved.create_corp_involved(cursor, corp_involved)

    @classmethod
    def _process_amalgamation_out(cls, cursor, filing):
        """Process amalgamation out."""
        corp_num = filing.get_corp_num()

        cont_out = ContOut()
        cont_out.corp_num = corp_num
        cont_out.start_event_id = filing.event_id
        cont_out.cont_out_dt = filing.body.get('amalgamationOutDate')
        cont_out.home_company_nme = filing.body.get('legalName')

        foreign_jurisdiction = filing.body.get('foreignJurisdiction')
        country_code = foreign_jurisdiction.get('country').upper()
        region_code = (foreign_jurisdiction.get('region') or '').upper()
        if country_code == 'CA':
            if region_code == 'FEDERAL':
                cont_out.can_jur_typ_cd = 'FD'
            else:
                cont_out.can_jur_typ_cd = region_code
        else:
            cont_out.can_jur_typ_cd = 'OT'
            cont_out.othr_juri_desc = \
                f'{country_code}, {region_code}' if region_code else country_code

        ContOut.create_cont_out(cursor, cont_out)

        amalgamated_to = cont_out.othr_juri_desc if cont_out.can_jur_typ_cd == 'OT' else cont_out.can_jur_typ_cd
        aml_out_dt_str = datetime.datetime.fromisoformat(cont_out.cont_out_dt).strftime('%B %-d, %Y')
        cls._insert_ledger_text(
            cursor,
            filing,
            f'AMALGAMATED OUT TO {amalgamated_to} EFFECTIVE {aml_out_dt_str} \
                UNDER THE NAME "{cont_out.home_company_nme}"'
        )

        Business.update_corp_state(cursor, filing.event_id, corp_num, Business.CorpStateTypes.AMALGAMATE_OUT.value)

    @classmethod
    # pylint: disable=too-many-arguments;
    def _process_ar(cls, cursor, filing: Filing, corp_num: str, ar_date: str, agm_date: str, filing_source: str) -> str:
        """Process specific to annual report."""
        text = ''
        if filing.filing_type == 'annualReport' and filing_source != cls.FilingSource.BAR.value:
            # update corp_state TO ACT (active) if it is in good standing. From CRUD:
            # - the current corp_state != 'ACT' and,
            # - they just filed the last outstanding ARs
            agm_year = int(ar_date[:4])
            if filing.business.corp_state != 'ACT':
                last_year = datetime.datetime.now().year - 1
                if agm_year >= last_year:
                    Business.update_corp_state(cursor=cursor, event_id=filing.event_id, corp_num=corp_num)

            # create new ledger text for annual report
            ledger_year = agm_date if agm_date else f'NO AGM HELD IN {agm_year}'
            text = f'ANNUAL REPORT - {ledger_year}'
        return text

    @classmethod
    def _process_office(cls, cursor, filing: Filing) -> str:
        """Add offices from the filing."""
        text = ''

        # offices in annualReport is redundant, skip it
        if filing.filing_type == 'annualReport':
            return ''

        corp_num = filing.get_corp_num()
        if Filing.is_filing_type_match(filing, 'dissolution', 'voluntary'):
            office = filing.body.get('custodialOffice')
            office_type = 'custodialOffice'
            Office.create_new_office(
                cursor=cursor,
                addresses=office,
                event_id=filing.event_id,
                corp_num=corp_num,
                office_type=office_type
            )
            return ''

        for office_type in filing.body.get('offices', []):
            Office.create_new_office(
                cursor=cursor,
                addresses=filing.body['offices'][office_type],
                event_id=filing.event_id,
                corp_num=corp_num,
                office_type=office_type
            )
            # create new ledger text for address change
            if filing.filing_type not in ['amalgamationApplication', 'continuationIn', 'incorporationApplication']:
                office_desc = (office_type.replace('O', ' O')).title()
                if text:
                    text = f'{text} Change to the {office_desc}.'
                else:
                    text = f'Change to the {office_desc}.'
        return text

    @classmethod
    def _process_directors(cls, cursor, filing: Filing, business: Business, corp_num: str) -> str:
        """Process directors."""
        text = ''
        # directors in annualReport is redundant, skip it
        if filing.filing_type != 'annualReport' and filing.body.get('directors', []):
            # create, cease, change directors
            changed_dirs = []
            for director in filing.body.get('directors', []):
                if 'appointed' in director['actions']:
                    Party.create_new_corp_party(cursor=cursor, event_id=filing.event_id, party=director,
                                                business=business)

                if 'ceased' in director['actions'] and not any(elem in ['nameChanged', 'addressChanged']
                                                               for elem in director['actions']):
                    Party.end_director_by_name(
                        cursor=cursor, director=director, event_id=filing.event_id, corp_num=corp_num
                    )

                elif 'nameChanged' in director['actions'] or 'addressChanged' in director['actions']:
                    if 'appointed' in director['actions']:
                        current_app.logger.error(f'Director appointed with name/address change: {director}')

                    found_match = False
                    current_parties = Party.get_current(cursor=cursor, corp_num=corp_num)
                    for current_party in current_parties:
                        # compare off of old value name (existing way)
                        if Party.compare_parties(party=current_party, officer_json=director['officer']):
                            director['prev_id'] = current_party.corp_party_id
                            Party.end_director_by_name(
                                cursor=cursor, director=director, event_id=filing.event_id, corp_num=corp_num
                            )
                            changed_dirs.append(director)
                            found_match = True
                    if not found_match:
                        raise GenericException(
                            error=f'Director does not exist in COLIN: {director["officer"]}',
                            status_code=HTTPStatus.NOT_FOUND
                        )

            # add back changed directors as new row - if ceased director with changes this will add them with
            # cessation date + end event id filled
            for director in changed_dirs:
                Party.create_new_corp_party(cursor=cursor, event_id=filing.event_id, party=director,
                                            business=business)

            # create new ledger text for address change
            text = 'Director change.'
        return text

    @classmethod
    def _create_corp_name(cls, cursor, filing: Filing, corp_num: str, corp_type: str):
        """Create name."""
        numbered_name = cls.generate_numbered_legal_name(corp_type, corp_num)
        if not (name := filing.body.get('nameRequest', {}).get('legalName')):
            name = numbered_name

        if filing.filing_type in ['amalgamationApplication', 'continuationIn', 'incorporationApplication']:
            # create corp state
            Business.create_corp_state(cursor=cursor, corp_num=corp_num, event_id=filing.event_id)
        elif filing.filing_type in ['alteration', 'restoration', 'correction']:
            old_corp_name = CorpName.get_current_name_or_numbered(cursor=cursor, corp_num=corp_num)
            if old_corp_name.corp_name != name:
                # end old corp name
                CorpName.end_current(cursor=cursor, event_id=filing.event_id, corp_num=corp_num)
            else:
                return  # No change

        corp_name_obj = CorpName()
        corp_name_obj.corp_num = corp_num
        corp_name_obj.event_id = filing.event_id
        if name and name != numbered_name:
            corp_name_obj.corp_name = name
            corp_name_obj.type_code = CorpName.TypeCodes.CORP.value
        else:
            corp_name_obj.corp_name = numbered_name
            corp_name_obj.type_code = CorpName.TypeCodes.NUMBERED_CORP.value
        CorpName.create_corp_name(cursor=cursor, corp_name_obj=corp_name_obj)

    @classmethod
    def generate_numbered_legal_name(cls, legal_type, identifier):
        """Generate legal name for a numbered business."""
        if legal_type not in Business.NUMBERED_CORP_NAME_SUFFIX:
            return None

        numbered_legal_name_suffix = Business.NUMBERED_CORP_NAME_SUFFIX[legal_type]
        numbered_legal_name_prefix = identifier
        if legal_type in (Business.TypeCodes.BCOMP_CONTINUE_IN.value,
                          Business.TypeCodes.ULC_CONTINUE_IN.value,
                          Business.TypeCodes.CCC_CONTINUE_IN.value,
                          Business.TypeCodes.CONTINUE_IN.value):
            numbered_legal_name_prefix = identifier[1:]

        return f'{numbered_legal_name_prefix} {numbered_legal_name_suffix}'

    @classmethod
    def _process_share_structure(cls, cursor, filing: Filing, corp_num: str):
        """Process share structure."""
        if share_structure := filing.body.get('shareStructure', None):
            for date_str in share_structure.get('resolutionDates', []):
                Business.create_resolution(
                    cursor=cursor,
                    corp_num=corp_num,
                    event_id=filing.event_id,
                    resolution_date=date_str
                )

            if filing.business.corp_type != Business.TypeCodes.COOP.value and \
                    (share_classes := share_structure.get('shareClasses', None)):
                if filing.filing_type == 'alteration':
                    ShareObject.end_share_structure(cursor=cursor, event_id=filing.event_id, corp_num=corp_num)

                ShareObject.create_share_structure(
                    cursor=cursor,
                    corp_num=corp_num,
                    event_id=filing.event_id,
                    shares_list=share_classes
                )

    @classmethod
    def _process_name_translations(cls, cursor, filing: Filing, corp_num: str):
        """Process name translations."""
        if 'nameTranslations' not in filing.body:
            return

        name_translations = filing.body.get('nameTranslations', [])
        old_translations = CorpName.get_current_by_type(
            cursor=cursor,
            corp_num=corp_num,
            type_code=CorpName.TypeCodes.TRANSLATION.value
        )

        CorpName.create_translations(cursor, corp_num, filing.event_id, name_translations, old_translations)
        #  End translations in db that are not present in the incoming filing json.
        for old_translation in old_translations:
            if not next((x for x in name_translations if x['name'] == old_translation.corp_name), None):
                CorpName.end_name(
                    cursor=cursor,
                    event_id=filing.event_id,
                    corp_num=corp_num,
                    corp_name=old_translation.corp_name,
                    type_code=CorpName.TypeCodes.TRANSLATION.value
                )

    @classmethod
    def _process_name_correction(cls, cursor, filing: Filing, corp_num: str, filing_type_code: str):
        """Process name correction."""
        # create new event record, return event ID
        filing.event_id = cls._get_event_id(cursor=cursor, corp_num=corp_num, filing_dt=filing.filing_date)
        cls._insert_filing_user(cursor=cursor, filing=filing)
        cls._insert_filing(cursor=cursor, filing=filing, filing_type_code=filing_type_code)

        if filing.body.get('nameRequest'):
            cls._create_corp_name(cursor, filing, corp_num, filing.business.corp_type)

        cls._process_name_translations(cursor, filing, corp_num)

        return filing.event_id

    @classmethod
    def _process_office_correction(cls, cursor, filing: Filing, corp_num: str, filing_type_code: str):
        """Process office correction."""
        # create new event record, return event ID
        filing.event_id = cls._get_event_id(cursor=cursor, corp_num=corp_num, filing_dt=filing.filing_date)
        cls._insert_filing_user(cursor=cursor, filing=filing)
        cls._insert_filing(cursor=cursor, filing=filing, filing_type_code=filing_type_code)

        cls._process_office(cursor, filing)

        return filing.event_id

    @classmethod
    def _process_director_correction(cls, cursor,  # pylint: disable=too-many-arguments;
                                     business: dict, filing: Filing,
                                     corp_num: str, filing_type_code: str):
        """Process director correction."""
        # create new event record, return event ID
        filing.event_id = cls._get_event_id(cursor=cursor, corp_num=corp_num, filing_dt=filing.filing_date)
        cls._insert_filing_user(cursor=cursor, filing=filing)
        cls._insert_filing(cursor=cursor, filing=filing, filing_type_code=filing_type_code)

        if parties := filing.body.get('parties', None):
            Party.end_current(cursor, filing.event_id, corp_num, 'Director')  # Cannot compare, user can change names
            for party in parties:
                cls._create_party_roles(cursor=cursor,
                                        party=party,
                                        business=business,
                                        event_id=filing.event_id)

        return filing.event_id

    @classmethod
    def _process_share_correction(cls, cursor, filing: Filing, corp_num: str, filing_type_code: str):
        """Process share correction."""
        filing.event_id = cls._get_event_id(cursor=cursor, corp_num=corp_num, filing_dt=filing.filing_date)
        cls._insert_filing_user(cursor=cursor, filing=filing)
        cls._insert_filing(cursor=cursor, filing=filing, filing_type_code=filing_type_code)

        share_structure = filing.body.get('shareStructure', {})
        if share_classes := share_structure.get('shareClasses', []):
            ShareObject.end_share_structure(cursor=cursor, event_id=filing.event_id, corp_num=corp_num)
            ShareObject.create_share_structure(
                cursor=cursor,
                corp_num=corp_num,
                event_id=filing.event_id,
                shares_list=share_classes
            )

        old_resolution_dates = Business.get_resolutions(cursor, corp_num)
        for date_str in share_structure.get('resolutionDates', []):
            if date_str not in old_resolution_dates:  # new resolution date
                Business.create_resolution(
                    cursor=cursor,
                    corp_num=corp_num,
                    event_id=filing.event_id,
                    resolution_date=date_str
                )
            else:  # existing resolution date (not changed)
                old_resolution_dates.remove(date_str)

        if old_resolution_dates:  # remove deleted resolution dates
            for resoultion_date in old_resolution_dates:
                Business.end_resolution(cursor, corp_num, filing.event_id, resoultion_date)

        return filing.event_id

    @classmethod
    def _process_comment_correction(cls, cursor, filing: Filing, corp_num: str, filing_type_code: str):
        """Process comment correction."""
        # create new event record, return event ID
        filing.event_id = cls._get_event_id(cursor=cursor, corp_num=corp_num, filing_dt=filing.filing_date)
        cls._insert_filing_user(cursor=cursor, filing=filing)
        cls._insert_filing(cursor=cursor, filing=filing, filing_type_code=filing_type_code)

        ledger_text = filing.body.get('comment', '')
        cls._insert_ledger_text(cursor, filing, ledger_text)

        return filing.event_id

    @classmethod
    def add_correction_filings(cls, con, filing: Filing) -> list:
        """Create correction filings."""
        try:
            filings_added = []

            legal_type = filing.business.corp_type
            corp_num = filing.business.corp_num

            filing.user_id = Filing.USERS[legal_type]
            business = filing.business.as_dict()
            cursor = con.cursor()

            sub_type = None
            if legal_type in Business.CORPS:
                sub_type = 'CORPS'
            else:
                raise GenericException(
                    'Correction is only implemented for CORPS',
                    HTTPStatus.NOT_IMPLEMENTED)

            if filing.body.get('nameChanged') or filing.body.get('nameTranslationsChanged'):
                filing_type_code = Filing.FILING_TYPES[filing.filing_type][f'{sub_type}_NAME']
                event_id = cls._process_name_correction(cursor, filing, corp_num, filing_type_code)

                filings_added.append({'event_id': event_id,
                                      'filing_type': filing.filing_type,
                                      'filing_sub_type': None})

            if filing.body.get('officeChanged'):
                filing_type_code = Filing.FILING_TYPES[filing.filing_type][f'{sub_type}_OFFICE']
                event_id = cls._process_office_correction(cursor, filing, corp_num, filing_type_code)

                filings_added.append({'event_id': event_id,
                                      'filing_type': filing.filing_type,
                                      'filing_sub_type': None})

            if filing.body.get('partyChanged'):
                filing_type_code = Filing.FILING_TYPES[filing.filing_type][f'{sub_type}_DIRECTOR']
                event_id = cls._process_director_correction(cursor, business, filing, corp_num, filing_type_code)

                filings_added.append({'event_id': event_id,
                                      'filing_type': filing.filing_type,
                                      'filing_sub_type': None})

            if filing.body.get('shareChanged') or filing.body.get('resolutionChanged'):
                filing_type_code = Filing.FILING_TYPES[filing.filing_type][f'{sub_type}_SHARE']
                event_id = cls._process_share_correction(cursor, filing, corp_num, filing_type_code)

                filings_added.append({'event_id': event_id,
                                      'filing_type': filing.filing_type,
                                      'filing_sub_type': None})

            # only comment added or running BEN correction statement job
            if bool(filing.body.get('commentOnly', False)) or bool(filing.header.get('correctionBenStatement', False)):
                filing_type_code = Filing.FILING_TYPES[filing.filing_type][f'{sub_type}_COMMENT_ONLY']
                event_id = cls._process_comment_correction(cursor, filing, corp_num, filing_type_code)

                filings_added.append({'event_id': event_id,
                                      'filing_type': filing.filing_type,
                                      'filing_sub_type': None})

            if not filings_added:  # if no filing created
                raise GenericException(  # pylint: disable=broad-exception-raised
                    f'No filing created for this correction identifier:{corp_num}.',
                    HTTPStatus.NOT_IMPLEMENTED
                )

            return filings_added

        except Exception as err:
            # something went wrong, roll it all back
            current_app.logger.error(err.with_traceback(None))
            raise err
