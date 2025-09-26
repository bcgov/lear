# Copyright © 2025 Province of British Columbia
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
"""Tests for the restoration processor are contained here."""

from unittest.mock import MagicMock, patch

from business_model.models import DCRevocationReason

from business_digital_credentials.digital_credential_processors import restoration
from tests.unit import create_business


@patch.object(restoration, 'get_all_digital_credentials_for_business', return_value=[])
@patch.object(restoration, 'revoke_digital_credential')
def test_processor_returns_none_if_no_issued_credentials(mock_revoke_digital_credential,
                                                         mock_get_all_digital_credentials_for_business,
                                                         app, session):
    """Assert that the processor returns None if the current business has no issued credentials."""
    business = create_business(identifier='FM0000001')

    result = restoration.process(business)

    mock_get_all_digital_credentials_for_business.assert_called_once_with(business=business)
    mock_revoke_digital_credential.assert_not_called()
    assert result is None


@patch.object(restoration, 'get_all_digital_credentials_for_business')
@patch.object(restoration, 'revoke_digital_credential')
def test_processor_revokes_all_credentials(mock_revoke_digital_credential,
                                          mock_get_all_digital_credentials_for_business,
                                          app, session):
    """Assert that the processor revokes all credentials when business is restored."""
    business = create_business(identifier='FM0000001')
    
    mock_credential1 = MagicMock()
    mock_credential1.id = 1
    mock_credential2 = MagicMock()
    mock_credential2.id = 2
    
    mock_get_all_digital_credentials_for_business.return_value = [mock_credential1, mock_credential2]

    result = restoration.process(business)

    mock_get_all_digital_credentials_for_business.assert_called_once_with(business=business)
    assert mock_revoke_digital_credential.call_count == 2
    # Check that revoke_digital_credential was called twice with RESTORATION reason
    calls = mock_revoke_digital_credential.call_args_list
    assert len(calls) == 2
    # Each call should have the reason argument set to RESTORATION
    for call in calls:
        assert call[1]['reason'].value == 'Your business was restored to the Registry. '
    assert result is None


@patch.object(restoration, 'get_all_digital_credentials_for_business')
@patch.object(restoration, 'revoke_digital_credential')
def test_processor_returns_none_with_empty_credentials_list(mock_revoke_digital_credential,
                                                           mock_get_all_digital_credentials_for_business,
                                                           app, session):
    """Assert that the processor returns None when credentials list is empty."""
    business = create_business(identifier='FM0000001')
    
    mock_get_all_digital_credentials_for_business.return_value = []

    result = restoration.process(business)

    mock_get_all_digital_credentials_for_business.assert_called_once_with(business=business)
    mock_revoke_digital_credential.assert_not_called()
    assert result is None


@patch.object(restoration, 'get_all_digital_credentials_for_business')
@patch.object(restoration, 'revoke_digital_credential')
def test_processor_returns_none_with_none_credentials(mock_revoke_digital_credential,
                                                     mock_get_all_digital_credentials_for_business,
                                                     app, session):
    """Assert that the processor returns None when credentials is None."""
    business = create_business(identifier='FM0000001')
    
    mock_get_all_digital_credentials_for_business.return_value = None

    result = restoration.process(business)

    mock_get_all_digital_credentials_for_business.assert_called_once_with(business=business)
    mock_revoke_digital_credential.assert_not_called()
    assert result is None