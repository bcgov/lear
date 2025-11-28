# Copyright © 2025 Province of British Columbia
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
"""Tests for the auth_unaffiliation processor."""
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_user():
    """Create a mock User object."""
    user = MagicMock()
    user.id = 123
    user.display_name = "Test User"
    user.idp_userid = "TEST_IDP_USERID"
    return user


@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.User")
def test_process_user_found(mock_user_class, app, mock_user):
    """Test process when user is found."""
    from business_digital_credentials.digital_credential_processors import auth_unaffiliation
    
    with app.app_context():
        mock_user_class.find_by_jwt_token.return_value = mock_user
        
        idp_userid = "TEST_IDP_USERID"
        unaffiliated_identifiers = ["FM1169745", "BC0888356"]
        
        # Should not raise any exceptions
        auth_unaffiliation.process(idp_userid, unaffiliated_identifiers)
        
        # Verify User.find_by_jwt_token was called with correct token
        mock_user_class.find_by_jwt_token.assert_called_once_with({"idp_userid": idp_userid})


@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.User")
def test_process_user_not_found(mock_user_class, app):
    """Test process when user is not found."""
    from business_digital_credentials.digital_credential_processors import auth_unaffiliation
    
    with app.app_context():
        mock_user_class.find_by_jwt_token.return_value = None
        
        idp_userid = "NONEXISTENT_USER"
        unaffiliated_identifiers = ["FM1169745"]
        
        # Should return early without raising exceptions
        auth_unaffiliation.process(idp_userid, unaffiliated_identifiers)
        
        mock_user_class.find_by_jwt_token.assert_called_once_with({"idp_userid": idp_userid})


@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.User")
def test_process_with_multiple_identifiers(mock_user_class, app, mock_user):
    """Test process with multiple unaffiliated identifiers."""
    from business_digital_credentials.digital_credential_processors import auth_unaffiliation
    
    with app.app_context():
        mock_user_class.find_by_jwt_token.return_value = mock_user
        
        idp_userid = "TEST_IDP_USERID"
        unaffiliated_identifiers = [
            "FM1169745", "BC0888356", "FM1169770", 
            "BC0887882", "C9900913"
        ]
        
        auth_unaffiliation.process(idp_userid, unaffiliated_identifiers)
        
        mock_user_class.find_by_jwt_token.assert_called_once()


@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.User")
def test_process_with_single_identifier(mock_user_class, app, mock_user):
    """Test process with single unaffiliated identifier."""
    from business_digital_credentials.digital_credential_processors import auth_unaffiliation
    
    with app.app_context():
        mock_user_class.find_by_jwt_token.return_value = mock_user
        
        idp_userid = "TEST_IDP_USERID"
        unaffiliated_identifiers = ["FM1169745"]
        
        auth_unaffiliation.process(idp_userid, unaffiliated_identifiers)
        
        mock_user_class.find_by_jwt_token.assert_called_once_with({"idp_userid": idp_userid})


@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.User")
def test_process_with_empty_identifiers_list(mock_user_class, app, mock_user):
    """Test process handles empty identifiers list."""
    from business_digital_credentials.digital_credential_processors import auth_unaffiliation
    
    with app.app_context():
        mock_user_class.find_by_jwt_token.return_value = mock_user
        
        idp_userid = "TEST_IDP_USERID"
        unaffiliated_identifiers = []
        
        # Should not raise exceptions with empty list
        auth_unaffiliation.process(idp_userid, unaffiliated_identifiers)
        
        mock_user_class.find_by_jwt_token.assert_called_once_with({"idp_userid": idp_userid})


@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.revoke_digital_credential")
@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.get_all_digital_credentials_for_business")
@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.Business")
@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.User")
def test_process_business_not_found(mock_user_class, mock_business_class, mock_get_credentials, mock_revoke, app, mock_user):
    """Test process when business is not found for identifier."""
    from business_digital_credentials.digital_credential_processors import auth_unaffiliation
    
    with app.app_context():
        mock_user_class.find_by_jwt_token.return_value = mock_user
        mock_business_class.find_by_identifier.return_value = None
        
        idp_userid = "TEST_IDP_USERID"
        unaffiliated_identifiers = ["NONEXISTENT_BUSINESS"]
        
        auth_unaffiliation.process(idp_userid, unaffiliated_identifiers)
        
        mock_business_class.find_by_identifier.assert_called_once_with("NONEXISTENT_BUSINESS")
        mock_get_credentials.assert_not_called()
        mock_revoke.assert_not_called()


