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

import pytest
from registry_schemas.example_data import ALTERATION_FILING_TEMPLATE

from legal_api.services import NameXService
from legal_api.services.filings import validate
from tests.unit.models import factory_business


ALTERATION_FILING = copy.deepcopy(ALTERATION_FILING_TEMPLATE)

TEST_DATA = [
    (False, '', 'BEN', '', True, 0),
    (True, 'legal_name-BC1234567_Changed', 'BEN', 'BEC', True, 0),
    (True, 'legal_name-BC1234567_Changed', 'BC', 'CCR', False, 1),
    (True, 'legal_name-BC1234568', 'CP', 'XCLP', False, 1),
    (True, 'legal_name-BC1234567_Changed', 'BEN', 'BECV', True, 0)
]


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data


@pytest.mark.parametrize('use_nr, new_name, legal_type, nr_type, should_pass, num_errors', TEST_DATA)
def test_alteration(session, use_nr, new_name, legal_type, nr_type, should_pass, num_errors):
    """Test that a valid Alteration without NR correction passes validation."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier)

    f = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    f['filing']['header']['identifier'] = identifier
    f['filing']['alteration']['business']['legalType'] = legal_type

    if use_nr:
        f['filing']['business']['identifier'] = identifier
        f['filing']['business']['legalName'] = 'legal_name-BC1234567'

        f['filing']['alteration']['nameRequest']['nrNumber'] = identifier
        f['filing']['alteration']['nameRequest']['legalName'] = new_name
        f['filing']['alteration']['nameRequest']['legalType'] = legal_type

        nr_json = {
            "state": "APPROVED",
            "expirationDate": "",
            "requestTypeCd": nr_type,
            "names": [{
                "name": new_name,
                "state": "APPROVED",
                "consumptionDate": ""
            }],
            "legalType": legal_type
        }

        nr_response = MockResponse(nr_json, 200)

        with patch.object(NameXService, 'query_nr_number', return_value=nr_response):
            err = validate(business, f)
    else:
        del f['filing']['alteration']['nameRequest']
        err = validate(business, f)

    if err:
        print(err.msg)

    if should_pass:
        # check that validation passed
        assert None is err
    else:
        # check that validation failed
        assert err
        assert HTTPStatus.BAD_REQUEST == err.code
        assert len(err.msg) == num_errors


@pytest.mark.parametrize('new_name, legal_type, nr_legal_type, nr_type, err_msg', [
    ('legal_name-BC1234568', 'CP', 'CP', 'BECV', None),
    ('legal_name-BC1234567_Changed', 'BEN', 'CP', 'BECV', 'Name Request legal type is not same as the business legal type.')
])
def test_alteration_name_change(session, new_name, legal_type, nr_legal_type, nr_type, err_msg):
    """Test that validator validates the alteration with legal type change."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier)

    f = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    f['filing']['header']['identifier'] = identifier
    f['filing']['alteration']['business']['legalType'] = legal_type


    f['filing']['business']['identifier'] = identifier
    f['filing']['business']['legalName'] = 'legal_name-BC1234567'

    f['filing']['alteration']['nameRequest']['nrNumber'] = identifier
    f['filing']['alteration']['nameRequest']['legalName'] = new_name
    f['filing']['alteration']['nameRequest']['legalType'] = legal_type

    nr_json = {
        "state": "APPROVED",
        "expirationDate": "",
        "requestTypeCd": nr_type,
        "names": [{
            "name": new_name,
            "state": "APPROVED",
            "consumptionDate": ""
        }],
        "legalType": nr_legal_type
    }

    nr_response = MockResponse(nr_json, 200)

    with patch.object(NameXService, 'query_nr_number', return_value=nr_response):
        err = validate(business, f)

    if err:
        print(err.msg)

    if not err_msg:
        # check that validation passed
        assert None is err
    else:
        # check that validation failed
        assert err
        assert HTTPStatus.BAD_REQUEST == err.code
        assert err.msg[0]['error'] == err_msg


