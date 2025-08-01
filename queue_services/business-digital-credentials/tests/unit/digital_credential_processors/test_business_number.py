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
"""Tests for the business number processor are contained here."""

from unittest.mock import patch

from business_model.models import DCDefinition, DCRevocationReason

from business_digital_credentials.digital_credential_processors import business_number
from tests.unit import create_business


@patch.object(business_number, 'get_all_digital_credentials_for_business', return_value=[])
@patch.object(business_number, 'replace_digital_credential')
def test_processor_does_not_run_if_no_issued_credential(mock_replace_digital_credential,
                                                              mock_get_all_digital_credentials_for_business,
                                                              app, session):
    """Assert that the processor does not run if the current business has no issued credentials."""
    # Arrange
    business = create_business(identifier='FM0000001')

    # Act
    business_number.process(business)

    # Assert
    mock_get_all_digital_credentials_for_business.assert_called_once_with(
        business=business)
    mock_replace_digital_credential.assert_not_called()


@patch.object(business_number, 'get_all_digital_credentials_for_business', return_value=[{'id': 1}])
@patch.object(business_number, 'replace_digital_credential')
def test_processor_replaces_issued_credential(mock_replace_digital_credential,
                                                    mock_get_all_digital_credentials_for_business,
                                                    app, session):
    """Assert that the processor replaces the issued credential if it exists."""
    # Arrange
    business = create_business(identifier='FM0000001')

    # Act
    business_number.process(business)

    # Assert
    mock_get_all_digital_credentials_for_business.assert_called_once_with(
        business=business)
    mock_replace_digital_credential.assert_called_once_with(
        credential={'id': 1},
        credential_type=DCDefinition.CredentialType.business.name,
        reason=DCRevocationReason.UPDATED_INFORMATION)
