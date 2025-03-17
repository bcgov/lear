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
"""Tests for the put back on processor are contained here."""

from unittest.mock import patch

import pytest
from legal_api.models import DCRevocationReason

from entity_digital_credentials.digital_credentials_processors.put_back_on import process
from tests.unit import create_business


@pytest.mark.asyncio
@patch('entity_digital_credentials.digital_credentials_processors.put_back_on.get_issued_digital_credentials',
       return_value=[])
@patch('entity_digital_credentials.digital_credentials_processors.put_back_on.logger')
@patch('entity_digital_credentials.digital_credentials_processors.put_back_on.revoke_digital_credential')
async def test_processor_does_not_run_if_no_issued_credential(mock_revoke_digital_credential,
                                                              mock_logger,
                                                              mock_get_issued_digital_credentials,
                                                              app, session):
    """Assert that the processor does not run if the current business has no issued credentials."""
    # Arrange
    business = create_business(identifier='FM0000001')

    # Act
    await process(business)

    # Assert
    mock_get_issued_digital_credentials.assert_called_once_with(
        business=business)
    mock_logger.warning.assert_called_once_with(
        'No issued credentials found for business: %s', 'FM0000001')
    mock_revoke_digital_credential.assert_not_called()


@pytest.mark.asyncio
@patch('entity_digital_credentials.digital_credentials_processors.put_back_on.get_issued_digital_credentials',
       return_value=[{'id': 1}])
@patch('entity_digital_credentials.digital_credentials_processors.put_back_on.revoke_digital_credential')
async def test_processor_revokes_issued_credential(mock_revoke_digital_credential,
                                                   mock_get_issued_digital_credentials,
                                                   app, session):
    """Assert that the processor revokes the issued credential if it exists."""
    # Arrange
    business = create_business(identifier='FM0000001')

    # Act
    await process(business)

    # Assert
    mock_get_issued_digital_credentials.assert_called_once_with(
        business=business)
    mock_revoke_digital_credential.assert_called_once_with(
        issued_credential={'id': 1}, reason=DCRevocationReason.PUT_BACK_ON)
