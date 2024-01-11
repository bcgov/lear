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

from legal_api.services.filings.validations.court_order import validate
from tests.unit.models import factory_legal_entity
from tests.unit.services.filings.test_utils import _upload_file
from tests.unit.services.filings.validations import lists_are_equal


@pytest.mark.parametrize(
    "test_status, expected_code, expected_msg",
    [
        (
            "FAIL",
            HTTPStatus.BAD_REQUEST,
            [
                {"error": "Invalid effectOfOrder.", "path": "/filing/courtOrder/effectOfOrder"},
                {"error": "Court Order is required (in orderDetails/fileKey).", "path": "/filing/courtOrder"},
            ],
        ),
        ("SUCCESS", None, None),
    ],
)
def test_court_orders(session, test_status, expected_code, expected_msg):
    """Assert valid court order."""
    legal_entity = factory_legal_entity("BC1234567")
    filing = copy.deepcopy(COURT_ORDER_FILING_TEMPLATE)
    del filing["filing"]["courtOrder"]["fileKey"]
    if test_status == "FAIL":
        del filing["filing"]["courtOrder"]["orderDetails"]
        filing["filing"]["courtOrder"]["effectOfOrder"] = "invalid"
    err = validate(legal_entity, filing)

    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None


file_key_path = "/filing/courtOrder/fileKey"


@pytest.mark.parametrize(
    "test_name, expected_code, expected_msg",
    [
        ("SUCCESS", None, None),
        ("FAIL_INVALID_FILE_KEY", HTTPStatus.BAD_REQUEST, [{"error": "Invalid file.", "path": file_key_path}]),
        (
            "FAIL_INVALID_FILE_KEY_SIZE",
            HTTPStatus.BAD_REQUEST,
            [{"error": "Document must be set to fit onto 8.5” x 11” letter-size paper.", "path": file_key_path}],
        ),
    ],
)
def test_court_order_file(session, minio_server, test_name, expected_code, expected_msg):
    """Assert valid court order."""
    legal_entity = factory_legal_entity("BC1234567")
    filing = copy.deepcopy(COURT_ORDER_FILING_TEMPLATE)

    if test_name == "SUCCESS":
        filing["filing"]["courtOrder"]["fileKey"] = _upload_file(letter, invalid=False)
    elif test_name == "FAIL_INVALID_FILE_KEY_SIZE":
        filing["filing"]["courtOrder"]["fileKey"] = _upload_file(letter, invalid=True)

    err = validate(legal_entity, filing)

    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None
