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
"""Tests for the change of registration processor are contained here."""

from unittest.mock import patch

import pytest
from legal_api.models import DCDefinition, DCRevocationReason, Filing

from entity_digital_credentials.digital_credentials_processors.change_of_registration import process
from tests.unit import create_business, create_filing


@pytest.mark.asyncio
@patch('entity_digital_credentials.digital_credentials_processors' +
       '.change_of_registration.get_issued_digital_credentials',
       return_value=[])
@patch('entity_digital_credentials.digital_credentials_processors.change_of_registration.logger')
@patch('entity_digital_credentials.digital_credentials_processors.' +
       'change_of_registration.replace_issued_digital_credential')
async def test_processor_does_not_run_if_no_issued_credential(mock_replace_issued_digital_credential,
                                                              mock_logger,
                                                              mock_get_issued_digital_credentials,
                                                              app, session):
    """Assert that the processor does not run if the current business has no issued credentials."""
    # Arrange
    business = create_business(identifier='FM0000001')
    filing = create_filing(session, business.id, {
        'filing': {
            'header': {
                'name': 'changeOfRegistration',
                'filingId': None
            },
            'changeOfRegistration': {
                'nameRequest': {}
            }
        }}, 'test', Filing.Status.COMPLETED.value)

    # Act
    await process(business, filing)

    # Assert
    mock_get_issued_digital_credentials.assert_called_once_with(business=business)
    mock_logger.warning.assert_called_once_with('No issued credentials found for business: %s', 'FM0000001')
    mock_replace_issued_digital_credential.assert_not_called()


@pytest.mark.asyncio
@patch('entity_digital_credentials.digital_credentials_processors' +
       '.change_of_registration.get_issued_digital_credentials',
       return_value=[{'id': 1}])
@patch('entity_digital_credentials.digital_credentials_processors' +
       '.change_of_registration.replace_issued_digital_credential')
async def test_processor_does_not_run_if_invalid_typel(mock_replace_issued_digital_credential,
                                                       mock_get_issued_digital_credentials,
                                                       app, session):
    """Assert that the processor does not run if not the right type."""
    # Arrange
    business = create_business(identifier='FM0000001')
    filing = create_filing(session, business.id, {
        'filing': {
            'header': {
                'name': 'changeOfRegistration',
                'filingId': None
            },
            'changeOfRegistration': {
                'test': {}
            }
        }}, 'changeOfRegistration', Filing.Status.COMPLETED.value)

    # Act
    await process(business, filing)

    # Assert
    mock_get_issued_digital_credentials.assert_not_called()
    mock_replace_issued_digital_credential.assert_not_called()


@pytest.mark.asyncio
@patch('entity_digital_credentials.digital_credentials_processors' +
       '.change_of_registration.get_issued_digital_credentials',
       return_value=[{'id': 1}])
@patch('entity_digital_credentials.digital_credentials_processors' +
       '.change_of_registration.replace_issued_digital_credential')
async def test_processor_replaces_issued_credential(mock_replace_issued_digital_credential,
                                                    mock_get_issued_digital_credentials,
                                                    app, session):
    """Assert that the processor replaces the issued credential if it exists."""
    # Arrange
    business = create_business(identifier='FM0000001')
    filing = create_filing(session, business.id, {
        'filing': {
            'header': {
                'name': 'changeOfRegistration',
                'filingId': None
            },
            'changeOfRegistration': {
                'nameRequest': {}
            }
        }}, 'changeOfRegistration', Filing.Status.COMPLETED.value)

    # Act
    await process(business, filing)

    # Assert
    mock_get_issued_digital_credentials.assert_called_once_with(business=business)
    mock_replace_issued_digital_credential.assert_called_once_with(
        business=business,
        issued_credential={'id': 1},
        credential_type=DCDefinition.CredentialType.business.name,
        reason=DCRevocationReason.UPDATED_INFORMATION)
