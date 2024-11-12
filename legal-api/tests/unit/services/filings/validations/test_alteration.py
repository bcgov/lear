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
from reportlab.lib.pagesizes import letter

from legal_api.models import Business
from legal_api.services import flags, NameXService
from legal_api.services.filings import validate
from tests.unit.models import factory_business
from tests.unit.services.filings.test_utils import _upload_file
from tests.unit.services.filings.validations import lists_are_equal


ALTERATION_FILING = copy.deepcopy(ALTERATION_FILING_TEMPLATE)


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data


@pytest.mark.parametrize('use_nr, new_name, legal_type, new_legal_type, nr_type, should_pass, num_errors', [
    (False, '', 'CP', 'CP', '', True, 0),
    (False, '', 'CP', 'BEN', '', False, 1),
    (False, '', 'CP', 'BC', '', False, 1),
    (False, '', 'CP', 'ULC', '', False, 1),
    (False, '', 'CP', 'CC', '', False, 1),
    (False, '', 'CP', 'C', '', False, 1),
    (False, '', 'CP', 'CBEN', '', False, 1),
    (False, '', 'CP', 'CUL', '', False, 1),
    (False, '', 'CP', 'CCC', '', False, 1),

    (False, '', 'BEN', 'BEN', '', True, 0),
    (False, '', 'BEN', 'BC', '', True, 0),
    (False, '', 'BEN', 'ULC', '', False, 1),
    (False, '', 'BEN', 'CC', '', True, 1),
    (False, '', 'BEN', 'CP', '', False, 1),
    (False, '', 'BEN', 'C', '', False, 1),
    (False, '', 'BEN', 'CBEN', '', False, 1),
    (False, '', 'BEN', 'CUL', '', False, 1),
    (False, '', 'BEN', 'CCC', '', False, 1),

    (False, '', 'BC', 'BC', '', True, 0),
    (False, '', 'BC', 'BEN', '', True, 0),
    (False, '', 'BC', 'ULC', '', True, 0),
    (False, '', 'BC', 'CC', '', True, 0),
    (False, '', 'BC', 'CP', '', False, 1),
    (False, '', 'BC', 'C', '', False, 1),
    (False, '', 'BC', 'CBEN', '', False, 1),
    (False, '', 'BC', 'CUL', '', False, 1),
    (False, '', 'BC', 'CCC', '', False, 1),

    (False, '', 'ULC', 'ULC', '', True, 0),
    (False, '', 'ULC', 'BC', '', True, 0),
    (False, '', 'ULC', 'BEN', '', True, 0),
    (False, '', 'ULC', 'CC', '', False, 1),
    (False, '', 'ULC', 'CP', '', False, 1),
    (False, '', 'ULC', 'C', '', False, 1),
    (False, '', 'ULC', 'CBEN', '', False, 1),
    (False, '', 'ULC', 'CUL', '', False, 1),
    (False, '', 'ULC', 'CCC', '', False, 1),

    (False, '', 'CC', 'CC', '', True, 0),
    (False, '', 'CC', 'BEN', '', False, 1),
    (False, '', 'CC', 'BC', '', False, 1),
    (False, '', 'CC', 'ULC', '', False, 1),
    (False, '', 'CC', 'CP', '', False, 1),
    (False, '', 'CC', 'C', '', False, 1),
    (False, '', 'CC', 'CBEN', '', False, 1),
    (False, '', 'CC', 'CUL', '', False, 1),
    (False, '', 'CC', 'CCC', '', False, 1),

    (False, '', 'CBEN', 'CBEN', '', True, 0),
    (False, '', 'CBEN', 'C', '', True, 0),
    (False, '', 'CBEN', 'CUL', '', False, 1),
    (False, '', 'CBEN', 'CCC', '', True, 1),
    (False, '', 'CBEN', 'BEN', '', False, 1),
    (False, '', 'CBEN', 'BC', '', False, 1),
    (False, '', 'CBEN', 'ULC', '', False, 1),
    (False, '', 'CBEN', 'CC', '', False, 1),
    (False, '', 'CBEN', 'CP', '', False, 1),

    (False, '', 'C', 'C', '', True, 0),
    (False, '', 'C', 'CBEN', '', True, 0),
    (False, '', 'C', 'CUL', '', True, 0),
    (False, '', 'C', 'CCC', '', True, 0),
    (False, '', 'C', 'BC', '', False, 1),
    (False, '', 'C', 'BEN', '', False, 1),
    (False, '', 'C', 'ULC', '', False, 1),
    (False, '', 'C', 'CC', '', False, 1),
    (False, '', 'C', 'CP', '', False, 1),

    (False, '', 'CUL', 'CUL', '', True, 0),
    (False, '', 'CUL', 'C', '', True, 0),
    (False, '', 'CUL', 'CBEN', '', True, 0),
    (False, '', 'CUL', 'CCC', '', False, 1),
    (False, '', 'CUL', 'ULC', '', False, 1),
    (False, '', 'CUL', 'BC', '', False, 1),
    (False, '', 'CUL', 'BEN', '', False, 1),
    (False, '', 'CUL', 'CC', '', False, 1),
    (False, '', 'CUL', 'CP', '', False, 1),

    (False, '', 'CCC', 'CCC', '', True, 0),
    (False, '', 'CCC', 'CBEN', '', False, 1),
    (False, '', 'CCC', 'C', '', False, 1),
    (False, '', 'CCC', 'CUL', '', False, 1),
    (False, '', 'CCC', 'CC', '', False, 1),
    (False, '', 'CCC', 'BEN', '', False, 1),
    (False, '', 'CCC', 'BC', '', False, 1),
    (False, '', 'CCC', 'ULC', '', False, 1),
    (False, '', 'CCC', 'CP', '', False, 1),

    (True, 'legal_name-BC1234567_Changed', 'BEN', 'BEN', 'BEC', True, 0),
    (True, 'legal_name-BC1234567_Changed', 'BC', 'BC', 'CCR', True, 0),
    (True, 'legal_name-BC1234568', 'CP', 'CP', 'XCLP', False, 1),
    (True, 'legal_name-BC1234567_Changed', 'BEN', 'BEN', 'BECV', True, 0)
])
def test_alteration(session, use_nr, new_name, legal_type, new_legal_type, nr_type, should_pass, num_errors):
    """Test that a valid Alteration without NR correction passes validation."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type=legal_type)

    f = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    f['filing']['header']['identifier'] = identifier
    f['filing']['business']['legalType'] = legal_type
    f['filing']['alteration']['business']['legalType'] = new_legal_type

    if use_nr:
        f['filing']['business']['identifier'] = identifier
        f['filing']['business']['legalName'] = 'legal_name-BC1234567'
        f['filing']['business']['legalType'] = legal_type

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
        with patch.object(flags, 'is_on', return_value=False):
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


@pytest.mark.parametrize('test_name, legal_type, new_legal_type, err_msg', [
    ('numbered_to_numbered', 'BC', 'BC', None),
    ('numbered_to_numbered', 'BC', 'BEN', None),
    ('numbered_to_numbered', 'BC', 'CC', None),
    ('numbered_to_numbered', 'BC', 'ULC', None),
    ('numbered_to_numbered', 'BEN', 'BEN', None),
    ('numbered_to_numbered', 'BEN', 'BC', None),
    ('numbered_to_numbered', 'ULC', 'ULC', None),
    ('numbered_to_numbered', 'ULC', 'BC', None),
    ('numbered_to_numbered', 'ULC', 'BEN', None),
    ('numbered_to_numbered', 'CC', 'CC', None),
    ('numbered_to_numbered_invalid', 'CC', 'CC', 'Unexpected legal name.'),
    ('named_to_numbered', 'BC', 'BC', None),
    ('named_to_numbered', 'BEN', 'BEN', None),
    ('named_to_numbered', 'CC', 'CC', None),
    ('named_to_numbered', 'ULC', 'ULC', None),
])
def test_validate_numbered_name(session, test_name, legal_type, new_legal_type, err_msg):
    """Test that validator validates the alteration with legal type change."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type=legal_type)
    if test_name in ['numbered_to_numbered', 'numbered_to_numbered_invalid']:
        business.legal_name = Business.generate_numbered_legal_name(legal_type, identifier)
    business.save()

    f = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    f['filing']['header']['identifier'] = identifier
    if not new_legal_type:
        new_legal_type = legal_type
    f['filing']['alteration']['business']['legalType'] = new_legal_type

    f['filing']['business']['identifier'] = identifier
    f['filing']['business']['legalName'] = 'legal_name-BC1234567'

    del f['filing']['alteration']['nameRequest']['nrNumber']
    if test_name == 'numbered_to_numbered_invalid':
        f['filing']['alteration']['nameRequest']['legalName'] = 'zxy'
    else:
        f['filing']['alteration']['nameRequest']['legalName'] = Business.generate_numbered_legal_name(
            new_legal_type,
            identifier)
    f['filing']['alteration']['nameRequest']['legalType'] = legal_type

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


