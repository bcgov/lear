# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test suite to ensure Voluntary Dissolution is validated correctly."""
import copy
from http import HTTPStatus
from unittest.mock import patch

import pytest
from registry_schemas.example_data import FILING_HEADER, DISSOLUTION
from reportlab.lib.pagesizes import letter, legal

from legal_api.models import Business
from legal_api.services import MinioService
from legal_api.services.filings.validations.dissolution import validate
from legal_api.services.filings.validations import dissolution
from tests.unit.services.filings.test_utils import _upload_file
from tests.unit.services.filings.validations import lists_are_equal


@pytest.mark.parametrize(
    'test_status, legal_type, dissolution_type, identifier, expected_code, expected_msg',
    [
        ('SUCCESS', 'CP', 'voluntary', 'CP1234567', None, None),
        ('SUCCESS', 'CP', 'voluntaryLiquidation', 'CP1234567', None, None),
        ('SUCCESS', 'BC', 'voluntary', 'BC1234567', None, None),
        ('FAIL', 'CP', 'involuntary', 'CP1234567', HTTPStatus.BAD_REQUEST, 'Invalid Dissolution type.'),
        ('FAIL', 'BC', 'voluntaryLiquidation', 'BC1234567', HTTPStatus.BAD_REQUEST, 'Invalid Dissolution type.'),
        ('FAIL', 'BEN', 'voluntaryLiquidation', 'BC1234567', HTTPStatus.BAD_REQUEST, 'Invalid Dissolution type.'),
        ('FAIL', 'CCC', 'voluntaryLiquidation', 'BC1234567', HTTPStatus.BAD_REQUEST, 'Invalid Dissolution type.'),
        ('FAIL', 'ULC', 'voluntaryLiquidation', 'BC1234567', HTTPStatus.BAD_REQUEST, 'Invalid Dissolution type.')
    ]
)
def test_dissolution_type(session, test_status, legal_type, dissolution_type,
                          identifier, expected_code, expected_msg):  # pylint: disable=too-many-arguments
    """Assert that a VD can be validated."""
    # setup
    business = Business(identifier=identifier)

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['name'] = 'dissolution'
    filing['filing']['business']['legalType'] = legal_type
    filing['filing']['dissolution'] = copy.deepcopy(DISSOLUTION)
    filing['filing']['dissolution']['dissolutionType'] = dissolution_type
    filing['filing']['dissolution']['parties'][1]['deliveryAddress'] = \
        filing['filing']['dissolution']['parties'][1]['mailingAddress']

    if legal_type != Business.LegalTypes.COOP.value:
        del filing['filing']['dissolution']['dissolutionStatementType']

    with patch.object(dissolution, 'validate_documents', return_value=None):
        err = validate(business, filing)

    # validate outcomes
    if expected_code or expected_msg:
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err


@pytest.mark.parametrize(
    'test_status, legal_type, dissolution_type, dissolution_statement_type, identifier, expected_code, expected_msg',
    [
        ('SUCCESS', 'CP', 'voluntary', '197NoAssetsNoLiabilities', 'CP1234567', None, None),
        ('SUCCESS', 'CP', 'voluntary', '197NoAssetsProvisionsLiabilities', 'CP1234567', None, None),
        ('FAIL', 'CP', 'voluntary', 'askf', 'CP1234567', HTTPStatus.BAD_REQUEST, 'Invalid Dissolution statement type.'),
        ('SUCCESS', 'BC', 'voluntary', '', 'BC1234567', None, None)
    ]
)
def test_dissolution_statement_type(session, test_status, legal_type, dissolution_type, dissolution_statement_type,
                                    identifier, expected_code, expected_msg):  # pylint: disable=too-many-arguments
    """Assert that a VD can be validated."""
    # setup
    business = Business(identifier=identifier)

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['name'] = 'dissolution'
    filing['filing']['business']['legalType'] = legal_type
    filing['filing']['dissolution'] = copy.deepcopy(DISSOLUTION)
    filing['filing']['dissolution']['dissolutionStatementType'] = dissolution_statement_type
    filing['filing']['dissolution']['dissolutionType'] = dissolution_type
    filing['filing']['dissolution']['parties'][1]['deliveryAddress'] = \
        filing['filing']['dissolution']['parties'][1]['mailingAddress']

    if legal_type != Business.LegalTypes.COOP.value:
        del filing['filing']['dissolution']['dissolutionStatementType']

    # perform test
    with patch.object(dissolution, 'validate_documents', return_value=None):
        err = validate(business, filing)

    # validate outcomes
    if expected_code or expected_msg:
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err


