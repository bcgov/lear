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
from unittest.mock import MagicMock, create_autospec, patch
from datetime import date
from flask import g
from legal_api.errors import Error
from legal_api.services.authz import PUBLIC_USER
from legal_api.services.permissions import ListActionsPermissionsAllowed, PermissionService
import pytest
from freezegun import freeze_time
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

class MockDirector:
    def __init__(self, cessation_date=None):
        self.cessation_date = cessation_date

def create_mock_directors(count=3):
    """Return a list of mock directors for tests."""
    return [MockDirector() for _ in range(count)]  


@pytest.mark.parametrize('use_nr, new_name, legal_type, new_legal_type, nr_type, mock_directors, should_pass, num_errors', [
    (False, '', 'CP', 'CP', '', True, True, 0),
    (False, '', 'CP', 'BEN', '', True, False, 1),
    (False, '', 'CP', 'BC', '', True, False, 1),
    (False, '', 'CP', 'ULC', '', True, False, 1),
    (False, '', 'CP', 'CC', '', True, False, 1),
    (False, '', 'CP', 'C', '', True, False, 1),
    (False, '', 'CP', 'CBEN', '', True, False, 1),
    (False, '', 'CP', 'CUL', '', True, False, 1),
    (False, '', 'CP', 'CCC', '', True, False, 1),

    (False, '', 'BEN', 'BEN', '', True, True, 0),
    (False, '', 'BEN', 'BC', '', True, True, 0),
    (False, '', 'BEN', 'ULC', '', True, False, 1),
    (False, '', 'BEN', 'CC', '', True, True, 1),
    (False, '', 'BEN', 'CP', '', True, False, 1),
    (False, '', 'BEN', 'C', '', True, False, 1),
    (False, '', 'BEN', 'CBEN', '', True, False, 1),
    (False, '', 'BEN', 'CUL', '', True, False, 1),
    (False, '', 'BEN', 'CCC', '', True, False, 1),

    (False, '', 'BC', 'BC', '', True, True, 0),
    (False, '', 'BC', 'BEN', '', True, True, 0),
    (False, '', 'BC', 'ULC', '', True, True, 0),
    (False, '', 'BC', 'CC', '', True, True, 0),
    (False, '', 'BC', 'CP', '', True, False, 1),
    (False, '', 'BC', 'C', '', True, False, 1),
    (False, '', 'BC', 'CBEN', '', True, False, 1),
    (False, '', 'BC', 'CUL', '', True, False, 1),
    (False, '', 'BC', 'CCC', '', True, False, 1),

    (False, '', 'ULC', 'ULC', '', True, True, 0),
    (False, '', 'ULC', 'BC', '', True, True, 0),
    (False, '', 'ULC', 'BEN', '', True, True, 0),
    (False, '', 'ULC', 'CC', '', True, False, 1),
    (False, '', 'ULC', 'CP', '', True, False, 1),
    (False, '', 'ULC', 'C', '', True, False, 1),
    (False, '', 'ULC', 'CBEN', '', True, False, 1),
    (False, '', 'ULC', 'CUL', '', True, False, 1),
    (False, '', 'ULC', 'CCC', '', True, False, 1),

    (False, '', 'CC', 'CC', '', True, True, 0),
    (False, '', 'CC', 'BEN', '', True, False, 1),
    (False, '', 'CC', 'BC', '', True, False, 1),
    (False, '', 'CC', 'ULC', '', True, False, 1),
    (False, '', 'CC', 'CP', '', True, False, 1),
    (False, '', 'CC', 'C', '', True, False, 1),
    (False, '', 'CC', 'CBEN', '', True, False, 1),
    (False, '', 'CC', 'CUL', '', True, False, 1),
    (False, '', 'CC', 'CCC', '', True, False, 1),

    (False, '', 'CBEN', 'CBEN', '', True, True, 0),
    (False, '', 'CBEN', 'C', '', True, True, 0),
    (False, '', 'CBEN', 'CUL', '', True, False, 1),
    (False, '', 'CBEN', 'CCC', '', True, True, 1),
    (False, '', 'CBEN', 'BEN', '', True, False, 1),
    (False, '', 'CBEN', 'BC', '', True, False, 1),
    (False, '', 'CBEN', 'ULC', '', True, False, 1),
    (False, '', 'CBEN', 'CC', '', True, False, 1),
    (False, '', 'CBEN', 'CP', '', True, False, 1),

    (False, '', 'C', 'C', '', True, True, 0),
    (False, '', 'C', 'CBEN', '', True, True, 0),
    (False, '', 'C', 'CUL', '', True, True, 0),
    (False, '', 'C', 'CCC', '', True, True, 0),
    (False, '', 'C', 'BC', '', True, False, 1),
    (False, '', 'C', 'BEN', '', True, False, 1),
    (False, '', 'C', 'ULC', '', True, False, 1),
    (False, '', 'C', 'CC', '', True, False, 1),
    (False, '', 'C', 'CP', '', True, False, 1),

    (False, '', 'CUL', 'CUL', '', True, True, 0),
    (False, '', 'CUL', 'C', '', True, True, 0),
    (False, '', 'CUL', 'CBEN', '', True, True, 0),
    (False, '', 'CUL', 'CCC', '', True, False, 1),
    (False, '', 'CUL', 'ULC', '', True, False, 1),
    (False, '', 'CUL', 'BC', '', True, False, 1),
    (False, '', 'CUL', 'BEN', '', True, False, 1),
    (False, '', 'CUL', 'CC', '', True, False, 1),
    (False, '', 'CUL', 'CP', '', True, False, 1),

    (False, '', 'CCC', 'CCC', '', True, True, 0),
    (False, '', 'CCC', 'CBEN', '', True, False, 1),
    (False, '', 'CCC', 'C', '', True, False, 1),
    (False, '', 'CCC', 'CUL', '', True, False, 1),
    (False, '', 'CCC', 'CC', '', True, False, 1),
    (False, '', 'CCC', 'BEN', '', True, False, 1),
    (False, '', 'CCC', 'BC', '', True, False, 1),
    (False, '', 'CCC', 'ULC', '', True, False, 1),
    (False, '', 'CCC', 'CP', '', True, False, 1),

    # check minimum directors validation
    (False, '', 'BC', 'CC', '', False, False, 1),
    (False, '', 'CBEN', 'CCC', '', False, False, 1),  

    # use_nr, new_name, legal_type, new_legal_type, nr_type, should_pass, num_errors

    # CHG (name change) NR type code tests
    (True, 'legal_name-BC1234567_Changed', 'BEN', 'BEN', 'BEC', True, True, 0),
    (True, 'legal_name-BC1234567_Changed', 'CC', 'CC', 'CCC', True, True, 0),
    (True, 'legal_name-BC1234567_Changed', 'BC', 'BC', 'CCR', True, True, 0),
    (True, 'legal_name-BC1234567_Changed', 'ULC', 'ULC', 'CUL', True, True, 0),
    (True, 'legal_name-BC1234567_Changed', 'CBEN', 'CBEN', 'BEC', True, True, 0),
    (True, 'legal_name-BC1234567_Changed', 'CCC', 'CCC', 'CCC', True, True, 0),
    (True, 'legal_name-BC1234567_Changed', 'C', 'C', 'CCR', True, True, 0),
    (True, 'legal_name-BC1234567_Changed', 'CUL', 'CUL', 'CUL', True, True, 0),

    (True, 'legal_name-CP1234567_Changed', 'CP', 'CP', 'CCP', True, True, 0),
    (True, 'legal_name-CP1234567_Changed', 'CP', 'CP', 'XCLP', True, False, 1),

    # CNV (conversion) NR type code tests
    (True, 'legal_name-BC1234567_Changed', 'BC', 'BEN', 'BECV', True, True, 0),
    (True, 'legal_name-BC1234567_Changed', 'BC', 'CC', 'CCV', True, True, 0),
    (True, 'legal_name-BC1234567_Changed', 'BC', 'ULC', 'UC', True, True, 0),
    (True, 'legal_name-BC1234567_Changed', 'BEN', 'BC', 'BECR', True, True, 0),
    (True, 'legal_name-BC1234567_Changed', 'BEN', 'CC', 'BECC', True, True, 0),
    (True, 'legal_name-BC1234567_Changed', 'BEN', 'ULC', 'BECC', True, False, 1),
    (True, 'legal_name-BC1234567_Changed', 'ULC', 'BC', 'ULCB', True, True, 0),
    (True, 'legal_name-BC1234567_Changed', 'ULC', 'BEN', 'ULBE', True, True, 0),
    (True, 'legal_name-BC1234567_Changed', 'ULC', 'CC', 'ULCC', True, False, 2),
    (True, 'legal_name-BC1234567_Changed', 'CC', 'BC', 'ULCC', True, False, 2),
    (True, 'legal_name-BC1234567_Changed', 'CC', 'BEN', 'ULCC', True, False, 2),
    (True, 'legal_name-BC1234567_Changed', 'CC', 'ULC', 'ULCC', True, False, 2),
    (True, 'legal_name-BC1234567_Changed', 'C', 'CBEN', 'BECV', True, True, 0),
    (True, 'legal_name-BC1234567_Changed', 'C', 'CCC', 'CCV', True, True, 0),
    (True, 'legal_name-BC1234567_Changed', 'C', 'CUL', 'UC', True, True, 0),
    (True, 'legal_name-BC1234567_Changed', 'CBEN', 'C', 'BECR', True, True, 0),
    (True, 'legal_name-BC1234567_Changed', 'CBEN', 'CCC', 'BECC', True, True, 0),
    (True, 'legal_name-BC1234567_Changed', 'CBEN', 'CUL', 'BECC', True, False, 1),
    (True, 'legal_name-BC1234567_Changed', 'CUL', 'C', 'ULCB', True, True, 0),
    (True, 'legal_name-BC1234567_Changed', 'CUL', 'CBEN', 'ULBE', True, True, 0),
    (True, 'legal_name-BC1234567_Changed', 'CUL', 'CCC', 'ULCC', True, False, 2),
    (True, 'legal_name-BC1234567_Changed', 'CCC', 'C', 'ULCC', True, False, 2),
    (True, 'legal_name-BC1234567_Changed', 'CCC', 'CBEN', 'ULCC', True, False, 2),
    (True, 'legal_name-BC1234567_Changed', 'CCC', 'CUL', 'ULCC', True, False, 2)
])
@patch.object(PermissionService, 'check_user_permission', MagicMock(return_value=None))
@patch('legal_api.models.PartyRole.get_parties_by_role')
def test_alteration(mock_get_parties, session, use_nr, new_name, legal_type, new_legal_type, nr_type, mock_directors, should_pass, num_errors):
    """Test that a valid Alteration without NR correction passes validation."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type=legal_type)

    f = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    f['filing']['header']['identifier'] = identifier
    f['filing']['business']['legalType'] = legal_type
    f['filing']['alteration']['business']['legalType'] = new_legal_type

    # mock directors
    if mock_directors:
        mock_get_parties.return_value = create_mock_directors(3)
    else:
        mock_get_parties.return_value = []

    if use_nr:
        f['filing']['business']['identifier'] = identifier
        f['filing']['business']['legalName'] = 'legal_name-BC1234567'
        f['filing']['business']['legalType'] = legal_type

        f['filing']['alteration']['nameRequest']['nrNumber'] = identifier
        f['filing']['alteration']['nameRequest']['legalName'] = new_name
        f['filing']['alteration']['nameRequest']['legalType'] = new_legal_type

        nr_json = {
            "state": "APPROVED",
            "expirationDate": "",
            "requestTypeCd": nr_type,
            "names": [{
                "name": new_name,
                "state": "APPROVED",
                "consumptionDate": ""
            }],
            "legalType": new_legal_type
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

        # check for minimum directors error message
        if (new_legal_type in [Business.LegalTypes.BC_CCC.value, Business.LegalTypes.CCC_CONTINUE_IN.value,
                               Business.LegalTypes.COOP.value] and not mock_directors):
            assert 'Must have a minimum of three directors. File a change of director filing first.' in [e['error'] for e in err.msg]


@pytest.mark.parametrize('test_name, legal_type, new_legal_type, err_msg', [
    ('numbered_to_numbered', 'BC', 'BC', None),
    ('numbered_to_numbered', 'BC', 'BEN', None),
    ('numbered_to_numbered', 'BC', 'CC', None),
    ('numbered_to_numbered', 'BC', 'ULC', None),
    ('numbered_to_numbered', 'BEN', 'BEN', None),
    ('numbered_to_numbered', 'BEN', 'BC', None),
    ('numbered_to_numbered', 'BEN', 'CC', None),
    ('numbered_to_numbered', 'BEN', 'ULC', 'BC Benefit Company can only change to'),
    ('numbered_to_numbered', 'ULC', 'ULC', None),
    ('numbered_to_numbered', 'ULC', 'BC', None),
    ('numbered_to_numbered', 'ULC', 'BEN', None),
    ('numbered_to_numbered', 'ULC', 'CC', 'BC Unlimited Liability Company can only change to'),
    ('numbered_to_numbered', 'CC', 'CC', None),
    ('numbered_to_numbered_invalid', 'CC', 'CC', 'Unexpected legal name.'),
    ('numbered_to_numbered', 'C', 'C', None),
    ('numbered_to_numbered', 'C', 'CBEN', None),
    ('numbered_to_numbered', 'C', 'CCC', None),
    ('numbered_to_numbered', 'C', 'CUL', None),
    ('numbered_to_numbered', 'CBEN', 'CBEN', None),
    ('numbered_to_numbered', 'CBEN', 'C', None),
    ('numbered_to_numbered', 'CBEN', 'CCC', None),
    ('numbered_to_numbered', 'CBEN', 'CUL', 'BC Benefit Company can only change to'),
    ('numbered_to_numbered', 'CUL', 'CUL', None),
    ('numbered_to_numbered', 'CUL', 'C', None),
    ('numbered_to_numbered', 'CUL', 'CBEN', None),
    ('numbered_to_numbered', 'CUL', 'CCC', 'BC Unlimited Liability Company can only change to'),
    ('numbered_to_numbered', 'CCC', 'CCC', None),
    ('numbered_to_numbered_invalid', 'CCC', 'CCC', 'Unexpected legal name.'),

    ('named_to_numbered', 'BC', 'BC', None),
    ('named_to_numbered', 'BEN', 'BEN', None),
    ('named_to_numbered', 'CC', 'CC', None),
    ('named_to_numbered', 'ULC', 'ULC', None),
    ('named_to_numbered', 'C', 'C', None),
    ('named_to_numbered', 'CBEN', 'CBEN', None),
    ('named_to_numbered', 'CCC', 'CCC', None),
    ('named_to_numbered', 'CUL', 'CUL', None),
])
@patch.object(PermissionService, 'check_user_permission', MagicMock(return_value=None))
@patch('legal_api.models.PartyRole.get_parties_by_role')
def test_validate_numbered_name(mock_get_parties, session, test_name, legal_type, new_legal_type, err_msg):
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

    mock_get_parties.return_value = create_mock_directors(3)

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
        assert err_msg in err.msg[0]['error']


@pytest.mark.parametrize('new_name, legal_type, nr_legal_type, nr_type, err_msg', [
    ('legal_name-BC1234568', 'CP', 'CP', 'BECV', None),
    ('legal_name-BC1234567_Changed', 'BEN', 'ULC', 'BECV', 'Name Request legal type is not same as the business legal type.')
])
@patch.object(PermissionService, 'check_user_permission', MagicMock(return_value=None))
@patch('legal_api.models.PartyRole.get_parties_by_role')
def test_validate_nr_type(mock_get_parties, session, new_name, legal_type, nr_legal_type, nr_type, err_msg):
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

    mock_get_parties.return_value = create_mock_directors(3)

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
@patch.object(PermissionService, 'check_user_permission', MagicMock(return_value=None))
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

@patch.object(PermissionService, 'check_user_permission', MagicMock(return_value=None))
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
@patch.object(PermissionService, 'check_user_permission', MagicMock(return_value=None))
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


@pytest.mark.parametrize(
    'legal_type, new_legal_type, has_rights_or_restrictions, has_series, should_pass',
    [
        ('BC', 'BC', False, True, False),
        ('BC', 'BC', False, False, True),
        ('BC', 'BC', True, True, True),
        ('BC', 'BC', True, False, True),
        ('BC', 'BEN', False, True, False),
        ('BC', 'BEN', False, False, True),
        ('BC', 'BEN', True, True, True),
        ('BC', 'BEN', True, False, True),
        ('BC', 'ULC', False, True, False),
        ('BC', 'ULC', False, False, True),
        ('BC', 'ULC', True, True, True),
        ('BC', 'ULC', True, False, True),
        ('BC', 'CC', False, True, False),
        ('BC', 'CC', False, False, True),
        ('BC', 'CC', True, True, True),
        ('BC', 'CC', True, False, True),

        ('BEN', 'BEN', False, True, False),
        ('BEN', 'BEN', False, False, True),
        ('BEN', 'BEN', True, True, True),
        ('BEN', 'BEN', True, False, True),
        ('BEN', 'BC', False, True, False),
        ('BEN', 'BC', False, False, True),
        ('BEN', 'BC', True, True, True),
        ('BEN', 'BC', True, False, True),
        ('BEN', 'CC', False, True, False),
        ('BEN', 'CC', False, False, True),
        ('BEN', 'CC', True, True, True),
        ('BEN', 'CC', True, False, True),

        ('ULC', 'ULC', False, True, False),
        ('ULC', 'ULC', False, False, True),
        ('ULC', 'ULC', True, True, True),
        ('ULC', 'ULC', True, False, True),
        ('ULC', 'BC', False, True, False),
        ('ULC', 'BC', False, False, True),
        ('ULC', 'BC', True, True, True),
        ('ULC', 'BC', True, False, True),
        ('ULC', 'BEN', False, True, False),
        ('ULC', 'BEN', False, False, True),
        ('ULC', 'BEN', True, True, True),
        ('ULC', 'BEN', True, False, True),

        ('CC', 'CC', False, True, False),
        ('CC', 'CC', False, False, True),
        ('CC', 'CC', True, True, True),
        ('CC', 'CC', True, False, True),

        ('CBEN', 'CBEN', False, True, False),
        ('CBEN', 'CBEN', False, False, True),
        ('CBEN', 'CBEN', True, True, True),
        ('CBEN', 'CBEN', True, False, True),
        ('CBEN', 'C', False, True, False),
        ('CBEN', 'C', False, False, True),
        ('CBEN', 'C', True, True, True),
        ('CBEN', 'C', True, False, True),
        ('CBEN', 'CCC', False, True, False),
        ('CBEN', 'CCC', False, False, True),
        ('CBEN', 'CCC', True, True, True),
        ('CBEN', 'CCC', True, False, True),

        ('C', 'C', False, True, False),
        ('C', 'C', False, False, True),
        ('C', 'C', True, True, True),
        ('C', 'C', True, False, True),
        ('C', 'CBEN', False, True, False),
        ('C', 'CBEN', False, False, True),
        ('C', 'CBEN', True, True, True),
        ('C', 'CBEN', True, False, True),
        ('C', 'CUL', False, True, False),
        ('C', 'CUL', False, False, True),
        ('C', 'CUL', True, True, True),
        ('C', 'CUL', True, False, True),

        ('C', 'CCC', False, True, False),
        ('C', 'CCC', False, False, True),
        ('C', 'CCC', True, True, True),
        ('C', 'CCC', True, False, True),

        ('CUL', 'CUL', False, True, False),
        ('CUL', 'CUL', False, False, True),
        ('CUL', 'CUL', True, True, True),
        ('CUL', 'CUL', True, False, True),
        ('CUL', 'C', False, True, False),
        ('CUL', 'C', False, False, True),
        ('CUL', 'C', True, True, True),
        ('CUL', 'C', True, False, True),
        ('CUL', 'CBEN', False, True, False),
        ('CUL', 'CBEN', False, False, True),
        ('CUL', 'CBEN', True, True, True),
        ('CUL', 'CBEN', True, False, True),

        ('CCC', 'CCC', False, True, False),
        ('CCC', 'CCC', False, False, True),
        ('CCC', 'CCC', True, True, True),
        ('CCC', 'CCC', True, False, True),
    ]
)
@patch.object(PermissionService, 'check_user_permission', MagicMock(return_value=None))
@patch('legal_api.models.PartyRole.get_parties_by_role')
def test_alteration_share_class_series_validation(mock_get_parties, session, legal_type, new_legal_type, has_rights_or_restrictions,
                                                  has_series, should_pass):
    """Test corps-type share class/series validation in alteration."""
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type=legal_type)

    filing = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    filing['filing']['header']['identifier'] = identifier
    filing['filing']['business']['legalType'] = legal_type
    filing['filing']['alteration']['business']['legalType'] = new_legal_type

    mock_get_parties.return_value = create_mock_directors(3)

    del filing['filing']['alteration']['nameRequest']

    if 'shareStructure' in filing['filing']['alteration']:
        for share_class in filing['filing']['alteration']['shareStructure']['shareClasses']:
            share_class['hasRightsOrRestrictions'] = has_rights_or_restrictions
            if not has_rights_or_restrictions:
                if not has_series:
                    share_class.pop('series', None)

    err = validate(business, filing)

    if should_pass:
        assert err is None
    else:
        assert err
        assert any('cannot have series when hasRightsOrRestrictions is false' in msg['error'] for msg in err.msg)

#setup
now = date(2020, 9, 17)

@pytest.mark.parametrize(
    'test_name, effective_date , expected_code, expected_msg',
    [
        ('SUCCESS', '2020-09-18T00:00:00+00:00', None, None),
        ('SUCCESS', None, None, None),
        ('FAIL_INVALID_DATE_TIME_FORMAT', '2020-09-18T00:00:00Z',
            HTTPStatus.BAD_REQUEST, [{
                'error': '2020-09-18T00:00:00Z is an invalid ISO format for effectiveDate.',
                'path': '/filing/header/effectiveDate'
            }]),
        ('FAIL_INVALID_DATE_TIME_MINIMUM', '2020-09-17T00:01:00+00:00',
            HTTPStatus.BAD_REQUEST, [{
                'error': 'Invalid Datetime, effective date must be a minimum of 2 minutes ahead.',
                'path': '/filing/header/effectiveDate'
            }]),
        ('FAIL_INVALID_DATE_TIME_MAXIMUM', '2020-09-27T00:01:00+00:00',
            HTTPStatus.BAD_REQUEST, [{
                'error': 'Invalid Datetime, effective date must be a maximum of 10 days ahead.',
                'path': '/filing/header/effectiveDate'
            }])
    ])
@patch.object(PermissionService, 'check_user_permission', MagicMock(return_value=None))
def test_validate_alteration_effective_date(session, test_name,
                                               effective_date, expected_code, expected_msg):
    """Test effective date validation in alteration."""
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type='BC')

    filing = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    filing['filing']['header']['identifier'] = identifier
    filing['filing']['business']['legalType'] = 'BC'
    filing['filing']['alteration']['business']['legalType'] = 'BEN'
    del filing['filing']['alteration']['nameRequest']

    if effective_date is not None:
        filing['filing']['header']['effectiveDate'] = effective_date

    if 'courtOrder' in filing['filing']['alteration']:
        del filing['filing']['alteration']['courtOrder']

    # perform test
    with freeze_time(now):
        err = validate(business, filing)

    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None

@pytest.mark.parametrize(
    ('good_standing', 'has_permission', 'should_pass', 'entity_type'),
    [
        (True, True, True, 'BC'),
        (True, False, True, 'BC'),
        (False, False, False, 'BC'),
        (False, True, True, 'BC')
        ]
        )
def test_alteration_good_standing(session, good_standing, has_permission, should_pass, entity_type):
    """Test that a valid Alteration passes/fails validation based on good standing."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type=entity_type)
    f = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    f['filing']['header']['identifier'] = identifier
    f['filing']['business']['legalType'] = entity_type
    f['filing']['alteration']['business']['legalType'] = 'BEN'
    del f['filing']['alteration']['nameRequest']
    if has_permission:
        mock_check_user_permission = MagicMock(return_value=None)
    else:
        mock_check_user_permission = MagicMock(return_value=Error(
            HTTPStatus.FORBIDDEN,
            [{'error': 'Permission Denied - You do not have permissions send not in gpod standing businesss in this filing.'}],
        ))
    with (
        patch.object(flags, 'is_on', return_value=True),
        patch.object(Business, 'good_standing', new_callable =lambda: good_standing),
        patch.object(PermissionService, 'check_user_permission', mock_check_user_permission)
    ):
        err = validate(business, f)
    if should_pass:
        # check that validation passed
        assert None is err
    else:
        # check that validation failed
        assert err
        if not good_standing and not has_permission:
            assert HTTPStatus.FORBIDDEN == err.code
            assert 'Permission Denied' in err.msg[0]['error']
        else:
            assert HTTPStatus.BAD_REQUEST == err.code

