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
"""Tests for the helper functions are contained here."""


from unittest.mock import patch

import pytest
from legal_api.models import (
    DCConnection,
    DCDefinition,
    DCIssuedBusinessUserCredential,
    DCIssuedCredential,
    DCRevocationReason,
    User,
)

from entity_digital_credentials.helpers import (
    get_issued_digital_credentials,
    issue_digital_credential,
    replace_issued_digital_credential,
    revoke_issued_digital_credential,
)
from tests.unit import create_business, create_dc_connection, create_dc_definition, create_dc_issued_credential


BUSINESS_IDENTIFIER = 'FM0000001'


@patch('legal_api.models.DCIssuedCredential.find_by', return_value=DCIssuedCredential(id=1))
@patch('legal_api.models.DCConnection.find_active_by', return_value=None)
def test_get_issued_digital_credentials_raises_exception(mock_find_active_by, mock_find_by, app, session):
    """Assert get_issued_digital_credentials raises an exception when no active connection found."""
    # Arrange
    business = create_business(identifier=BUSINESS_IDENTIFIER)

    # Act
    with pytest.raises(Exception) as excinfo:
        get_issued_digital_credentials(business=business)

    # Assert
    assert f'{BUSINESS_IDENTIFIER} active connection not found.' in str(excinfo)


@patch('legal_api.models.DCIssuedCredential.find_by', return_value=None)
@patch('legal_api.models.DCConnection.find_active_by', return_value=DCConnection(id=1))
def test_get_issued_credentials_returns_empty_list(mock_find_active_by, mock_find_by, app, session):
    """Assert get_issued_digital_credentials returns an empty list when no issued credentials found."""
    # Arrange
    business = create_business(identifier=BUSINESS_IDENTIFIER)

    # Act
    issued_credentials = get_issued_digital_credentials(business=business)

    # Assert
    assert issued_credentials == []


@patch('legal_api.services.digital_credentials.revoke_credential')
def test_issued_credential_not_issued_not_revoked(mock_revoke_credential, app, session):
    """Assert that the issued credential is not revoked if is not yet issued."""
    # Arrange
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    issued_credential = create_dc_issued_credential(business=business, is_issued=False)

    # Act
    with pytest.raises(Exception) as excinfo:
        revoke_issued_digital_credential(business=business,
                                         issued_credential=issued_credential,
                                         reason=DCRevocationReason.UPDATED_INFORMATION)
    # Assert
    assert 'Credential is not issued yet or is revoked already.' in str(excinfo)
    mock_revoke_credential.assert_not_called()


@patch('legal_api.services.digital_credentials.revoke_credential')
def test_issued_credential_already_revoked_not_revoked(mock_revoke_credential, app, session):
    """Assert that the issued credential is not revoked if already revoked."""
    # Arrange
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    issued_credential = create_dc_issued_credential(business=business, is_issued=True, is_revoked=True)

    # Act
    with pytest.raises(Exception) as excinfo:
        revoke_issued_digital_credential(business=business,
                                         issued_credential=issued_credential,
                                         reason=DCRevocationReason.UPDATED_INFORMATION)
    # Assert
    assert 'Credential is not issued yet or is revoked already.' in str(excinfo)
    mock_revoke_credential.assert_not_called()


@patch('legal_api.models.DCConnection.find_active_by', return_value=None)
@patch('legal_api.services.digital_credentials.revoke_credential')
def test_issued_credential_no_active_connection_not_revoked(mock_revoke_credential, mock_find_active_by,
                                                            app, session):
    """Assert that the issued credential is not revoked if no active connection found."""
    # Arrange
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    issued_credential = create_dc_issued_credential(business=business, is_issued=True, is_revoked=False)

    # Act
    with pytest.raises(Exception) as excinfo:
        revoke_issued_digital_credential(business=business,
                                         issued_credential=issued_credential,
                                         reason=DCRevocationReason.UPDATED_INFORMATION)
    # Assert
    assert f'{BUSINESS_IDENTIFIER} active connection not found.' in str(excinfo)
    mock_revoke_credential.assert_not_called()