@pytest.mark.parametrize(
    'test_status, legal_type, address_validation, identifier, expected_code, expected_msg',
    [
        ('FAIL', 'CP', 'not_in_ca', 'CP1234567', HTTPStatus.BAD_REQUEST, 'Address must be in Canada.'),
        ('FAIL', 'BC', 'not_in_bc', 'BC1234567', HTTPStatus.BAD_REQUEST, 'Address must be in BC.'),
        ('FAIL', 'BC', 'mailing_address_required', 'BC1234567',
         HTTPStatus.BAD_REQUEST, 'mailingAddress is required.'),
        ('FAIL', 'BC', 'party_address_required', 'BC1234567',
         HTTPStatus.BAD_REQUEST, 'Dissolution party is required.'),
        ('FAIL', 'CP', 'lookup_error', 'CP1234567',
         HTTPStatus.BAD_REQUEST, 'Address Country must resolve to a valid ISO-2 country.')
    ]
)
def test_dissolution_address(session, test_status, legal_type, address_validation,
                             identifier, expected_code, expected_msg):  # pylint: disable=too-many-arguments
    """Assert that a VD can be validated."""
    # setup
    business = Business(identifier=identifier)

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['name'] = 'dissolution'
    filing['filing']['business']['legalType'] = legal_type
    filing['filing']['dissolution'] = copy.deepcopy(DISSOLUTION)
    filing['filing']['dissolution']['parties'][1]['deliveryAddress'] = \
        filing['filing']['dissolution']['parties'][1]['mailingAddress']

    if legal_type != Business.LegalTypes.COOP.value:
        del filing['filing']['dissolution']['dissolutionStatementType']

    if address_validation in ['not_in_ca', 'not_in_bc']:
        if legal_type == Business.LegalTypes.COOP.value:
            filing['filing']['dissolution']['parties'][1]['mailingAddress']['addressCountry'] = 'US'
        elif legal_type == Business.LegalTypes.COMP.value:
            filing['filing']['dissolution']['parties'][1]['mailingAddress']['addressRegion'] = 'AB'
    elif address_validation == 'mailing_address_required':
        del filing['filing']['dissolution']['parties'][1]['mailingAddress']
    elif address_validation == 'party_address_required':
        filing['filing']['dissolution']['parties'] = []
    elif address_validation == 'lookup_error':
        filing['filing']['dissolution']['parties'][1]['mailingAddress']['addressCountry'] = 'adssadkj'

    with patch.object(dissolution, 'validate_documents', return_value=None):
        err = validate(business, filing)

    # validate outcomes
    if expected_code or expected_msg:
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err


