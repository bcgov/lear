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
from datetime import datetime, timedelta
from http import HTTPStatus
from unittest.mock import patch
from datetime import date

import pytest
from freezegun import freeze_time
from registry_schemas.example_data import FILING_HEADER, DISSOLUTION, SPECIAL_RESOLUTION
from reportlab.lib.pagesizes import letter

from legal_api.models import Business
from legal_api.services import MinioService
from legal_api.services.filings.validations import dissolution
from legal_api.services.filings.validations.dissolution import validate
from tests.unit.services.filings.test_utils import _upload_file
from tests.unit.services.filings.validations import lists_are_equal


@pytest.mark.parametrize(
    'test_status, legal_type, dissolution_type, identifier, expected_code, expected_msg',
    [
        ('SUCCESS', 'CP', 'voluntary', 'CP1234567', None, None),
        ('SUCCESS', 'CP', 'voluntaryLiquidation', 'CP1234567', None, None),
        ('SUCCESS', 'BC', 'voluntary', 'BC1234567', None, None),
        ('SUCCESS', 'SP', 'voluntary', 'BC1234567', None, None),
        ('SUCCESS', 'GP', 'voluntary', 'BC1234567', None, None),
        ('SUCCESS', 'GP', 'administrative', 'FM1234567', None, None),
        ('SUCCESS', 'SP', 'administrative', 'FM1234567', None, None),
        ('SUCCESS', 'CP', 'administrative', 'CP1234567', None, None),
        ('SUCCESS', 'BC', 'administrative', 'BC1234567', None, None),
        ('FAIL', 'CP', 'involuntary', 'CP1234567', HTTPStatus.BAD_REQUEST, 'Invalid Dissolution type.'),
        ('FAIL', 'BC', 'voluntaryLiquidation', 'BC1234567', HTTPStatus.BAD_REQUEST, 'Invalid Dissolution type.'),
        ('FAIL', 'BEN', 'voluntaryLiquidation', 'BC1234567', HTTPStatus.BAD_REQUEST, 'Invalid Dissolution type.'),
        ('FAIL', 'CC', 'voluntaryLiquidation', 'BC1234567', HTTPStatus.BAD_REQUEST, 'Invalid Dissolution type.'),
        ('FAIL', 'ULC', 'voluntaryLiquidation', 'BC1234567', HTTPStatus.BAD_REQUEST, 'Invalid Dissolution type.')
    ]
)
def test_dissolution_type(session, test_status, legal_type, dissolution_type,
                          identifier, expected_code, expected_msg):  # pylint: disable=too-many-arguments
    """Assert that a VD can be validated."""
    # setup
    business = Business(identifier=identifier, legal_type=legal_type)

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['name'] = 'dissolution'
    filing['filing']['business']['legalType'] = legal_type
    filing['filing']['dissolution'] = copy.deepcopy(DISSOLUTION)
    filing['filing']['dissolution']['dissolutionType'] = dissolution_type
    filing['filing']['dissolution']['parties'][1]['deliveryAddress'] = \
        filing['filing']['dissolution']['parties'][1]['mailingAddress']

    if legal_type != Business.LegalTypes.COOP.value or dissolution_type == 'administrative':
        del filing['filing']['dissolution']['dissolutionStatementType']

    if dissolution_type == 'administrative':
        filing['filing']['dissolution']['details'] = "Some Details"
        del filing['filing']['dissolution']['affidavitFileKey']
        del filing['filing']['dissolution']['parties']

    with patch.object(dissolution, 'validate_affidavit', return_value=None):
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
    business = Business(identifier=identifier, legal_type=legal_type)

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
    with patch.object(dissolution, 'validate_affidavit', return_value=None):
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
        ('PASS', 'SP', 'not_in_bc', 'FM1234567', None, None),
        ('PASS', 'GP', 'not_in_bc', 'FM1234567', None, None),
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
    business = Business(identifier=identifier, legal_type=legal_type)

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

    with patch.object(dissolution, 'validate_affidavit', return_value=None):
        err = validate(business, filing)

    # validate outcomes
    if expected_code or expected_msg:
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err