@patch('legal_api.services.digital_credentials.revoke_credential', return_value=None)
def test_revoke_issued_digital_credential_helper_throws_exception(mock_revoke_credential, app, session):
    """Assert that the revoke issued credential helper throws an exception if the service fails."""
    # Arrange
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    issued_credential = create_dc_issued_credential(business=business, is_issued=True, is_revoked=False)

    # Act
    with pytest.raises(Exception) as excinfo:
        revoke_issued_digital_credential(business=business,
                                         issued_credential=issued_credential,
                                         reason=DCRevocationReason.UPDATED_INFORMATION)

    # Assert
    assert 'Failed to revoke credential.' in str(excinfo)
    assert issued_credential.is_revoked is False


@patch('legal_api.services.digital_credentials.revoke_credential', return_value={})
def test_issued_credential_revoked(mock_revoke_credential, app, session):
    """Assert that the issued credential is revoked."""
    # Arrange
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    issued_credential = create_dc_issued_credential(business=business, is_issued=True, is_revoked=False)

    # Act
    revoke_issued_digital_credential(business=business,
                                     issued_credential=issued_credential,
                                     reason=DCRevocationReason.UPDATED_INFORMATION)

    # Assert
    assert issued_credential.is_revoked is True


@patch('entity_digital_credentials.helpers.issue_digital_credential', return_value=None)
@patch('legal_api.services.digital_credentials.fetch_credential_exchange_record', return_value=None)
@patch('legal_api.models.User.find_by_id', return_value=User(id=1))
@patch('legal_api.models.DCIssuedBusinessUserCredential.find_by_id',
       return_value=DCIssuedBusinessUserCredential(id=1, user_id=1))
@patch('entity_digital_credentials.helpers.revoke_issued_digital_credential')
def test_issued_credential_not_revoked_is_revoked_first(mock_revoke_credential,
                                                        mock_find_ibuc_by_id,
                                                        mock_find_user_by_id,
                                                        mock_fetch_credential_exchange_record,
                                                        mock_issue_digital_credential,
                                                        app, session):
    """Assert that the issued credential is revoked first if its not revoked before replacing."""
    # Arrange
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    issued_credential = create_dc_issued_credential(business=business, is_issued=True, is_revoked=False)
    reason = DCRevocationReason.UPDATED_INFORMATION

    # Act
    replace_issued_digital_credential(business=business,
                                      issued_credential=issued_credential,
                                      credential_type=DCDefinition.CredentialType.business.name,
                                      reason=reason)

    # Assert
    mock_revoke_credential.assert_called_once_with(business, issued_credential, reason)


@patch('entity_digital_credentials.helpers.issue_digital_credential', return_value=None)
@patch('legal_api.services.digital_credentials.fetch_credential_exchange_record', return_value=None)
@patch('legal_api.models.User.find_by_id', return_value=User(id=1))
@patch('legal_api.models.DCIssuedBusinessUserCredential.find_by_id',
       return_value=DCIssuedBusinessUserCredential(id=1, user_id=1))
@patch('entity_digital_credentials.helpers.revoke_issued_digital_credential')
def test_issued_credential_revoked_is_not_revoked_first(mock_revoke_credential,
                                                        mock_find_ibuc_by_id,
                                                        mock_find_user_by_id,
                                                        mock_fetch_credential_exchange_record,
                                                        mock_issue_digital_credential,
                                                        app, session):
    """Assert that the issued credential is not revoked first if its already revoked before replacing."""
    # Arrange
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    issued_credential = create_dc_issued_credential(business=business, is_issued=True, is_revoked=True)
    reason = DCRevocationReason.UPDATED_INFORMATION

    # Act
    replace_issued_digital_credential(business=business,
                                      issued_credential=issued_credential,
                                      credential_type=DCDefinition.CredentialType.business.name,
                                      reason=reason)

    # Assert
    mock_revoke_credential.assert_not_called()


@patch('entity_digital_credentials.helpers.issue_digital_credential')
@patch('legal_api.services.digital_credentials.fetch_credential_exchange_record',
       return_value='test_credential_exchange_id')
