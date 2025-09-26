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
"""Tests for the change of registration processor are contained here."""

from unittest.mock import MagicMock, patch

from business_model.models import DCDefinition, DCRevocationReason

from business_digital_credentials.digital_credential_processors import change_of_registration
from tests.unit import create_business, create_filing, create_user


@patch.object(change_of_registration, 'get_all_digital_credentials_for_business', return_value=[])
@patch.object(change_of_registration, 'replace_digital_credential')
@patch.object(change_of_registration, 'revoke_digital_credential')
def test_processor_does_not_run_if_no_issued_credential(mock_revoke_digital_credential,
                                                              mock_replace_digital_credential,
                                                              mock_get_all_digital_credentials_for_business,
                                                              app, session):
    """Assert that the processor does not run if the current business has no issued credentials."""
    business = create_business(identifier='FM0000001')
    filing = create_filing(filing_json={
        'filing': {
            'header': {
                'name': 'changeOfRegistration',
                'filingId': None
            },
            'changeOfRegistration': {
                'nameRequest': {}
            }
        }}, business_id=business.id)

    change_of_registration.process(business, filing)

    mock_get_all_digital_credentials_for_business.assert_called_once_with(
        business=business)
    mock_replace_digital_credential.assert_not_called()
    mock_revoke_digital_credential.assert_not_called()


@patch.object(change_of_registration, 'get_all_digital_credentials_for_business')
@patch.object(change_of_registration, 'is_user_in_officers', return_value=True)
@patch.object(change_of_registration, 'replace_digital_credential')
@patch.object(change_of_registration, 'revoke_digital_credential')
def test_processor_skips_credential_with_no_user(mock_revoke_digital_credential,
                                                mock_replace_digital_credential,
                                                mock_is_user_in_officers,
                                                mock_get_all_digital_credentials_for_business,
                                                app, session):
    """Assert that the processor skips credentials with no associated user."""
    business = create_business(identifier='FM0000001')
    filing = create_filing(filing_json={
        'filing': {
            'header': {
                'name': 'changeOfRegistration',
                'filingId': None
            },
            'changeOfRegistration': {
                'nameRequest': {}
            }
        }}, business_id=business.id)
    
    # Create mock credential with no connection/business_user/user
    mock_credential = MagicMock()
    mock_credential.id = 1
    mock_credential.connection = None
    mock_get_all_digital_credentials_for_business.return_value = [mock_credential]

    change_of_registration.process(business, filing)

    mock_get_all_digital_credentials_for_business.assert_called_once_with(business=business)
    mock_is_user_in_officers.assert_not_called()
    mock_replace_digital_credential.assert_not_called()
    mock_revoke_digital_credential.assert_not_called()


@patch.object(change_of_registration, 'get_all_digital_credentials_for_business')
@patch.object(change_of_registration, 'is_user_in_officers', return_value=True)
@patch.object(change_of_registration, 'replace_digital_credential')
@patch.object(change_of_registration, 'revoke_digital_credential')
def test_processor_replaces_credential_when_user_in_parties_and_name_request(mock_revoke_digital_credential,
                                                                           mock_replace_digital_credential,
                                                                           mock_is_user_in_officers,
                                                                           mock_get_all_digital_credentials_for_business,
                                                                           app, session):
    """Assert that the processor replaces credential when user is in parties and name request exists."""
    business = create_business(identifier='FM0000001')
    filing = create_filing(filing_json={
        'filing': {
            'header': {
                'name': 'changeOfRegistration',
                'filingId': None
            },
            'changeOfRegistration': {
                'nameRequest': {
                    'legalName': 'New Company Name'
                }
            }
        }}, business_id=business.id)
    
    user = create_user()
    mock_credential = MagicMock()
    mock_credential.id = 1
    mock_credential.connection.business_user.user = user
    mock_get_all_digital_credentials_for_business.return_value = [mock_credential]

    change_of_registration.process(business, filing)

    mock_get_all_digital_credentials_for_business.assert_called_once_with(business=business)
    filing_data = filing.filing_json.get("filing", {}).get(filing.filing_type, {})
    mock_is_user_in_officers.assert_called_once_with(user, filing_data, 'Partner')
    mock_replace_digital_credential.assert_called_once_with(
        credential=mock_credential,
        credential_type=DCDefinition.CredentialType.business.name,
        reason=DCRevocationReason.UPDATED_INFORMATION
    )
    mock_revoke_digital_credential.assert_not_called()