@pytest.mark.parametrize(
    'test_name, legal_type, dissolution_type, identifier, has_special_resolution_filing, expected_code, expected_msg',
    [
        ('SUCCESS', 'BC', 'voluntary', 'BC1234567', False, None, None),
        ('SUCCESS', 'CP', 'voluntary', 'CP1234567', True, None, None),
        ('FAIL_REQUIRED_SPECIAL_RESOLUTIONS', 'CP', 'voluntary', 'CP1234567', False,
         HTTPStatus.BAD_REQUEST, [{'error': 'Special Resolution is required.', 'path': '/filing/specialResolution'}])
    ]
)
def test_dissolution_special_resolution(session, test_name, legal_type, dissolution_type,
                                        identifier, has_special_resolution_filing, expected_code, expected_msg):  # pylint: disable=too-many-arguments
    """Assert that special resolution can be validated."""
    from legal_api.services.filings import validate
    # setup
    business = Business(identifier=identifier, legal_type=legal_type)

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['name'] = 'dissolution'
    filing['filing']['business']['legalType'] = legal_type
    filing['filing']['dissolution'] = copy.deepcopy(DISSOLUTION)
    filing['filing']['dissolution']['dissolutionType'] = dissolution_type
    filing['filing']['dissolution']['parties'][1]['deliveryAddress'] = \
        filing['filing']['dissolution']['parties'][1]['mailingAddress']
    if has_special_resolution_filing:
        filing['filing']['specialResolution'] = copy.deepcopy(SPECIAL_RESOLUTION)
        resolution_date_str = filing['filing']['specialResolution']['resolutionDate']
        resolution_date_time = datetime.strptime(resolution_date_str, '%Y-%m-%d')
        business.founding_date = resolution_date_time - timedelta(days=1000)

    with patch.object(dissolution, 'validate_affidavit', return_value=None):
        err = validate(business, filing)

    # validate outcomes
    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None


@pytest.mark.parametrize(
    'test_name, legal_type, dissolution_type, key, scenario, identifier, expected_code, expected_msg',
    [
        ('SUCCESS', 'BC', 'voluntary', '', 'success', 'BC1234567', None, None),
        ('SUCCESS', 'CP', 'voluntary', '', 'success', 'CP1234567', None, None),
        ('FAIL_INVALID_AFFIDAVIT_FILE_KEY', 'CP', 'voluntary', 'affidavitFileKey', 'failAffidavit', 'CP1234567',
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Invalid file.', 'path': '/filing/dissolution/affidavitFileKey'
         }]),
        ('FAIL_REQUIRED_AFFIDAVIT_FILE_KEY', 'CP', 'voluntary', 'affidavitFileKey', '', 'CP1234567',
         HTTPStatus.BAD_REQUEST, [{
             'error': 'A valid affidavit key is required.', 'path': '/filing/dissolution/affidavitFileKey'
         }]),
        ('FAIL_INVALID_AFFIDAVIT_FILE', 'CP', 'voluntary', 'affidavitFileKey', 'invalidAffidavitPageSize', 'CP1234567',
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Document must be set to fit onto 8.5” x 11” letter-size paper.',
             'path': '/filing/dissolution/affidavitFileKey'
         }]),
    ]
)
def test_dissolution_affidavit(session, minio_server, test_name, legal_type, dissolution_type, key, scenario,
                               identifier, expected_code, expected_msg):  # pylint: disable=too-many-arguments
    """Assert that an affidavit can be validated."""
    # setup
    business = Business(identifier=identifier, legal_type=legal_type)

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['name'] = 'dissolution'
    filing['filing']['business']['legalType'] = legal_type
    filing['filing']['dissolution'] = copy.deepcopy(DISSOLUTION)
    filing['filing']['dissolution']['dissolutionType'] = dissolution_type
    filing['filing']['dissolution']['parties'][1]['deliveryAddress'] = \
        filing['filing']['dissolution']['parties'][1]['mailingAddress']

    if scenario:
        if scenario == 'success':
            if legal_type == Business.LegalTypes.COOP.value:
                filing['filing']['dissolution']['affidavitFileKey'] = _upload_file(letter, invalid=False)
            else:
                del filing['filing']['dissolution']['affidavitFileKey']
        elif scenario == 'failAffidavit':
            filing['filing']['dissolution']['affidavitFileKey'] = 'invalid file key'
        elif scenario == 'invalidAffidavitPageSize':
            filing['filing']['dissolution']['affidavitFileKey'] = _upload_file(letter, invalid=True)
    else:
        # Assign key and value to test empty variables for failures
        key_value = ''
        filing['filing']['dissolution'][key] = key_value

    err = validate(business, filing)

    # validate outcomes
    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None

    # Cleanup
    if file_key := filing['filing']['dissolution'].get('affidavitFileKey', None):
        MinioService.delete_file(file_key)