@pytest.mark.parametrize('new_name, legal_type, nr_legal_type, nr_type, err_msg', [
    ('legal_name-BC1234568', 'CP', 'CP', 'BECV', None),
    ('legal_name-BC1234567_Changed', 'BEN', 'ULC', 'BECV', 'Name Request legal type is not same as the business legal type.')
])
def test_validate_nr_type(session, new_name, legal_type, nr_legal_type, nr_type, err_msg):
    """Test that validator validates the alteration with legal type change."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type=legal_type)

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
    del f['filing']['alteration']['business']['legalType']

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
    del f['filing']['alteration']['business']['legalType']
    del f['filing']['alteration']['shareStructure']['shareClasses']
    f['filing']['alteration']['shareStructure']['resolutionDates'] = ['2020-05-23']

    err = validate(business, f)
    assert None is err


rules_file_key_path = '/filing/alteration/rulesFileKey'
memorandum_file_key_path = '/filing/alteration/memorandumFileKey'


@pytest.mark.parametrize(
    'test_name, key, scenario, expected_code, expected_msg',
    [
        ('SUCCESS', 'rulesFileKey', 'success', None, None),
        ('SUCCESS', 'memorandumFileKey', 'success', None, None),
        ('FAIL_INVALID_RULES_FILE_KEY', 'rulesFileKey', 'failRules',
            HTTPStatus.BAD_REQUEST, [{
                'error': 'Invalid file.', 'path': rules_file_key_path
            }]),
        ('FAIL_INVALID_MEMORANDUM_FILE_KEY', 'memorandumFileKey', 'failMemorandum',
            HTTPStatus.BAD_REQUEST, [{
                'error': 'Invalid file.', 'path': memorandum_file_key_path
            }]),
        ('FAIL_INVALID_RULES_FILE_KEY', 'rulesFileKey', 'invalidRulesSize',
            HTTPStatus.BAD_REQUEST, [{
                'error': 'Document must be set to fit onto 8.5” x 11” letter-size paper.',
                'path': rules_file_key_path
            }]),
        ('FAIL_INVALID_RULES_FILE_KEY', 'rulesFileKey', 'invalidMemorandumSize',
            HTTPStatus.BAD_REQUEST, [{
                'error': 'Document must be set to fit onto 8.5” x 11” letter-size paper.',
                'path': memorandum_file_key_path
            }]),
    ])
def test_validate_cooperative_documents(session, mocker, minio_server, test_name, key, scenario, expected_code,
                                        expected_msg):
    """Assert that validator validates cooperative documents correctly."""
    identifier = 'CP1234567'
    business = factory_business(identifier)

    filing_json = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    filing_json['filing']['header']['identifier'] = identifier
    del filing_json['filing']['alteration']['nameRequest']
    del filing_json['filing']['alteration']['business']['legalType']

    # Mock upload file for test scenarios
    if scenario == 'success':
        filing_json['filing']['alteration']['rulesFileKey'] = _upload_file(letter, invalid=False)
        filing_json['filing']['alteration']['memorandumFileKey'] = _upload_file(letter, invalid=False)
    if scenario == 'failRules':
        filing_json['filing']['alteration']['rulesFileKey'] = scenario
        filing_json['filing']['alteration']['memorandumFileKey'] = _upload_file(letter, invalid=False)
    if scenario == 'failMemorandum':
        filing_json['filing']['alteration']['rulesFileKey'] = _upload_file(letter, invalid=False)
        filing_json['filing']['alteration']['memorandumFileKey'] = scenario
    if scenario == 'invalidRulesSize':
        filing_json['filing']['alteration']['rulesFileKey'] = _upload_file(letter, invalid=True)
        filing_json['filing']['alteration']['memorandumFileKey'] = _upload_file(letter, invalid=False)
    if scenario == 'invalidMemorandumSize':
        filing_json['filing']['alteration']['rulesFileKey'] = _upload_file(letter, invalid=False)
        filing_json['filing']['alteration']['memorandumFileKey'] = _upload_file(letter, invalid=True)

    # perform test
    err = validate(business, filing_json)

    # validate outcomes
    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None