@pytest.mark.parametrize(
    'test_name, should_pass, has_rights_or_restrictions, has_rights_or_restrictions_series, resolution_dates', [
        ('SUCCESS_has_rights_or_restrictions', True, True, False, ['2020-05-23']),
        ('SUCCESS', True, False, False, []),
        ('FAILURE', False, True, False, []),
        ('SUCCESS_series_has_rights_or_restrictions', True, False, True, ['2020-05-23']),
        ('SUCCESS_series', True, False, False, []),
        ('FAILURE_series', False, False, True, [])
    ])
def test_alteration_resolution_date(
        session, test_name, should_pass, has_rights_or_restrictions,
        has_rights_or_restrictions_series, resolution_dates):
    """Test resolution date in share structure."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier)

    f = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    f['filing']['header']['identifier'] = identifier
    del f['filing']['alteration']['nameRequest']

    f['filing']['alteration']['shareStructure']['shareClasses'][0]['hasRightsOrRestrictions'] = \
        has_rights_or_restrictions
    f['filing']['alteration']['shareStructure']['shareClasses'][0]['series'][0]['hasRightsOrRestrictions'] = \
        has_rights_or_restrictions_series
    f['filing']['alteration']['shareStructure']['resolutionDates'] = resolution_dates

    err = validate(business, f)

    if err:
        print(err.msg)

    if should_pass:
        # check that validation passed
        assert None is err
    else:
        # check that validation failed
        assert err
        assert HTTPStatus.BAD_REQUEST == err.code


def test_alteration_share_classes_optional(session):
    """Assert shareClasses is optional in alteration."""
    identifier = 'BC1234567'
    business = factory_business(identifier)

    f = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    f['filing']['header']['identifier'] = identifier
    del f['filing']['alteration']['nameRequest']
    del f['filing']['alteration']['shareStructure']['shareClasses']
    f['filing']['alteration']['shareStructure']['resolutionDates'] = ['2020-05-23']

    err = validate(business, f)
    assert None is err


@pytest.mark.parametrize(
    'test_status, should_pass, rules_file_key, rules_file_name', [
        ('SUCCESS', True, "rulesFileKey", "rulesFileName"),
        ('FAILURE', False, None, "rulesFileName"),
        ('FAILURE', False, "rulesFileKey", None),
    ])
def test_rules_change(session, test_status, should_pass, rules_file_key, rules_file_name):
    """Assert riles is optional in alteration."""
    identifier = 'CP1234567'
    business = factory_business(identifier)

    f = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    f['filing']['header']['identifier'] = identifier
    del f['filing']['alteration']['nameRequest']

    if rules_file_key:
        f['filing']['alteration']['rulesFileKey'] = rules_file_key
    if rules_file_name:
        f['filing']['alteration']['rulesFileName'] = rules_file_name

    err = validate(business, f)
    
    if err:
        print(err.msg)

    if should_pass:
        # check that validation passed
        assert None is err
    else:
        # check that validation failed
        assert err
        assert HTTPStatus.BAD_REQUEST == err.code

@pytest.mark.parametrize(
    'test_status, should_pass, memorandum_file_key, memorandum_file_name', [
        ('SUCCESS', True, "memorandumFileKey", "memorandumFileName"),
        ('FAILURE', False, None, "memorandumFileName"),
        ('FAILURE', False, "memorandumFileKey", None),
    ])
def test_memorandum_change(session, test_status, should_pass, memorandum_file_key, memorandum_file_name):
    """Assert riles is optional in alteration."""
    identifier = 'CP1234567'
    business = factory_business(identifier)

    f = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    f['filing']['header']['identifier'] = identifier
    del f['filing']['alteration']['nameRequest']

    if memorandum_file_key:
        f['filing']['alteration']['memorandumFileKey'] = memorandum_file_key
    if memorandum_file_name:
        f['filing']['alteration']['memorandumFileName'] = memorandum_file_name

    err = validate(business, f)
    
    if err:
        print(err.msg)

    if should_pass:
        # check that validation passed
        assert None is err
    else:
        # check that validation failed
        assert err
        assert HTTPStatus.BAD_REQUEST == err.code