@patch.object(change_of_registration, 'get_all_digital_credentials_for_business')
@patch.object(change_of_registration, 'is_user_in_officers', return_value=True)
@patch.object(change_of_registration, 'replace_digital_credential')
@patch.object(change_of_registration, 'revoke_digital_credential')
def test_processor_does_not_replace_when_user_in_parties_but_no_name_request(mock_revoke_digital_credential,
                                                                            mock_replace_digital_credential,
                                                                            mock_is_user_in_officers,
                                                                            mock_get_all_digital_credentials_for_business,
                                                                            app, session):
    """Assert that the processor does not replace credential when user is in parties but no name request."""
    business = create_business(identifier='FM0000001')
    filing = create_filing(filing_json={
        'filing': {
            'header': {
                'name': 'changeOfRegistration',
                'filingId': None
            },
            'changeOfRegistration': {
                'parties': []
            }
        }}, business_id=business.id)
    
    user = create_user()
    mock_credential = MagicMock()
    mock_credential.id = 1
    mock_credential.connection.business_user.user = user
    mock_get_all_digital_credentials_for_business.return_value = [mock_credential]

    change_of_registration.process(business, filing)

    mock_get_all_digital_credentials_for_business.assert_called_once_with(business=business)
    filing_data = filing.filing_json.get("filing", {}).get(filing.filing_type, {})
    mock_is_user_in_officers.assert_called_once_with(user, filing_data, 'Partner')
    mock_replace_digital_credential.assert_not_called()
    mock_revoke_digital_credential.assert_not_called()


@patch.object(change_of_registration, 'get_all_digital_credentials_for_business')
@patch.object(change_of_registration, 'is_user_in_officers', return_value=False)
@patch.object(change_of_registration, 'replace_digital_credential')
@patch.object(change_of_registration, 'revoke_digital_credential')
def test_processor_revokes_credential_when_user_not_in_parties(mock_revoke_digital_credential,
                                                              mock_replace_digital_credential,
                                                              mock_is_user_in_officers,
                                                              mock_get_all_digital_credentials_for_business,
                                                              app, session):
    """Assert that the processor revokes credential when user is not in filing parties."""
    business = create_business(identifier='FM0000001')
    filing = create_filing(filing_json={
        'filing': {
            'header': {
                'name': 'changeOfRegistration',
                'filingId': None
            },
            'changeOfRegistration': {
                'parties': []
            }
        }}, business_id=business.id)
    
    user = create_user()
    mock_credential = MagicMock()
    mock_credential.id = 1
    mock_credential.connection.business_user.user = user
    mock_get_all_digital_credentials_for_business.return_value = [mock_credential]

    change_of_registration.process(business, filing)

    mock_get_all_digital_credentials_for_business.assert_called_once_with(business=business)
    filing_data = filing.filing_json.get("filing", {}).get(filing.filing_type, {})
    mock_is_user_in_officers.assert_called_once_with(user, filing_data, 'Partner')
    mock_replace_digital_credential.assert_not_called()
    mock_revoke_digital_credential.assert_called_once_with(
        credential=mock_credential,
        reason=DCRevocationReason.CHANGE_OF_DIRECTORS
    )


@patch.object(change_of_registration, 'get_all_digital_credentials_for_business')
@patch.object(change_of_registration, 'is_user_in_officers', return_value=False)
@patch.object(change_of_registration, 'replace_digital_credential')
@patch.object(change_of_registration, 'revoke_digital_credential')
def test_processor_continues_processing_after_credential_error(mock_revoke_digital_credential,
                                                               mock_replace_digital_credential,
                                                               mock_is_user_in_officers,
                                                               mock_get_all_digital_credentials_for_business,
                                                               app, session):
    """Assert that the processor continues processing other credentials after one fails."""
    business = create_business(identifier='FM0000001')
    filing = create_filing(filing_json={
        'filing': {
            'header': {
                'name': 'changeOfRegistration',
                'filingId': None
            },
            'changeOfRegistration': {
                'parties': []
            }
        }}, business_id=business.id)
    
    user1 = create_user(firstname='John', lastname='Doe')
    user2 = create_user(firstname='Jane', lastname='Smith')
    
    mock_credential1 = MagicMock()
    mock_credential1.id = 1
    mock_credential1.connection.business_user.user = user1
    
    mock_credential2 = MagicMock()
    mock_credential2.id = 2
    mock_credential2.connection.business_user.user = user2
    
    mock_get_all_digital_credentials_for_business.return_value = [mock_credential1, mock_credential2]
    
    # Make the first credential processing fail
    def side_effect(*args, **kwargs):
        if args[0] == mock_credential1:
            raise Exception("Test error")
        return None
    
    mock_revoke_digital_credential.side_effect = side_effect

    change_of_registration.process(business, filing)

    mock_get_all_digital_credentials_for_business.assert_called_once_with(business=business)
    filing_data = filing.filing_json.get("filing", {}).get(filing.filing_type, {})
    assert mock_is_user_in_officers.call_count == 2
    mock_is_user_in_officers.assert_any_call(user1, filing_data, 'Partner')
    mock_is_user_in_officers.assert_any_call(user2, filing_data, 'Partner')
    
    # Both credentials should be attempted to be revoked, even though first one fails
    assert mock_revoke_digital_credential.call_count == 2
    mock_replace_digital_credential.assert_not_called()