@pytest.mark.parametrize(
    'test_name, legal_type, dissolution_type, key, scenario, identifier, expected_code, expected_msg',
    [
        ('SUCCESS', 'BC', 'voluntary', '', 'success', 'BC1234567', None, None),
        ('SUCCESS', 'CP', 'voluntary', '', 'success', 'BC1234567', None, None),
        ('FAIL_INVALID_AFFIDAVIT_FILE_KEY', 'CP', 'voluntary', 'affidavitFileKey', 'failAffidavit', 'CP1234567',
         HTTPStatus.BAD_REQUEST, [{
            'error': 'Invalid file.', 'path': '/filing/dissolution/affidavitFileKey'
        }]),
        ('FAIL_INVALID_SPECIAL_RESOLUTIONS_FILE_KEY', 'CP', 'voluntary', 'specialResolutionFileKey', 'failSpecialResolutions', 'CP1234567',
         HTTPStatus.BAD_REQUEST, [{
            'error': 'Invalid file.', 'path': '/filing/dissolution/specialResolutionFileKey'
        }]),
        ('FAIL_REQUIRED_AFFIDAVIT_FILE_KEY', 'CP', 'voluntary', 'affidavitFileKey', '', 'CP1234567',
         HTTPStatus.BAD_REQUEST, [{
            'error': 'A valid affidavit key is required.', 'path': '/filing/dissolution/affidavitFileKey'
        }]),
        ('FAIL_REQUIRED_AFFIDAVIT_FILE_NAME', 'CP', 'voluntary', 'affidavitFileName', '', 'CP1234567',
         HTTPStatus.BAD_REQUEST, [{
            'error': 'A valid affidavit file name is required.', 'path': '/filing/dissolution/affidavitFileName'
        }]),
        ('FAIL_REQUIRED_SPECIAL_RESOLUTION_FILE_KEY', 'CP', 'voluntary', 'specialResolutionFileKey', '', 'CP1234567',
         HTTPStatus.BAD_REQUEST, [{
            'error': 'A valid special resolution key is required.', 'path': '/filing/dissolution/specialResolutionFileKey'
        }]),
        ('FAIL_REQUIRED_SPECIAL_RESOLUTION_FILE_NAME', 'CP', 'voluntary', 'specialResolutionFileName', '', 'CP1234567',
         HTTPStatus.BAD_REQUEST, [{
            'error': 'A valid special resolution file name is required.', 'path': '/filing/dissolution/specialResolutionFileName'
        }]),
        ('FAIL_INVALID_AFFIDAVIT_FILE', 'CP', 'voluntary', 'affidavitFileKey', 'invalidAffidavitFileSize', 'CP1234567',
         HTTPStatus.BAD_REQUEST, [{
            'error': 'Document must be set to fit onto 8.5” x 11” letter-size paper.', 'path': '/filing/dissolution/affidavitFileKey'
        }]),
        ('FAIL_INVALID_SPECIAL_RESOLUTION_FILE', 'CP', 'voluntary', 'specialResolutionFileKey',
         'invalidSpecialResolutionFileSize', 'CP1234567',
         HTTPStatus.BAD_REQUEST, [{
            'error': 'Document must be set to fit onto 8.5” x 11” letter-size paper.', 'path': '/filing/dissolution/specialResolutionFileKey'
        }]),
    ]
)
def test_dissolution_documents(session, minio_server, test_name, legal_type, dissolution_type, key, scenario, identifier,
                               expected_code, expected_msg):  # pylint: disable=too-many-arguments
    """Assert that a VD can be validated."""
    # setup
    business = Business(identifier=identifier)

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['name'] = 'dissolution'
    filing['filing']['business']['legalType'] = legal_type
    filing['filing']['dissolution'] = copy.deepcopy(DISSOLUTION)
    filing['filing']['dissolution']['dissolutionType'] = dissolution_type
    filing['filing']['dissolution']['parties'][1]['deliveryAddress'] = \
        filing['filing']['dissolution']['parties'][1]['mailingAddress']

    if scenario:
        if scenario == 'success':
            if legal_type != Business.LegalTypes.COOP.value:
                del filing['filing']['dissolution']['affidavitFileKey']
                del filing['filing']['dissolution']['affidavitFileName']
                del filing['filing']['dissolution']['specialResolutionFileKey']
                del filing['filing']['dissolution']['specialResolutionFileName']
            else:
                filing['filing']['dissolution']['affidavitFileKey'] = _upload_file(letter)
                filing['filing']['dissolution']['specialResolutionFileKey'] = _upload_file(letter)
        elif scenario == 'failAffidavit':
            filing['filing']['dissolution']['affidavitFileKey'] = "invalid file key"
            filing['filing']['dissolution']['specialResolutionFileKey'] = _upload_file(letter)
        elif scenario == 'failSpecialResolutions':
            filing['filing']['dissolution']['affidavitFileKey'] = _upload_file(letter)
            filing['filing']['dissolution']['specialResolutionFileKey'] = "invalid file key"
        elif scenario == 'invalidAffidavitFileSize':
            filing['filing']['dissolution']['affidavitFileKey'] = _upload_file(legal)
            filing['filing']['dissolution']['specialResolutionFileKey'] = _upload_file(letter)
        elif scenario == 'invalidSpecialResolutionFileSize':
            filing['filing']['dissolution']['affidavitFileKey'] = _upload_file(letter)
            filing['filing']['dissolution']['specialResolutionFileKey'] = _upload_file(legal)
    else:
        # Assign key and value to test empty variables for failures
        key_value = ''
        filing['filing']['dissolution'][key] = key_value

    # perform test
    err = validate(business, filing)

    # validate outcomes
    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None

    # Cleanup
    if affidavitFileKey := filing['filing']['dissolution'].get('affidavitFileKey', None):
        MinioService.delete_file(affidavitFileKey)
    if specialResolutionFileKey := filing['filing']['dissolution'].get('specialResolutionFileKey', None):
        MinioService.delete_file(specialResolutionFileKey)