@patch('legal_api.services.digital_credentials.remove_credential_exchange_record', return_value=None)
def test_replace_issued_digital_credential_throws_cred_ex_id_exception(mock_remove_credential_exchange_record,
                                                                       mock_fetch_credential_exchange_record,
                                                                       mock_issue_digital_credential,
                                                                       app, session):
    """
    Assert the digital credential credential service throws an exception.

    An exception should be thrown if the service fails to remove a credential exchange id.
    """
    # Arrange
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    issued_credential = create_dc_issued_credential(business=business, is_issued=True, is_revoked=True)
    reason = DCRevocationReason.UPDATED_INFORMATION

    # Act
    with pytest.raises(Exception) as excinfo:
        replace_issued_digital_credential(business=business,
                                          issued_credential=issued_credential,
                                          credential_type=DCDefinition.CredentialType.business.name,
                                          reason=reason)

    # Assert
    assert 'Failed to remove credential exchange record.' in str(excinfo)
    mock_issue_digital_credential.assert_not_called()


@patch('entity_digital_credentials.helpers.issue_digital_credential')
@patch('legal_api.services.digital_credentials.fetch_credential_exchange_record', return_value=None)
@patch('legal_api.models.DCIssuedBusinessUserCredential.find_by_id', return_value=None)
def test_replace_issued_digital_credential_throws_ibuc_not_found_exception(mock_find_ibuc_by_id,
                                                                           mock_fetch_credential_exchange_record,
                                                                           mock_issue_digital_credential,
                                                                           app, session):
    """
    Assert the digital credential credential service throws an exception.

    An exception should be thrown if the issued business user credential is not found.
    """
    # Arrange
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    issued_credential = create_dc_issued_credential(business=business, is_issued=True, is_revoked=True)
    reason = DCRevocationReason.UPDATED_INFORMATION

    # Act
    with pytest.raises(Exception) as excinfo:
        replace_issued_digital_credential(business=business,
                                          issued_credential=issued_credential,
                                          credential_type=DCDefinition.CredentialType.business.name,
                                          reason=reason)

    # Assert
    assert 'Unable to find business user for issued credential.' in str(excinfo)
    mock_issue_digital_credential.assert_not_called()


@patch('entity_digital_credentials.helpers.issue_digital_credential')
@patch('legal_api.services.digital_credentials.fetch_credential_exchange_record', return_value=None)
@patch('legal_api.models.User.find_by_id', return_value=None)
@patch('legal_api.models.DCIssuedBusinessUserCredential.find_by_id',
       return_value=DCIssuedBusinessUserCredential(id=1, user_id=1))
def test_replace_issued_digital_credential_throws_user_not_found_exception(mock_find_ibuc_by_id,
                                                                           mock_find_user_by_id,
                                                                           mock_fetch_credential_exchange_record,
                                                                           mock_issue_digital_credential,
                                                                           app, session):
    """
    Assert the digital credential credential service throws an exception.

    An exception should be thrown if the user is not found.
    """
    # Arrange
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    issued_credential = create_dc_issued_credential(business=business, is_issued=True, is_revoked=True)
    reason = DCRevocationReason.UPDATED_INFORMATION

    # Act
    with pytest.raises(Exception) as excinfo:
        replace_issued_digital_credential(business=business,
                                          issued_credential=issued_credential,
                                          credential_type=DCDefinition.CredentialType.business.name,
                                          reason=reason)

    # Assert
    assert 'Unable to find user for issued business user credential.' in str(excinfo)
    mock_issue_digital_credential.assert_not_called()


@patch('entity_digital_credentials.helpers.issue_digital_credential', return_value=None)
@patch('legal_api.services.digital_credentials.fetch_credential_exchange_record', return_value=None)
@patch('legal_api.models.User.find_by_id', return_value=User(id=1))
@patch('legal_api.models.DCIssuedBusinessUserCredential.find_by_id',
       return_value=DCIssuedBusinessUserCredential(id=1, user_id=1))
