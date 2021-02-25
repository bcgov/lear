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
"""Test Correction validations."""
import copy
from http import HTTPStatus
from unittest.mock import patch

from registry_schemas.example_data import ALTERATION_FILING_TEMPLATE

from legal_api.services import NameXService
from legal_api.services.filings import validate
from tests.unit.models import factory_business


ALTERATION_FILING = copy.deepcopy(ALTERATION_FILING_TEMPLATE)


def test_valid_alteration(session):
    """Test that a valid Alteration without NR correction passes validation."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier)

    f = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    f['filing']['header']['identifier'] = identifier

    del f['filing']['alteration']['nameRequest']

    err = validate(business, f)

    if err:
        print(err.msg)

    # check that validation passed
    assert None is err


def test_valid_nr_alteration(session):
    """Test that a valid NR alteration passes validation."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier)

    f = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    f['filing']['header']['identifier'] = identifier

    f['filing']['business']['identifier'] = identifier
    f['filing']['business']['legalName'] = 'legal_name-BC1234567'

    f['filing']['alteration']['nameRequest']['nrNumber'] = identifier
    f['filing']['alteration']['nameRequest']['legalName'] = 'legal_name-BC1234567_Changed'
    f['filing']['alteration']['nameRequest']['legalType'] = 'BEN'

    nr_response = {
        'state': 'APPROVED',
        'expirationDate': '',
        'names': [{
            'name': 'legal_name-BC1234567_Changed',
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


def test_invalid_nr_alteration(session):
    """Test that an invalid NR alteration fails validation."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier)

    f = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    f['filing']['header']['identifier'] = identifier

    f['filing']['business']['identifier'] = identifier
    f['filing']['business']['legalName'] = 'legal_name-BC1234567'

    f['filing']['alteration']['nameRequest']['nrNumber'] = 'BC1234568'
    f['filing']['alteration']['nameRequest']['legalType'] = 'CP'
    f['filing']['alteration']['nameRequest']['legalName'] = 'legal_name-BC1234568'

    nr_response = {
        'state': 'INPROGRESS',
        'expirationDate': '',
        'names': [{
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
