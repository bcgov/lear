# Copyright © 2020 Province of British Columbia
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
"""The Unit Tests for the Incorporation filing."""

import copy
from datetime import datetime
from unittest.mock import patch

import pytest
from legal_api.models import Filing
from registry_schemas.example_data import ALTERATION_FILING_TEMPLATE

from entity_filer.filing_processors import alteration
from tests.unit import create_filing

ALTERATION = {
    'provisionsRemoved': False,
    'business': {
        'corpType': 'benefitCompany'
    },
    'nameRequest': {
        'nrNumber': 'NR 8798956',
        'legalName': 'HAULER MEDIA INC.',
        'legalType': 'BC'
    },
    'nameTranslations': {
        'new': ['MÉDIAS DE TRANSPORT INC.'],
        'modified': [{
            'oldValue': 'A1 LTD.',
            'newValue': 'SOCIÉTÉ GÉNÉRALE'
        }],
        'ceased': ['B1', 'B2']
    },
    'shareStructure': {
        'resolutionDates': ['2020-05-23', '2020-06-01'],
        'shareClasses': [{
            'name': 'class1',
            'priority': 1,
            'maxNumberOfShares': 600,
            'parValue': 1,
            'currency': 'CAD',
            'hasMaximumShares': True,
            'hasParValue': True,
            'hasRightsOrRestrictions': False,
            'series': [{
                'name': 'series1',
                'priority': 1,
                'maxNumberOfShares': 600,
                'hasMaximumShares': True,
                'hasRightsOrRestrictions': False
            }]
        }]
    }
}