@pytest.mark.parametrize(
    'test_status, file_number, effect_of_order, expected_code, expected_msg',
    [
        ('FAIL', None, 'planOfArrangement', HTTPStatus.BAD_REQUEST, 'Court order file number is required.'),
        ('FAIL', '12345678901234567890', 'invalid', HTTPStatus.BAD_REQUEST, 'Invalid effectOfOrder.'),
        ('SUCCESS', '12345678901234567890', 'planOfArrangement', None, None)
    ]
)
def test_dissolution_court_orders(session, test_status, file_number, effect_of_order, expected_code, expected_msg):
    """Assert valid court orders."""
    business = Business(identifier='BC1234567')

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['name'] = 'dissolution'
    filing['filing']['business']['legalType'] = 'BC'
    filing['filing']['dissolution'] = copy.deepcopy(DISSOLUTION)
    filing['filing']['dissolution']['parties'][1]['deliveryAddress'] = \
        filing['filing']['dissolution']['parties'][1]['mailingAddress']

    court_order = {
        'effectOfOrder': effect_of_order
    }

    if file_number:
        court_order['fileNumber'] = file_number

    filing['filing']['dissolution']['courtOrder'] = court_order

    with patch.object(dissolution, 'validate_affidavit', return_value=None):
        err = validate(business, filing)

    # validate outcomes
    if test_status == 'FAIL':
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err


@pytest.mark.parametrize(
    'test_status, legal_type, dissolution_type, email, expected_code, expected_msg',
    [
        # Required email cases (missing or None)
        ('FAIL', 'BC', 'voluntary', None, HTTPStatus.BAD_REQUEST,
         'Custodian email is required for voluntary dissolution.'),
        ('FAIL', 'BEN', 'voluntary', None, HTTPStatus.BAD_REQUEST,
         'Custodian email is required for voluntary dissolution.'),
        ('FAIL', 'CC', 'voluntary', None, HTTPStatus.BAD_REQUEST,
         'Custodian email is required for voluntary dissolution.'),
        ('FAIL', 'ULC', 'voluntary', None, HTTPStatus.BAD_REQUEST,
         'Custodian email is required for voluntary dissolution.'),

        # Whitespace-only emails
        ('FAIL', 'BC', 'voluntary', ' ', HTTPStatus.BAD_REQUEST,
         'Custodian email cannot contain any whitespaces.'),
        ('FAIL', 'BC', 'voluntary', '   ', HTTPStatus.BAD_REQUEST,
         'Custodian email cannot contain any whitespaces.'),
        ('FAIL', 'BC', 'voluntary', '\t', HTTPStatus.BAD_REQUEST,
         'Custodian email cannot contain any whitespaces.'),
        ('FAIL', 'BC', 'voluntary', '\n', HTTPStatus.BAD_REQUEST,
         'Custodian email cannot contain any whitespaces.'),

        # Leading/trailing/middle whitespace
        ('FAIL', 'BC', 'voluntary', ' test@example.com', HTTPStatus.BAD_REQUEST,
         'Custodian email cannot contain any whitespaces.'),
        ('FAIL', 'BC', 'voluntary', 'test@example.com ', HTTPStatus.BAD_REQUEST,
         'Custodian email cannot contain any whitespaces.'),
        ('FAIL', 'BC', 'voluntary', 'te st@example.com', HTTPStatus.BAD_REQUEST,
         'Custodian email cannot contain any whitespaces.'),

        # Valid emails (no whitespace)
        ('SUCCESS', 'CP', 'voluntary', None, None, None),
        ('SUCCESS', 'BC', 'voluntary', 'test@example.com', None, None),
        ('SUCCESS', 'BEN', 'voluntary', 'test@example.com', None, None),
        ('SUCCESS', 'CC', 'voluntary', 'test@example.com', None, None),
        ('SUCCESS', 'ULC', 'voluntary', 'test@example.com', None, None),
        ('SUCCESS', 'BC', 'administrative', None, None, None),
    ]
)
def test_dissolution_custodian_email(session, test_status, legal_type, dissolution_type,
                                     email, expected_code, expected_msg):
    """Test custodian email validation in voluntary dissolution."""
    business = Business(identifier='BC1234567', legal_type=legal_type)
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['name'] = 'dissolution'
    filing['filing']['business']['legalType'] = legal_type
    filing['filing']['dissolution'] = copy.deepcopy(DISSOLUTION)
    filing['filing']['dissolution']['dissolutionType'] = dissolution_type
    filing['filing']['dissolution']['parties'][1]['deliveryAddress'] = \
        filing['filing']['dissolution']['parties'][1]['mailingAddress']

    officer = filing['filing']['dissolution']['parties'][1]['officer']
    if email is None:
        officer.pop('email', None)
    else:
        officer['email'] = email

    if dissolution_type == 'administrative':
        filing['filing']['dissolution']['details'] = "Some Details"
        del filing['filing']['dissolution']['affidavitFileKey']

    with patch.object(dissolution, 'validate_affidavit', return_value=None):
        err = validate(business, filing)

    if test_status == 'FAIL':
        assert err.code == expected_code
        assert any(expected_msg in msg['error'] for msg in err.msg)
    else:
        assert err is None

