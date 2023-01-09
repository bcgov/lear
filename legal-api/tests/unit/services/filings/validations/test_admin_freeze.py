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
"""Test Admin Freeze validations."""
import copy
from http import HTTPStatus

import pytest
from registry_schemas.example_data import ADMIN_FREEZE, FILING_HEADER
from reportlab.lib.pagesizes import letter

from legal_api.services.filings.validations.admin_freeze import validate

from tests.unit.models import factory_business
from tests.unit.services.filings.test_utils import _upload_file
from tests.unit.services.filings.validations import lists_are_equal


@pytest.mark.parametrize(
    'freeze, identifier, expected_code',
    [
        (False, 'CP1234567', HTTPStatus.BAD_REQUEST),
    ]
)
def test_admin_freeze(session, freeze, identifier, expected_code):
    """Assert valid admin freeze."""
    business = factory_business(identifier)

    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['adminFreeze'] = copy.deepcopy(ADMIN_FREEZE)

    if not freeze:
        filing_json['filing']['adminFreeze']['freeze'] = False

    err = validate(business, filing_json)

    if expected_code:
        assert err.code == expected_code
    else:
        assert err is None