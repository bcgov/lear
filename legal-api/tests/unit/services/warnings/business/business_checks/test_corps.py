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
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from tests.unit.models import factory_business
from legal_api.services.warnings.business.business_checks import WarningType
from legal_api.services.warnings.business.business_checks.corps import check_business

@pytest.mark.parametrize("has_amalgamation, expected_warning, expected_data", [
    (True, True, {"amalgamationDate": datetime.now() + timedelta(days=1)}),  # Future effective amalgamation
    (False, False, {}),  # No amalgamation
])
def test_check_business(session, has_amalgamation, expected_warning, expected_data):
    """Test the check_business function."""
    business = factory_business(identifier="BC1234567")

    mock_filing = Mock()
    if has_amalgamation:
        mock_filing.effective_date = expected_data["amalgamationDate"]
        mock_filing.payment_completion_date = datetime.now() - timedelta(days=1)
    else:
        # Set to realistic non-amalgamating scenario
        mock_filing.effective_date = datetime.now() - timedelta(days=2)
        mock_filing.payment_completion_date = datetime.now() - timedelta(days=1)

    with patch('legal_api.models.business.Business.is_pending_amalgamating_business', return_value=mock_filing):
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
