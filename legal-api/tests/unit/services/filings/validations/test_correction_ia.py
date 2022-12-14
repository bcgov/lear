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
from tests.unit import MockResponse

import pytest
from registry_schemas.example_data import CORRECTION_INCORPORATION, INCORPORATION_FILING_TEMPLATE

from legal_api.services import NameXService
from legal_api.services.filings import validate
from tests.unit.models import factory_business, factory_completed_filing
from tests import todo_tech_debt

INCORPORATION_APPLICATION = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
CORRECTION = copy.deepcopy(CORRECTION_INCORPORATION)
CORRECTION['filing']['correction']['parties'][0]['roles'].append({
    "roleType": "Incorporator",
    "appointmentDate": "2018-01-01"
})


def test_valid_ia_correction(session):
    """Test that a valid IA without NR correction passes validation."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier)

    corrected_filing = factory_completed_filing(business, INCORPORATION_APPLICATION)

    f = copy.deepcopy(CORRECTION)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id

    del f['filing']['correction']['diff']
    del f['filing']['incorporationApplication']

    err = validate(business, f)

    if err:
        print(err.msg)

    # check that validation passed
    assert None is err


@pytest.mark.parametrize('new_name, legal_type, nr_legal_type, nr_type, err_msg', [
    ('legal_name-BC1234568', 'CP', 'CP', 'BECV', None),
    ('legal_name-BC1234567_Changed', 'BEN', 'CP', 'BECV',
     'Name Request legal type is not same as the business legal type.'),
    ('nr_not_approved', 'BEN', 'CP', 'BECV', 'Name Request is not approved.')
])
def test_nr_correction(session, new_name, legal_type, nr_legal_type, nr_type, err_msg):
    """Test that a valid NR correction passes validation."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier)

    INCORPORATION_APPLICATION['filing']['incorporationApplication']['nameRequest']['nrNumber'] = identifier
    INCORPORATION_APPLICATION['filing']['incorporationApplication']['nameRequest']['legalName'] = 'Test'

    corrected_filing = factory_completed_filing(business, INCORPORATION_APPLICATION)

    f = copy.deepcopy(CORRECTION)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id

    f['filing']['correction']['nameRequest']['nrNumber'] = identifier
    f['filing']['correction']['nameRequest']['legalName'] = new_name
    f['filing']['correction']['nameRequest']['legalType'] = legal_type
    f['filing']['business']['legalType'] = legal_type

    del f['filing']['correction']['diff']
    del f['filing']['incorporationApplication']

    nr_response_json = {
        'state': 'INPROGRESS' if new_name == 'nr_not_approved' else 'APPROVED',
        'expirationDate': '',
        'legalType': nr_legal_type,
        'names': [{
            'name': new_name,
            'state': 'INPROGRESS' if new_name == 'nr_not_approved' else 'APPROVED',
            'consumptionDate': ''
        }]
    }
    nr_response = MockResponse(nr_response_json)

    with patch.object(NameXService, 'query_nr_number', return_value=nr_response):
        err = validate(business, f)
        if err:
            print(err.msg)

    if not err_msg:
        assert None is err
    else:
        assert err
        assert HTTPStatus.BAD_REQUEST == err.code
        assert err.msg[0]['error'] == err_msg


@pytest.mark.parametrize('test_name, legal_type, err_msg', [
    ('valid_parties', 'BEN', None),
    ('valid_parties', 'BC', None),
    ('valid_parties', 'ULC', None),
    ('no_roles', 'BC', 'Must have a minimum of one completing party'),
    ('no_roles', 'ULC', 'Must have a minimum of one completing party'),
    ('no_roles', 'BEN', 'Must have a minimum of one completing party')
])
def test_parties_correction(session, test_name, legal_type, err_msg):
    """Test that a valid NR correction passes validation."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier)

    INCORPORATION_APPLICATION['filing']['incorporationApplication']['nameRequest']['nrNumber'] = identifier
    INCORPORATION_APPLICATION['filing']['incorporationApplication']['nameRequest']['legalName'] = 'Test'

    corrected_filing = factory_completed_filing(business, INCORPORATION_APPLICATION)

    f = copy.deepcopy(CORRECTION)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id

    f['filing']['correction']['nameRequest']['nrNumber'] = identifier
    f['filing']['correction']['nameRequest']['legalName'] = 'test'
    f['filing']['correction']['nameRequest']['legalType'] = legal_type
    f['filing']['business']['legalType'] = legal_type

    del f['filing']['correction']['diff']
    del f['filing']['incorporationApplication']

    if test_name == 'no_roles':
        f['filing']['correction']['parties'][0]['roles'] = []

    nr_response_json = {
        'state': 'APPROVED',
        'expirationDate': '',
        'legalType': legal_type,
        'names': [{
            'name': 'test',
            'state': 'APPROVED',
            'consumptionDate': ''
        }]
    }
    nr_response = MockResponse(nr_response_json)

    with patch.object(NameXService, 'query_nr_number', return_value=nr_response):
        err = validate(business, f)
        if err:
            print(err.msg)

    if not err_msg:
        assert None is err
    else:
        assert err
        assert HTTPStatus.BAD_REQUEST == err.code
        assert len(err.msg) == 3
        assert err.msg[0]['error'] == err_msg


@ pytest.mark.parametrize('test_name, json1, json2, expected', [
    ('no effective date',
     {},
     {'filing': {'header': {'effectiveDate': '1970-01-01T00:00:00+00:00'}}},
     None
     ),
    ('same effective date',
     {'filing': {'header': {'effectiveDate': '1970-01-01T00:00:00+00:00'}}},
     {'filing': {'header': {'effectiveDate': '1970-01-01T00:00:00+00:00'}}},
     None
     ),
    ('changed effective date',
     {'filing': {'header': {'effectiveDate': '2020-01-01T00:00:00+00:00'}}},
     {'filing': {'header': {'effectiveDate': '1970-01-01T00:00:00+00:00'}}},
     {'error': 'The effective date of a filing cannot be changed in a correction.'}
     ),
    # invalid dates should be trapped by the JSONSchema validator
])
def test_validate_correction_effective_date(test_name, json1, json2, expected):
    """Assert that a corrected effective date."""
    from legal_api.services.filings.validations.incorporation_application import validate_correction_effective_date

    err = validate_correction_effective_date(json1, json2)

    assert err == expected
