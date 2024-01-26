# Copyright © 2024 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in business with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test suite to ensure Corpse business checks work correctly."""
import pytest
from unittest.mock import patch
from tests.unit.models import factory_business
from legal_api.services.warnings.business.business_checks import WarningType
from legal_api.services.warnings.business.business_checks.corps import check_business

@pytest.mark.parametrize("has_amalgamation, expected_warning, expected_data", [
    (True, True, {"amalgamationDate": None}),  # Test case where the business is part of an amalgamation
    (False, False, {}),                        # Test case where the business is not part of an amalgamation
])
def test_check_business(session, has_amalgamation, expected_warning, expected_data):
    """Test the check_business function."""
    business = factory_business(identifier="BC1234567")

    with patch('legal_api.services.warnings.business.business_checks.corps.check_amalgamating_business') as mock_check:
        mock_check.return_value = [{
            "code": "AMALGAMATING_BUSINESS",
            "message": "This business is part of a future effective amalgamation.",
            "warningType": WarningType.FUTURE_EFFECTIVE_AMALGAMATION,
            "data": expected_data
        }] if has_amalgamation else []

        result = check_business(business)

        if expected_warning:
            assert len(result) == 1
            warning = result[0]
            assert warning['code'] == "AMALGAMATING_BUSINESS"
            assert warning['message'] == "This business is part of a future effective amalgamation."
            assert warning['warningType'] == WarningType.FUTURE_EFFECTIVE_AMALGAMATION
            assert warning['data'] == expected_data
        else:
            assert len(result) == 0