@pytest.mark.parametrize(
    'test_status, legal_type, dissolution_type, party_type, org_name, expected_code, expected_msg',
    [
        # Required organization name cases (missing or None)
        ('FAIL', 'BC', 'voluntary', 'organization', None, HTTPStatus.BAD_REQUEST,
         'Corporation or firm name is required for an organization.'),
        ('FAIL', 'BC', 'voluntary', 'organization', '', HTTPStatus.BAD_REQUEST,
         'Corporation or firm name is required for an organization.'),
        ('FAIL', 'BC', 'voluntary', 'organization', '   ', HTTPStatus.BAD_REQUEST,
         'Corporation or firm name is required for an organization.'),

        # Leading/trailing whitespace
        ('SUCCESS', 'BC', 'voluntary', 'organization', '  LeadingSpace', None, None),
        ('SUCCESS', 'BC', 'voluntary', 'organization', 'TrailingSpace  ', None, None),
        ('SUCCESS', 'BC', 'voluntary', 'organization', '  BothSides  ', None, None),

        # Valid name
        ('SUCCESS', 'BC', 'voluntary', 'organization', 'Test Org', None, None),

        # Non-organization party types should skip validation
        ('SUCCESS', 'BC', 'voluntary', 'person', None, None, None),

        # Legal types other than CORP should skip validation
        ('SUCCESS', 'CP', 'voluntary', 'organization', None, None, None),
        ('SUCCESS', 'BC', 'administrative', 'organization', None, None, None),
    ]
)
def test_dissolution_custodian_org_name(session, test_status, legal_type, dissolution_type,
                                        party_type, org_name, expected_code, expected_msg):
    """Test custodian organization name validation and trimming."""

    business = Business(identifier='BC1234567', legal_type=legal_type)
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['name'] = 'dissolution'
    filing['filing']['business']['legalType'] = legal_type
    filing['filing']['dissolution'] = copy.deepcopy(DISSOLUTION)
    filing['filing']['dissolution']['dissolutionType'] = dissolution_type
    filing['filing']['dissolution']['parties'][1]['deliveryAddress'] = \
        filing['filing']['dissolution']['parties'][1]['mailingAddress']

    if dissolution_type == 'administrative':
        filing['filing']['dissolution']['details'] = "Some Details"
        del filing['filing']['dissolution']['affidavitFileKey']

    officer = filing['filing']['dissolution']['parties'][1]['officer']
    officer['partyType'] = party_type
    if org_name is not None:
        officer['organizationName'] = org_name
    elif 'organizationName' in officer:
        del officer['organizationName']

    with patch.object(dissolution, 'validate_affidavit', return_value=None):
        err = validate(business, filing)

    if test_status == 'FAIL':
        assert err.code == expected_code
        assert any(expected_msg in msg['error'] for msg in err.msg)
    else:
        assert err is None

    # Check that the organizationName is trimmed for successful payloads
    if org_name and party_type == 'organization' and test_status == 'SUCCESS' and legal_type in Business.CORPS:
        trimmed = filing['filing']['dissolution']['parties'][1]['officer'].get('organizationName')
        assert trimmed == org_name.strip()



