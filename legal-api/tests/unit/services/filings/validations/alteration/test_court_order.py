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
"""Tests to assure the Court Order is validated properly."""
import pytest

from legal_api.services.filings.validations.common_validations import validate_court_order


@pytest.mark.parametrize(
    "invalid_court_order",
    [
        {
            "fileNumber": "123456789012345678901",  # long fileNumber
            "orderDate": "2021-01-30T09:56:01+01:00",
            "effectOfOrder": "planOfArrangement",
        },
        {"orderDate": "2021-01-30T09:56:01+01:00", "effectOfOrder": "planOfArrangement"},
        {
            "fileNumber": "Valid file number",
            "orderDate": "a2021-01-30T09:56:01",  # Invalid date
            "effectOfOrder": "planOfArrangement",
        },
        {
            "fileNumber": "Valid File Number",
            "orderDate": "2021-01-30T09:56:01+01:00",
            "effectOfOrder": "invalid",  # Invalid effectOfOrder
        },
    ],
)
def test_validate_invalid_court_orders(session, invalid_court_order):
    """Assert not valid court orders."""
    msg = validate_court_order("/filing/alteration/courtOrder", invalid_court_order)

    assert msg
    assert len(msg) > 0


@pytest.mark.parametrize(
    "valid_court_order",
    [
        {"fileNumber": "12345678901234567890"},
        {
            "fileNumber": "Valid file number",
            "orderDate": "2021-01-30T09:56:01+01:00",
            "effectOfOrder": "planOfArrangement",
        },
    ],
)
def test_validate_valid_court_orders(session, valid_court_order):
    """Assert valid court orders."""
    msg = validate_court_order("/filing/alteration/courtOrder", valid_court_order)

    assert not msg