def test_issued_credential_replaced(mock_find_ibuc_by_id,
                                    mock_find_user_by_id,
                                    mock_fetch_credential_exchange_record,
                                    mock_issue_digital_credential,
                                    app, session):
    """Assert that the issued credential is deleted and replaced with a new one."""
    # Arrange
    user = User.find_by_id(1)
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    issued_credential = create_dc_issued_credential(business=business, is_issued=True, is_revoked=True)
    credential_type = DCDefinition.CredentialType.business.name
    reason = DCRevocationReason.UPDATED_INFORMATION

    # Act
    replace_issued_digital_credential(business=business,
                                      issued_credential=issued_credential,
                                      credential_type=credential_type,
                                      reason=reason)

    # Assert
    assert DCIssuedCredential.find_by_id(issued_credential.id) is None
    mock_issue_digital_credential.assert_called_once_with(business, user, credential_type)


@patch('legal_api.models.DCDefinition.find_by', return_value=None)
def test_issue_digital_credential_throws_definition_not_found_error(mock_find_definition_by, app, session):
    """Assert that the issue_digital_credential helper throws an exception if the definition is not found."""
    # Arrange
    user = User(id=1)
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    definition = create_dc_definition()

    # Act
    with pytest.raises(Exception) as excinfo:
        issue_digital_credential(business=business, user=user, credential_type=definition.credential_type.name)

    # Assert
    assert 'Definition not found for credential type: business.' in str(excinfo)


@patch('legal_api.models.DCConnection.find_active_by', return_value=None)
@patch('entity_digital_credentials.helpers.digital_credentials')
def test_issue_digital_credential_throws_active_connection_not_found_error(mock_digital_credentials,
                                                                           mock_find_active_by,
                                                                           app, session):
    """Assert that the issue_digital_credential helper throws an exception if the definition is not found."""
    # Arrange
    mock_digital_credentials.business_schema_id = 'test_schema_id'
    mock_digital_credentials.business_cred_def_id = 'test_credential_definition_id'
    user = User(id=1)
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    definition = create_dc_definition()

    # Act
    with pytest.raises(Exception) as excinfo:
        issue_digital_credential(business=business, user=user, credential_type=definition.credential_type.name)

    # Assert
    assert f'{BUSINESS_IDENTIFIER} active connection not found.' in str(excinfo)


@patch('entity_digital_credentials.helpers.digital_credentials')
@patch('entity_digital_credentials.helpers.DigitalCredentialsHelpers.get_digital_credential_data', return_value=[{
    'name': 'credential_id',
    'value': '00000001'
}])
def test_issue_digital_credential_throws_exception_on_failure(mock_digital_credentials_helpers,
                                                              mock_digital_credentials,
                                                              app, session):
    """Assert that the issue_digital_credential helper throws an exception if the service fails."""
    # Arrange
    mock_digital_credentials.issue_credential.return_value = None
    mock_digital_credentials.business_schema_id = 'test_schema_id'
    mock_digital_credentials.business_cred_def_id = 'test_credential_definition_id'
    user = User(id=1)
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    definition = create_dc_definition()
    create_dc_connection(business=business, is_active=True)

    # Act
    with pytest.raises(Exception) as excinfo:
        issue_digital_credential(business=business, user=user, credential_type=definition.credential_type.name)

    # Assert
    assert 'Failed to issue credential.' in str(excinfo)


@patch('entity_digital_credentials.helpers.digital_credentials')
@patch('entity_digital_credentials.helpers.DigitalCredentialsHelpers.get_digital_credential_data', return_value=[{
    'name': 'credential_id',
    'value': '00000001'
}])
def test_issue_digital_credential(mock_digital_credentials_helpers,
                                  mock_digital_credentials,
                                  app, session):
    """Assert that the issue_digital_credential helper issues a credential."""
    # Arrange
    mock_digital_credentials.issue_credential.return_value = {'cred_ex_id': 'test_credential_exchange_id'}
    mock_digital_credentials.business_schema_id = 'test_schema_id'
    mock_digital_credentials.business_cred_def_id = 'test_credential_definition_id'
    user = User(id=1)
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    definition = create_dc_definition()
    connection = create_dc_connection(business=business, is_active=True)

    # Act
    issued_credential = issue_digital_credential(business=business,
                                                 user=user,
                                                 credential_type=definition.credential_type.name)

    # Assert
    assert issued_credential.credential_exchange_id == 'test_credential_exchange_id'
    assert issued_credential.credential_id == '00000001'
    assert issued_credential.dc_definition_id == definition.id
    assert issued_credential.dc_connection_id == connection.id