@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.revoke_digital_credential")
@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.get_all_digital_credentials_for_business")
@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.Business")
@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.User")
def test_process_no_credentials_found(mock_user_class, mock_business_class, mock_get_credentials, mock_revoke, app, mock_user):
    """Test process when no credentials found for business."""
    from business_digital_credentials.digital_credential_processors import auth_unaffiliation
    
    with app.app_context():
        mock_user_class.find_by_jwt_token.return_value = mock_user
        
        mock_business = MagicMock()
        mock_business_class.find_by_identifier.return_value = mock_business
        mock_get_credentials.return_value = []
        
        idp_userid = "TEST_IDP_USERID"
        unaffiliated_identifiers = ["FM1169745"]
        
        auth_unaffiliation.process(idp_userid, unaffiliated_identifiers)
        
        mock_get_credentials.assert_called_once_with(mock_business)
        mock_revoke.assert_not_called()


@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.revoke_digital_credential")
@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.get_all_digital_credentials_for_business")
@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.Business")
@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.User")
def test_process_credential_belongs_to_different_user(mock_user_class, mock_business_class, mock_get_credentials, mock_revoke, app, mock_user):
    """Test process when credential belongs to different user."""
    from business_digital_credentials.digital_credential_processors import auth_unaffiliation
    
    with app.app_context():
        mock_user_class.find_by_jwt_token.return_value = mock_user
        
        mock_business = MagicMock()
        mock_business_class.find_by_identifier.return_value = mock_business
        
        # Create credential belonging to different user
        mock_credential = MagicMock()
        mock_credential.id = 456
        mock_credential.connection.business_user.user.id = 999  # Different user ID
        mock_get_credentials.return_value = [mock_credential]
        
        idp_userid = "TEST_IDP_USERID"
        unaffiliated_identifiers = ["FM1169745"]
        
        auth_unaffiliation.process(idp_userid, unaffiliated_identifiers)
        
        mock_get_credentials.assert_called_once_with(mock_business)
        mock_revoke.assert_not_called()


@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.revoke_digital_credential")
@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.get_all_digital_credentials_for_business")
@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.Business")
@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.User")
def test_process_revokes_user_credential(mock_user_class, mock_business_class, mock_get_credentials, mock_revoke, app, mock_user):
    """Test process successfully revokes credential for matching user."""
    from business_digital_credentials.digital_credential_processors import auth_unaffiliation
    from business_model.models import DCRevocationReason
    
    with app.app_context():
        mock_user_class.find_by_jwt_token.return_value = mock_user
        
        mock_business = MagicMock()
        mock_business_class.find_by_identifier.return_value = mock_business
        
        # Create credential belonging to the user
        mock_credential = MagicMock()
        mock_credential.id = 456
        mock_credential.connection.business_user.user.id = 123  # Matches mock_user.id
        mock_get_credentials.return_value = [mock_credential]
        
        idp_userid = "TEST_IDP_USERID"
        unaffiliated_identifiers = ["FM1169745"]
        
        auth_unaffiliation.process(idp_userid, unaffiliated_identifiers)
        
        mock_get_credentials.assert_called_once_with(mock_business)
        mock_revoke.assert_called_once_with(
            credential=mock_credential,
            reason=DCRevocationReason.AUTH_UNAFFILIATED
        )