@pytest.mark.parametrize('test_name, name_translation, expected_code, expected_msg', [
    ('SUCCESS_NAME_TRANSLATION_EMPTY_ARRAY', [], None, None),
    ('SUCCESS_NAME_TRANSLATION', [{"name": "TEST"}], None, None),
    ('FAIL_EMPTY_NAME_TRANSLATION', [{"name": ""}],  HTTPStatus.BAD_REQUEST, [{
        'error': 'Name translation cannot be an empty string.',
        'path': '/filing/alteration/nameTranslations/0/name/'
    }]),
    ('FAIL_WHITESPACE_ONLY_NAME_TRANSLATION', [{"name": "   "}], HTTPStatus.BAD_REQUEST, [{
        'error': 'Name translation cannot be an empty string.',
        'path': '/filing/alteration/nameTranslations/0/name/'
    }]),
    ('FAIL_LEADING_AND_TRAILING_WHITESPACE_NAME_TRANSLATION', [{"name": " TEST "}], HTTPStatus.BAD_REQUEST, [{
        'error': 'Name translation cannot start or end with whitespace.',
        'path': '/filing/alteration/nameTranslations/0/name/'
    }]),
    ('FAIL_MULTIPLE_NAME_TRANSLATION', [{"name": "   "}, {"name": " TEST  "}], HTTPStatus.BAD_REQUEST, [{
        'error': 'Name translation cannot be an empty string.',
        'path': '/filing/alteration/nameTranslations/0/name/'
    },
    {
        'error': 'Name translation cannot start or end with whitespace.',
        'path': '/filing/alteration/nameTranslations/1/name/'
    }
    ]),
])
def test_validate_name_translation(session, test_name, name_translation, expected_code, expected_msg):
    """Test validate name translation if provided."""
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type='BC')
    filing = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    filing['filing']['header']['identifier'] = identifier
    filing['filing']['business']['legalType'] = 'BC'
    filing['filing']['alteration']['business']['legalType'] = 'BEN'
    del filing['filing']['alteration']['nameRequest']
    if 'courtOrder' in filing['filing']['alteration']:
        del filing['filing']['alteration']['courtOrder']
    
    filing['filing']['alteration']['nameTranslations'] = name_translation

    # perform test
    with freeze_time(now):
        err = validate(business, filing)

    # validate outcomes
    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        if err:
            print(err, err.code, err.msg)
        assert err is None
