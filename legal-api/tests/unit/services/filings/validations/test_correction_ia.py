# Copyright © 2019 Province of British Columbia
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
"""Test Correction IA validations."""

import copy
from http import HTTPStatus
from unittest.mock import patch

from registry_schemas.example_data import CORRECTION_INCORPORATION, INCORPORATION_FILING_TEMPLATE

from legal_api.services import NameXService
from legal_api.services.filings import validate
from tests.unit.models import factory_business, factory_completed_filing


INCORPORATION_APPLICATION = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)


def test_valid_ia_correction(session):
    """Test that a valid IA without NR correction passes validation."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier)

    corrected_filing = factory_completed_filing(business, INCORPORATION_APPLICATION)

    f = copy.deepcopy(CORRECTION_INCORPORATION)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id

    err = validate(business, f)

    if err:
        print(err.msg)

    # check that validation passed
    assert None is err


def test_valid_nr_correction(session):
    """Test that a valid NR correction passes validation."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier)

    INCORPORATION_APPLICATION['filing']['incorporationApplication']['nameRequest']['nrNumber'] = identifier
    INCORPORATION_APPLICATION['filing']['incorporationApplication']['nameRequest']['legalName'] = 'legal_name-BC1234567'

    corrected_filing = factory_completed_filing(business, INCORPORATION_APPLICATION)

    f = copy.deepcopy(CORRECTION_INCORPORATION)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id

    f['filing']['incorporationApplication']['nameRequest']['nrNumber'] = identifier
    f['filing']['incorporationApplication']['nameRequest']['legalName'] = 'legal_name-BC1234567_Changed'

    nr_response = {
        'state': 'APPROVED',
        'expirationDate': '',
        'names': [{
            'name': 'legal_name-BC1234567',
            'state': 'APPROVED',
            'consumptionDate': ''
        }]
    }
    with patch.object(NameXService, 'query_nr_number', return_value=nr_response):
        err = validate(business, f)

    if err:
        print(err.msg)

    # check that validation passed
    assert None is err


def test_invalid_nr_correction(session):
    """Test that an invalid NR correction fails validation."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier)

    INCORPORATION_APPLICATION['filing']['incorporationApplication']['nameRequest']['nrNumber'] = identifier
    INCORPORATION_APPLICATION['filing']['incorporationApplication']['nameRequest']['legalName'] = 'legal_name-BC1234567'

    corrected_filing = factory_completed_filing(business, INCORPORATION_APPLICATION)

    f = copy.deepcopy(CORRECTION_INCORPORATION)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id

    f['filing']['incorporationApplication']['nameRequest']['nrNumber'] = 'BC1234568'
    f['filing']['incorporationApplication']['nameRequest']['legalType'] = 'CP'
    f['filing']['incorporationApplication']['nameRequest']['legalName'] = 'legal_name-BC1234568'

    nr_response = {
        'state': 'INPROGRESS',
        'expirationDate': '',
        'names': [{
            'name': 'legal_name-BC1234567',
            'state': 'APPROVED',
            'consumptionDate': ''
        }, {
            'name': 'legal_name-BC1234567_Changed',
            'state': 'INPROGRESS',
            'consumptionDate': ''
        }]
    }
    with patch.object(NameXService, 'query_nr_number', return_value=nr_response):
        err = validate(business, f)

    if err:
        print(err.msg)

    # check that validation failed
    assert err
    assert HTTPStatus.BAD_REQUEST == err.code
    assert len(err.msg) == 3
