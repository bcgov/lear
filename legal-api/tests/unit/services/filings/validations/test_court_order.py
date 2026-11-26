# Copyright © 2023 Province of British Columbia
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
"""Test Court Order validations."""
import copy
from http import HTTPStatus

import pytest
from registry_schemas.example_data import COURT_ORDER_FILING_TEMPLATE
from reportlab.lib.pagesizes import letter

from legal_api.services.authz import MIGRATED_COURT_ORDER_FEATURE
from legal_api.services.filings.validations import common_validations
from legal_api.services.filings.validations.common_validations import (
    MAX_COURT_ORDER_FILE_SIZE,
    MAX_FILE_SIZE,
    validate_pdf,
)
from legal_api.services.filings.validations.court_order import validate

from tests.unit.models import factory_business
from tests.unit.services.filings.test_utils import _create_pdf_file, _upload_file, mock_drs_get_document
from tests.unit.services.filings.validations import lists_are_equal
from tests.unit.services.utils import mock_new_feature


def _mock_file_size(monkeypatch, file_size):
    """Serve a valid letter-size PDF that reports the given size."""
    pdf_data = _create_pdf_file(letter, invalid=False).read()
    monkeypatch.setattr(common_validations, '_get_file_data', lambda _file_key: (pdf_data, file_size))


DETAILS_REQUIRED = {'error': 'Court Order details are required.', 'path': '/filing/courtOrder/orderDetails'}
DOCUMENT_REQUIRED = {'error': 'Court Order document is required.', 'path': '/filing/courtOrder/files'}
DETAILS_OR_DOCUMENT_REQUIRED = {'error': 'Court Order is required (in orderDetails/fileKey/files).',
                                'path': '/filing/courtOrder'}


def _court_order_filing(order_details, document):
    """Return a court order filing with only the given details and document (fileKey / files / None)."""
    filing = copy.deepcopy(COURT_ORDER_FILING_TEMPLATE)
    court_order = filing['filing']['courtOrder']
    file_key = court_order.pop('fileKey')
    del court_order['orderDetails']
    if order_details is not None:
        court_order['orderDetails'] = order_details
    if document == 'fileKey':
        court_order['fileKey'] = file_key
    elif document == 'files':
        court_order['files'] = [{'fileName': 'test_file.pdf', 'fileKey': file_key, 'documentType': 'court_order'}]
    return filing


@pytest.mark.parametrize(
    'test_name, order_details, document, expected_msg',
    [
        ('details_and_file_key', 'A note about order', 'fileKey', None),
        ('details_and_files', 'A note about order', 'files', None),
        ('no_details', None, 'files', [DETAILS_REQUIRED]),
        ('empty_details', '', 'files', [DETAILS_REQUIRED]),
        ('blank_details', '   ', 'fileKey', [DETAILS_REQUIRED]),
        ('no_document', 'A note about order', None, [DOCUMENT_REQUIRED]),
        ('no_details_or_document', None, None, [DETAILS_REQUIRED, DOCUMENT_REQUIRED]),
    ]
)
def test_court_order_migrated_requires_details_and_document(session, monkeypatch, test_name, order_details,
                                                            document, expected_msg):
    """Assert the court order filing requires the order details and a document when migratedCourtOrder is on."""
    mock_new_feature(monkeypatch, MIGRATED_COURT_ORDER_FEATURE, True)
    _mock_file_size(monkeypatch, MAX_FILE_SIZE)
    business = factory_business('BC1234567')

    err = validate(business, _court_order_filing(order_details, document))

    if expected_msg:
        assert err.code == HTTPStatus.BAD_REQUEST
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None


@pytest.mark.parametrize(
    'test_name, order_details, document, expected_msg',
    [
        ('details_and_files', 'A note about order', 'files', None),
        ('details_only', 'A note about order', None, None),
        ('file_key_only', None, 'fileKey', None),
        ('files_only', None, 'files', None),
        ('no_details_or_document', None, None, [DETAILS_OR_DOCUMENT_REQUIRED]),
        ('blank_details_no_document', '   ', None, [DETAILS_OR_DOCUMENT_REQUIRED]),
    ]
)
def test_court_order_legacy_requires_details_or_document(session, monkeypatch, test_name, order_details,
                                                         document, expected_msg):
    """Assert the court order filing requires the order details or a document when migratedCourtOrder is off."""
    mock_new_feature(monkeypatch, MIGRATED_COURT_ORDER_FEATURE, False)
    _mock_file_size(monkeypatch, MAX_FILE_SIZE)
    business = factory_business('BC1234567')

    err = validate(business, _court_order_filing(order_details, document))

    if expected_msg:
        assert err.code == HTTPStatus.BAD_REQUEST
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None