@pytest.mark.parametrize(
    'test_status, legal_type, dissolution_type, has_custodial_office, expected_code, expected_msg',
    [
        ('FAIL', 'BC', 'voluntary', False, HTTPStatus.BAD_REQUEST,
        'Custodial office is required for voluntary dissolution.'),
        ('FAIL', 'BEN', 'voluntary', False, HTTPStatus.BAD_REQUEST,
        'Custodial office is required for voluntary dissolution.'),
        ('FAIL', 'CC', 'voluntary', False, HTTPStatus.BAD_REQUEST,
        'Custodial office is required for voluntary dissolution.'),
        ('FAIL', 'ULC', 'voluntary', False, HTTPStatus.BAD_REQUEST,
        'Custodial office is required for voluntary dissolution.'),
        ('SUCCESS', 'CP', 'voluntary', False, None, None),
        ('SUCCESS', 'BC', 'voluntary', True, None, None),
        ('SUCCESS', 'BEN', 'voluntary', True, None, None),
        ('SUCCESS', 'CC', 'voluntary', True, None, None),
        ('SUCCESS', 'ULC', 'voluntary', True, None, None),
        ('SUCCESS', 'BC', 'administrative', False, None, None),
    ]
)
def test_dissolution_custodial_office(session, test_status, legal_type, dissolution_type, has_custodial_office,
                                      expected_code, expected_msg):
    """Test custodial office validation in voluntary dissolution."""
    business = Business(identifier='BC1234567', legal_type=legal_type)
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['name'] = 'dissolution'
    filing['filing']['business']['legalType'] = legal_type
    filing['filing']['dissolution'] = copy.deepcopy(DISSOLUTION)
    filing['filing']['dissolution']['dissolutionType'] = dissolution_type
    filing['filing']['dissolution']['parties'][1]['deliveryAddress'] = \
        filing['filing']['dissolution']['parties'][1]['mailingAddress']

    if not has_custodial_office:
        del filing['filing']['dissolution']['custodialOffice']

    if dissolution_type == 'administrative':
        filing['filing']['dissolution']['details'] = "Some Details"
        del filing['filing']['dissolution']['affidavitFileKey']

    with patch.object(dissolution, 'validate_affidavit', return_value=None):
        err = validate(business, filing)

    if test_status == 'FAIL':
        assert err.code == expected_code
        assert any(expected_msg in msg['error'] for msg in err.msg)
    else:
        assert err is None

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
def test_dissolution_effective_date(session, test_name,
                                               effective_date, expected_code, expected_msg):
    """Test effective date validation in voluntary dissolution."""
    business = Business(identifier='BC1234567', legal_type='BC')
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['name'] = 'dissolution'
    filing['filing']['business']['legalType'] = 'BC'
    filing['filing']['dissolution'] = copy.deepcopy(DISSOLUTION)
    filing['filing']['dissolution']['dissolutionType'] = 'voluntary'
    filing['filing']['dissolution']['parties'][1]['deliveryAddress'] = \
        filing['filing']['dissolution']['parties'][1]['mailingAddress']

    if effective_date is not None:
        filing['filing']['header']['effectiveDate'] = effective_date

    # perform test
    with freeze_time(now):
        err = validate(business, filing)

    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None