@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.revoke_digital_credential")
@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.get_all_digital_credentials_for_business")
@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.Business")
@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.User")
def test_process_revokes_multiple_credentials(mock_user_class, mock_business_class, mock_get_credentials, mock_revoke, app, mock_user):
    """Test process revokes multiple credentials across multiple businesses."""
    from business_digital_credentials.digital_credential_processors import auth_unaffiliation
    from business_model.models import DCRevocationReason
    
    with app.app_context():
        mock_user_class.find_by_jwt_token.return_value = mock_user
        
        # Setup multiple businesses
        mock_business1 = MagicMock()
        mock_business2 = MagicMock()
        mock_business_class.find_by_identifier.side_effect = [mock_business1, mock_business2]
        
        # Create credentials for each business
        mock_credential1 = MagicMock()
        mock_credential1.id = 456
        mock_credential1.connection.business_user.user.id = 123
        
        mock_credential2 = MagicMock()
        mock_credential2.id = 789
        mock_credential2.connection.business_user.user.id = 123
        
        mock_get_credentials.side_effect = [[mock_credential1], [mock_credential2]]
        
        idp_userid = "TEST_IDP_USERID"
        unaffiliated_identifiers = ["FM1169745", "BC0888356"]
        
        auth_unaffiliation.process(idp_userid, unaffiliated_identifiers)
        
        assert mock_revoke.call_count == 2
        mock_revoke.assert_any_call(
            credential=mock_credential1,
            reason=DCRevocationReason.AUTH_UNAFFILIATED
        )
        mock_revoke.assert_any_call(
            credential=mock_credential2,
            reason=DCRevocationReason.AUTH_UNAFFILIATED
        )


@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.revoke_digital_credential")
@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.get_all_digital_credentials_for_business")
@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.Business")
@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.User")
def test_process_continues_on_credential_error(mock_user_class, mock_business_class, mock_get_credentials, mock_revoke, app, mock_user):
    """Test process continues processing other credentials when one fails."""
    from business_digital_credentials.digital_credential_processors import auth_unaffiliation
    from business_model.models import DCRevocationReason
    
    with app.app_context():
        mock_user_class.find_by_jwt_token.return_value = mock_user
        
        mock_business = MagicMock()
        mock_business_class.find_by_identifier.return_value = mock_business
        
        # Create two credentials, first will error
        mock_credential1 = MagicMock()
        mock_credential1.id = 456
        mock_credential1.connection.business_user.user.id = 123
        
        mock_credential2 = MagicMock()
        mock_credential2.id = 789
        mock_credential2.connection.business_user.user.id = 123
        
        mock_get_credentials.return_value = [mock_credential1, mock_credential2]
        
        # First revoke raises exception, second should still be called
        mock_revoke.side_effect = [Exception("Revoke failed"), None]
        
        idp_userid = "TEST_IDP_USERID"
        unaffiliated_identifiers = ["FM1169745"]
        
        # Should not raise exception
        auth_unaffiliation.process(idp_userid, unaffiliated_identifiers)
        
        # Both credentials should have been attempted
        assert mock_revoke.call_count == 2


@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.revoke_digital_credential")
@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.get_all_digital_credentials_for_business")
@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.Business")
@patch("business_digital_credentials.digital_credential_processors.auth_unaffiliation.User")
def test_process_mixed_credentials(mock_user_class, mock_business_class, mock_get_credentials, mock_revoke, app, mock_user):
    """Test process with mix of user's and other users' credentials."""
    from business_digital_credentials.digital_credential_processors import auth_unaffiliation
    from business_model.models import DCRevocationReason
    
    with app.app_context():
        mock_user_class.find_by_jwt_token.return_value = mock_user
        
        mock_business = MagicMock()
        mock_business_class.find_by_identifier.return_value = mock_business
        
        # Create mix of credentials
        mock_credential1 = MagicMock()
        mock_credential1.id = 456
        mock_credential1.connection.business_user.user.id = 123  # User's credential
        
        mock_credential2 = MagicMock()
        mock_credential2.id = 789
        mock_credential2.connection.business_user.user.id = 999  # Other user's credential
        
        mock_credential3 = MagicMock()
        mock_credential3.id = 101
        mock_credential3.connection.business_user.user.id = 123  # User's credential
        
        mock_get_credentials.return_value = [mock_credential1, mock_credential2, mock_credential3]
        
        idp_userid = "TEST_IDP_USERID"
        unaffiliated_identifiers = ["FM1169745"]
        
        auth_unaffiliation.process(idp_userid, unaffiliated_identifiers)
        
        # Only user's credentials should be revoked
        assert mock_revoke.call_count == 2
        mock_revoke.assert_any_call(
            credential=mock_credential1,
            reason=DCRevocationReason.AUTH_UNAFFILIATED
        )
        mock_revoke.assert_any_call(
            credential=mock_credential3,
            reason=DCRevocationReason.AUTH_UNAFFILIATED
        )