@pytest.mark.parametrize('is_migrated, expected_required', [
    (True, [DETAILS_REQUIRED, DOCUMENT_REQUIRED]),
    (False, [DETAILS_OR_DOCUMENT_REQUIRED]),
])
def test_court_order_invalid_effect_of_order(session, monkeypatch, is_migrated, expected_required):
    """Assert an invalid effectOfOrder is reported with the required errors."""
    mock_new_feature(monkeypatch, MIGRATED_COURT_ORDER_FEATURE, is_migrated)
    business = factory_business('BC1234567')
    filing = _court_order_filing(None, None)
    filing['filing']['courtOrder']['effectOfOrder'] = 'invalid'

    err = validate(business, filing)

    assert err.code == HTTPStatus.BAD_REQUEST
    assert lists_are_equal(err.msg, [
        {'error': 'Invalid effectOfOrder.', 'path': '/filing/courtOrder/effectOfOrder'},
        *expected_required
    ])


file_key_path = '/filing/courtOrder/fileKey'


@pytest.mark.parametrize('is_file_key', [True, False])
@pytest.mark.parametrize(
    'test_name, expected_code, expected_msg',
    [
        ('SUCCESS', None, None),
        ('FAIL_INVALID_FILE_KEY', HTTPStatus.BAD_REQUEST, [{'error': 'Invalid file.', 'path': file_key_path}]),
        ('FAIL_INVALID_FILE_KEY_SIZE', HTTPStatus.BAD_REQUEST, [{
            'error': 'Document must be set to fit onto 8.5” x 11” letter-size paper.',
            'path': file_key_path}])
    ])
def test_court_order_file(session, monkeypatch, test_name, expected_code, expected_msg, is_file_key):
    """Assert valid court order."""
    mock_drs_get_document(monkeypatch)
    business = factory_business('BC1234567')
    filing = copy.deepcopy(COURT_ORDER_FILING_TEMPLATE)

    if is_file_key:
        if test_name == 'SUCCESS':
            filing['filing']['courtOrder']['fileKey'] = _upload_file(letter, invalid=False)
        elif test_name == 'FAIL_INVALID_FILE_KEY_SIZE':
            filing['filing']['courtOrder']['fileKey'] = _upload_file(letter, invalid=True)
    else:
        files = []
        if test_name == 'FAIL_INVALID_FILE_KEY':
            files.append({
                "fileName": "test_file.pdf",
                "fileKey": filing['filing']['courtOrder']['fileKey'],
                "documentType": "court_order"
            })
        else:
            files.append({
                "fileName": "test_file.pdf",
                "fileKey": _upload_file(letter, invalid=(test_name == 'FAIL_INVALID_FILE_KEY_SIZE')),
                "documentType": "court_order"
            })
        del filing['filing']['courtOrder']['fileKey']
        filing['filing']['courtOrder']['files'] = files

    err = validate(business, filing)

    if expected_code:
        for msg in expected_msg:
            if not is_file_key:
                msg['path'] = msg['path'].replace('fileKey', 'files/0/fileKey')
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None


@pytest.mark.parametrize('is_file_key', [True, False])
@pytest.mark.parametrize(
    'file_size, expected_code',
    [
        (MAX_FILE_SIZE + 1, None),
        (MAX_COURT_ORDER_FILE_SIZE, None),
        (MAX_COURT_ORDER_FILE_SIZE + 1, HTTPStatus.BAD_REQUEST),
    ])
def test_court_order_file_size(session, monkeypatch, file_size, expected_code, is_file_key):
    """Assert court order files are accepted up to the court order size limit."""
    _mock_file_size(monkeypatch, file_size)
    business = factory_business('BC1234567')
    filing = copy.deepcopy(COURT_ORDER_FILING_TEMPLATE)
    expected_path = file_key_path

    if not is_file_key:
        file_key = filing['filing']['courtOrder'].pop('fileKey')
        filing['filing']['courtOrder']['files'] = [
            {'fileName': 'test_file.pdf', 'fileKey': file_key, 'documentType': 'court_order'}
        ]
        expected_path = '/filing/courtOrder/files/0/fileKey'

    err = validate(business, filing)

    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, [{'error': 'File exceeds maximum size.', 'path': expected_path}])
    else:
        assert err is None


@pytest.mark.parametrize(
    'file_size, expected_msg',
    [
        (MAX_FILE_SIZE, []),
        (MAX_FILE_SIZE + 1, [{'error': 'File exceeds maximum size.', 'path': file_key_path}]),
    ])
def test_validate_pdf_default_file_size(app, monkeypatch, file_size, expected_msg):
    """Assert the default size limit still applies to other uploads."""
    _mock_file_size(monkeypatch, file_size)

    with app.app_context():
        assert validate_pdf('COOP-DS1234567890', file_key_path) == expected_msg
