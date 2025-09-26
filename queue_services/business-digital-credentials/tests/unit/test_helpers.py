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
"""Tests for the helper functions are contained here."""


from unittest.mock import patch

import pytest
from business_model.models import DCBusinessUser, DCCredential, DCDefinition, DCRevocationReason, User

from business_digital_credentials.digital_credential_processors.helpers import (
    _does_officer_match_user,
    does_officer_have_action,
    get_all_digital_credentials_for_business,
    issue_digital_credential,
    replace_digital_credential,
    revoke_digital_credential,
)
from tests.unit import (
    create_business,
    create_dc_business_user,
    create_dc_connection,
    create_dc_credential,
    create_user,
)


BUSINESS_IDENTIFIER = 'FM0000001'


def test_get_all_issued_credentials_for_business_returns_empty_list_no_business_users(app, session):
    """Assert get_all_digital_credentials_for_business returns an empty list when no business users."""
    business = create_business(identifier=BUSINESS_IDENTIFIER)

    credentials = get_all_digital_credentials_for_business(business=business)

    assert credentials == []


def test_get_all_issued_credentials_for_business_returns_empty_list_no_active_connection(app, session):
    """Assert get_all_digital_credentials_for_business returns an empty list when no active connections."""
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    user = create_user()
    business_user = create_dc_business_user(business=business, user=user)
    create_dc_connection(business_user=business_user, is_active=False)

    credentials = get_all_digital_credentials_for_business(business=business)

    assert credentials == []


def test_get_all_issued_credentials_for_business_returns_credentials(app, session):
    """Assert get_all_digital_credentials_for_business returns a list of credentials."""
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    user = create_user()
    user2 = create_user()
    business_user1 = create_dc_business_user(business=business, user=user)
    business_user2 = create_dc_business_user(business=business, user=user2)
    create_dc_credential(business_user=business_user1,
                         is_issued=True, is_revoked=False)
    create_dc_credential(business_user=business_user2,
                         is_issued=True, is_revoked=False)

    credentials = get_all_digital_credentials_for_business(business=business)

    assert len(credentials) == 2


@patch('business_registry_digital_credentials.DigitalCredentialsService.revoke_credential')
def test_issued_credential_not_issued_not_revoked(mock_revoke_credential, app, session):
    """Assert that the issued credential is not revoked if is not yet issued."""
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    user = create_user()
    business_user = create_dc_business_user(business=business, user=user)
    credential = create_dc_credential(
        business_user=business_user, is_issued=False)

    with pytest.raises(Exception) as excinfo:
        revoke_digital_credential(
            credential=credential, reason=DCRevocationReason.UPDATED_INFORMATION)
    assert 'Credential is not issued yet or is revoked already.' in str(
        excinfo)
    mock_revoke_credential.assert_not_called()


@patch('business_registry_digital_credentials.DigitalCredentialsService.revoke_credential')
def test_issued_credential_already_revoked_not_revoked(mock_revoke_credential, app, session):
    """Assert that the issued credential is not revoked if already revoked."""
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    user = create_user()
    business_user = create_dc_business_user(business=business, user=user)
    credential = create_dc_credential(
        business_user=business_user, is_issued=True, is_revoked=True)

    with pytest.raises(Exception) as excinfo:
        revoke_digital_credential(
            credential=credential, reason=DCRevocationReason.UPDATED_INFORMATION)
    assert 'Credential is not issued yet or is revoked already.' in str(
        excinfo)
    mock_revoke_credential.assert_not_called()


@patch('business_registry_digital_credentials.DigitalCredentialsService.revoke_credential')
def test_issued_credential_no_credential_connection_not_revoked(mock_revoke_credential, app, session):
    """Assert that the issued credential is not revoked if no credential connection found."""
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    user = create_user()
    business_user = create_dc_business_user(business=business, user=user)
    credential = create_dc_credential(
        business_user=business_user, is_issued=True, is_revoked=False)

    credential.connection = None
    with pytest.raises(Exception) as excinfo:
        revoke_digital_credential(
            credential=credential, reason=DCRevocationReason.UPDATED_INFORMATION)
    assert f'Active connection not found for credential with ID: {credential.credential_id}.' in str(
        excinfo)
    mock_revoke_credential.assert_not_called()


@patch('business_registry_digital_credentials.DigitalCredentialsService.revoke_credential')
def test_issued_credential_no_active_credential_connection_not_revoked(mock_revoke_credential, app, session):
    """Assert that the issued credential is not revoked if credential connection is not active."""
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    user = create_user()
    business_user = create_dc_business_user(business=business, user=user)
    credential = create_dc_credential(
        business_user=business_user, is_issued=True, is_revoked=False)

    credential.connection.is_active = False
    with pytest.raises(Exception) as excinfo:
        revoke_digital_credential(
            credential=credential, reason=DCRevocationReason.UPDATED_INFORMATION)
    assert f'Active connection not found for credential with ID: {credential.credential_id}.' in str(
        excinfo)
    mock_revoke_credential.assert_not_called()


@patch('business_registry_digital_credentials.DigitalCredentialsService.revoke_credential', return_value=None)
def test_revoke_digital_credential_helper_throws_exception(mock_revoke_credential, app, session):
    """Assert that the revoke issued credential helper throws an exception if the service fails."""
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    user = create_user()
    business_user = create_dc_business_user(business=business, user=user)
    credential = create_dc_credential(
        business_user=business_user, is_issued=True, is_revoked=False)

    with pytest.raises(Exception) as excinfo:
        revoke_digital_credential(
            credential=credential, reason=DCRevocationReason.UPDATED_INFORMATION)

    assert 'Failed to revoke credential.' in str(excinfo)
    assert credential.is_revoked is False


@patch('business_registry_digital_credentials.DigitalCredentialsService.revoke_credential', return_value={})
def test_issued_credential_revoked(mock_revoke_credential, app, session):
    """Assert that the issued credential is revoked."""
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    user = create_user()
    business_user = create_dc_business_user(business=business, user=user)
    credential = create_dc_credential(
        business_user=business_user, is_issued=True, is_revoked=False)

    revoke_digital_credential(
        credential=credential, reason=DCRevocationReason.UPDATED_INFORMATION)

    assert credential.is_revoked is True


@patch('business_digital_credentials.digital_credential_processors.helpers.issue_digital_credential', return_value=None)
@patch('business_registry_digital_credentials.DigitalCredentialsService.fetch_credential_exchange_record', return_value=None)
@patch('business_model.models.User.find_by_id', return_value=User(id=1))
@patch('business_model.models.DCBusinessUser.find_by_id', return_value=DCBusinessUser(id=1, user_id=1))
@patch('business_digital_credentials.digital_credential_processors.helpers.revoke_digital_credential')
def test_issued_credential_not_revoked_is_revoked_first(mock_revoke_digital_credential,
                                                        mock_find_business_user_by_id,
                                                        mock_find_user_by_id,
                                                        mock_fetch_credential_exchange_record,
                                                        mock_issue_digital_credential,
                                                        app, session):
    """Assert that the issued credential is revoked first if its not revoked before replacing."""
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    user = create_user()
    business_user = create_dc_business_user(business=business, user=user)
    credential = create_dc_credential(
        business_user=business_user, is_issued=True, is_revoked=False)
    reason = DCRevocationReason.UPDATED_INFORMATION

    replace_digital_credential(credential=credential,
                               credential_type=DCDefinition.CredentialType.business.name,
                               reason=reason)

    mock_revoke_digital_credential.assert_called_once_with(credential, reason)


@patch('business_digital_credentials.digital_credential_processors.helpers.issue_digital_credential', return_value=None)
@patch('business_registry_digital_credentials.DigitalCredentialsService.fetch_credential_exchange_record', return_value=None)
@patch('business_model.models.User.find_by_id', return_value=User(id=1))
@patch('business_model.models.DCBusinessUser.find_by_id', return_value=DCBusinessUser(id=1, user_id=1))
@patch('business_digital_credentials.digital_credential_processors.helpers.revoke_digital_credential')
def test_issued_credential_revoked_is_not_revoked_first(mock_revoke_credential,
                                                        mock_find_buisness_user_by_id,
                                                        mock_find_user_by_id,
                                                        mock_fetch_credential_exchange_record,
                                                        mock_issue_digital_credential,
                                                        app, session):
    """Assert that the issued credential is not revoked first if its already revoked before replacing."""
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    user = create_user()
    business_user = create_dc_business_user(business=business, user=user)
    credential = create_dc_credential(
        business_user=business_user, is_issued=True, is_revoked=True)
    reason = DCRevocationReason.UPDATED_INFORMATION

    replace_digital_credential(credential=credential,
                               credential_type=DCDefinition.CredentialType.business.name,
                               reason=reason)

    mock_revoke_credential.assert_not_called()


@patch('business_digital_credentials.digital_credential_processors.helpers.issue_digital_credential')
@patch('business_registry_digital_credentials.DigitalCredentialsService.fetch_credential_exchange_record',
       return_value='test_credential_exchange_id')
@patch('business_registry_digital_credentials.DigitalCredentialsService.remove_credential_exchange_record', return_value=None)
def test_replace_digital_credential_throws_cred_ex_id_exception(mock_remove_credential_exchange_record,
                                                                mock_fetch_credential_exchange_record,
                                                                mock_issue_digital_credential,
                                                                app, session):
    """
    Assert the digital credential credential service throws an exception.

    An exception should be thrown if the service fails to remove a credential exchange id.
    """
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    user = create_user()
    business_user = create_dc_business_user(business=business, user=user)
    credential = create_dc_credential(
        business_user=business_user, is_issued=True, is_revoked=True)
    reason = DCRevocationReason.UPDATED_INFORMATION

    with pytest.raises(Exception) as excinfo:
        replace_digital_credential(credential=credential,
                                   credential_type=DCDefinition.CredentialType.business.name,
                                   reason=reason)

    assert 'Failed to remove credential exchange record.' in str(excinfo)
    mock_issue_digital_credential.assert_not_called()


@patch('business_digital_credentials.digital_credential_processors.helpers.issue_digital_credential', return_value=None)
@patch('business_registry_digital_credentials.DigitalCredentialsService.fetch_credential_exchange_record', return_value=None)
def test_issued_credential_replaced(mock_fetch_credential_exchange_record,
                                    mock_issue_digital_credential,
                                    app, session):
    """Assert that the issued credential is deleted and replaced with a new one."""
    user = create_user()
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    business_user = create_dc_business_user(business=business, user=user)
    credential = create_dc_credential(
        business_user=business_user, is_issued=True, is_revoked=True)
    credential_type = DCDefinition.CredentialType.business.name
    reason = DCRevocationReason.UPDATED_INFORMATION

    replace_digital_credential(credential=credential,
                               credential_type=credential_type,
                               reason=reason)

    assert DCCredential.find_by_id(credential.id) is None
    mock_issue_digital_credential.assert_called_once_with(
        business_user, credential_type)


@patch('business_model.models.DCDefinition.find_by', return_value=None)
def test_issue_digital_credential_throws_definition_not_found_error(mock_find_definition_by, app, session):
    """Assert that the issue_digital_credential helper throws an exception if the definition is not found."""
    user = create_user()
    business = create_business(identifier=BUSINESS_IDENTIFIER)
    business_user = create_dc_business_user(business=business, user=user)
    # Don't create a definition - the test expects find_by to return None

    with pytest.raises(Exception) as excinfo:
        issue_digital_credential(
            business_user=business_user, credential_type=DCDefinition.CredentialType.business.name)

    assert 'Definition not found for credential type: business.' in str(
        excinfo)


@patch('business_model.models.DCConnection.find_active_by_business_user_id', return_value=None)
@patch('business_digital_credentials.digital_credential_processors.helpers.digital_credentials')
def test_issue_digital_credential_throws_active_connection_not_found_error(mock_digital_credentials,
                                                                           mock_find_active_by,
                                                                           app, session):
    """Assert that the issue_digital_credential helper throws an exception if the definition is not found."""
    mock_digital_credentials.business_schema_id = 'test_schema_id'
    mock_digital_credentials.business_cred_def_id = 'test_credential_definition_id'
    
    # Mock the definition lookup to return a valid definition
    mock_definition = DCDefinition(
        id=1,
        credential_type=DCDefinition.CredentialType.business,
        schema_name="test_business_schema",
        schema_version="1.0.0",
        schema_id="test_schema_id",
        credential_definition_id="test_credential_definition_id",
    )
    
    with patch('business_model.models.DCDefinition.find_by', return_value=mock_definition):
        user = create_user()
        business = create_business(identifier='FM0000002')
        business_user = create_dc_business_user(business=business, user=user)

        with pytest.raises(Exception) as excinfo:
            issue_digital_credential(
                business_user=business_user, credential_type=DCDefinition.CredentialType.business.name)

        assert f'Active connection not found for business user with ID: {business_user.id}.' in str(
            excinfo)


@patch('business_digital_credentials.digital_credential_processors.helpers.digital_credentials')
@patch('business_digital_credentials.digital_credential_processors.helpers.get_digital_credential_data', return_value=[{
    'name': 'credential_id',
    'value': '00000001'
}])
def test_issue_digital_credential_throws_exception_on_failure(mock_digital_credentials_helpers,
                                                              mock_digital_credentials,
                                                              app, session):
    """Assert that the issue_digital_credential helper throws an exception if the service fails."""
    mock_digital_credentials.issue_credential.return_value = None
    mock_digital_credentials.business_schema_id = 'test_schema_id'
    mock_digital_credentials.business_cred_def_id = 'test_credential_definition_id'
    
    # Mock the definition lookup to return a valid definition
    mock_definition = DCDefinition(
        id=1,
        credential_type=DCDefinition.CredentialType.business,
        schema_name="test_business_schema",
        schema_version="1.0.0",
        schema_id="test_schema_id",
        credential_definition_id="test_credential_definition_id",
    )
    
    with patch('business_model.models.DCDefinition.find_by', return_value=mock_definition):
        user = create_user()
        business = create_business(identifier='FM0000003')
        business_user = create_dc_business_user(business=business, user=user)
        create_dc_connection(business_user=business_user, is_active=True)

        with pytest.raises(Exception) as excinfo:
            issue_digital_credential(
                business_user=business_user, credential_type=DCDefinition.CredentialType.business.name)

        assert 'Failed to issue credential.' in str(excinfo)


@patch('business_digital_credentials.digital_credential_processors.helpers.digital_credentials')
@patch('business_digital_credentials.digital_credential_processors.helpers.get_digital_credential_data', return_value=[{
    'name': 'credential_id',
    'value': '00000001'
}])
def test_issue_digital_credential(mock_digital_credentials_helpers,
                                  mock_digital_credentials,
                                  app, session):
    """Assert that the issue_digital_credential helper issues a credential."""
    mock_digital_credentials.issue_credential.return_value = {
        'cred_ex_id': 'test_credential_exchange_id'}
    mock_digital_credentials.business_schema_id = 'test_schema_id'
    mock_digital_credentials.business_cred_def_id = 'test_credential_definition_id'
    
    # Mock the definition lookup to return a valid definition
    mock_definition = DCDefinition(
        id=1,
        credential_type=DCDefinition.CredentialType.business,
        schema_name="test_business_schema",
        schema_version="1.0.0",
        schema_id="test_schema_id",
        credential_definition_id="test_credential_definition_id",
    )
    
    with patch('business_model.models.DCDefinition.find_by', return_value=mock_definition):
        user = create_user()
        business = create_business(identifier='FM0000004')
        business_user = create_dc_business_user(business=business, user=user)
        connection = create_dc_connection(business_user=business_user, is_active=True)

        issued_credential = issue_digital_credential(
            business_user=business_user, credential_type=DCDefinition.CredentialType.business.name)

        assert issued_credential.credential_exchange_id == 'test_credential_exchange_id'
        assert issued_credential.credential_id == '00000001'
        assert issued_credential.definition_id == mock_definition.id
        assert issued_credential.connection_id == connection.id


# Tests for is_user_in_officers function
@pytest.mark.parametrize("user_first,user_last,officer_first,officer_last,role_type,search_role,expected", [
    # Positive cases
    ("John", "Doe", "John", "Doe", "Partner", "Partner", True),
    ("john", "doe", "JOHN", "DOE", "Partner", "Partner", True),  # Case insensitive
    
    # Negative cases - name mismatch
    ("John", "Doe", "Jane", "Smith", "Partner", "Partner", False),
    
    # Negative cases - role mismatch
    ("John", "Doe", "John", "Doe", "Director", "Partner", False),
])
def test_is_user_in_officers_basic_matching(user_first, user_last, officer_first, officer_last, role_type, search_role, expected, app, session):
    """Test basic name and role matching scenarios."""
    from business_digital_credentials.digital_credential_processors.helpers import is_user_in_officers
    
    user = create_user(firstname=user_first, lastname=user_last)
    filing_data = {
        'parties': [
            {
                'officer': {
                    'firstName': officer_first,
                    'lastName': officer_last
                },
                'roles': [
                    {'roleType': role_type}
                ]
            }
        ]
    }
    
    result = is_user_in_officers(user, filing_data, search_role)
    assert result is expected


@pytest.mark.parametrize("filing_data,expected", [
    ({'parties': []}, False),  # Empty parties
    ({}, False),  # Missing parties key
    ({'parties': [{'roles': [{'roleType': 'Partner'}]}]}, False),  # Missing officer data
    ({'parties': [{'officer': {'firstName': 'John', 'lastName': 'Doe'}}]}, False),  # Missing roles
])
def test_is_user_in_officers_edge_cases(filing_data, expected, app, session):
    """Test edge cases with malformed or missing data."""
    from business_digital_credentials.digital_credential_processors.helpers import is_user_in_officers
    
    user = create_user(firstname='John', lastname='Doe')
    result = is_user_in_officers(user, filing_data, 'Partner')
    assert result is expected


def test_is_user_in_officers_stops_at_first_match(app, session):
    """Assert that is_user_in_officers stops at first match and returns True."""
    from business_digital_credentials.digital_credential_processors.helpers import is_user_in_officers
    
    user = create_user(firstname='John', lastname='Doe')
    filing_data = {
        'parties': [
            {
                'officer': {
                    'firstName': 'John',
                    'lastName': 'Doe'
                },
                'roles': [
                    {'roleType': 'Partner'}
                ]
            },
            {
                'officer': {
                    'firstName': 'John',
                    'lastName': 'Doe'
                },
                'roles': [
                    {'roleType': 'Director'}
                ]
            }
        ]
    }
    
    result = is_user_in_officers(user, filing_data, 'Partner')
    assert result is True


# Tests for _does_officer_match_user function
@pytest.mark.parametrize("user_first,user_last,officer_first,officer_last,expected", [
    # Positive cases
    ("John", "Doe", "John", "Doe", True),
    ("John", "Doe", "JOHN", "DOE", True),  # Case insensitive
    
    # Negative cases
    ("John", "Doe", "Jane", "Doe", False),  # Different first name
    ("John", "Doe", "John", "Smith", False),  # Different last name
])
def test_does_officer_match_user_name_matching(user_first, user_last, officer_first, officer_last, expected, app, session):
    """Test name matching scenarios."""
    user = create_user(firstname=user_first, lastname=user_last)
    officer = {
        'firstName': officer_first,
        'lastName': officer_last
    }
    
    result = _does_officer_match_user(officer, user)
    assert result is expected


@pytest.mark.parametrize("officer,expected", [
    ({'lastName': 'Doe'}, False),  # Missing firstName
    ({'firstName': 'John'}, False),  # Missing lastName
    ({}, False),  # Empty dict
    ({'firstName': '', 'lastName': ''}, False),  # Empty names
])
def test_does_officer_match_user_missing_or_empty_data(officer, expected, app, session):
    """Test handling of missing or empty officer data."""
    user = create_user(firstname='John', lastname='Doe')
    result = _does_officer_match_user(officer, user)
    assert result is expected


# Tests for does_officer_have_action function
@pytest.mark.parametrize("officer_first,officer_last,actions,filing_officer_type,search_officer_type,search_action,expected", [
    # Positive cases
    ("John", "Doe", ["ceased", "appointed"], "directors", "directors", "ceased", True),
    ("John", "Doe", ["CEASED"], "directors", "directors", "ceased", True),  # Case insensitive action
    ("JOHN", "DOE", ["ceased"], "directors", "directors", "ceased", True),  # Case insensitive names
    ("John", "Doe", ["ceased"], "partners", "partners", "ceased", True),  # Different officer type
    
    # Negative cases
    ("John", "Doe", ["appointed"], "directors", "directors", "ceased", False),  # User doesn't have action
    ("Jane", "Smith", ["ceased"], "directors", "directors", "ceased", False),  # User not found
    ("John", "Doe", [], "directors", "directors", "ceased", False),  # Empty actions
    ("John", "Doe", ["ceased"], "directors", "partners", "ceased", False),  # Wrong officer type (searching partners in directors filing)
])
def test_does_officer_have_action_basic_scenarios(officer_first, officer_last, actions, filing_officer_type, search_officer_type, search_action, expected, app, session):
    """Test basic action checking scenarios."""
    user = create_user(firstname='John', lastname='Doe')
    filing_data = {
        filing_officer_type: [
            {
                'officer': {
                    'firstName': officer_first,
                    'lastName': officer_last
                },
                'actions': actions
            }
        ]
    }
    
    result = does_officer_have_action(user, filing_data, search_officer_type, search_action)
    assert result is expected


def test_does_officer_have_action_missing_actions_field(app, session):
    """Assert does_officer_have_action returns False when actions field is missing."""
    user = create_user(firstname='John', lastname='Doe')
    filing_data = {
        'directors': [
            {
                'officer': {
                    'firstName': 'John',
                    'lastName': 'Doe'
                }
                # actions field is missing
            }
        ]
    }
    
    result = does_officer_have_action(user, filing_data, 'directors', 'ceased')
    assert result is False


def test_does_officer_have_action_multiple_officers_finds_correct_match(app, session):
    """Assert does_officer_have_action finds the correct user among multiple officers."""
    user = create_user(firstname='John', lastname='Doe')
    filing_data = {
        'directors': [
            {
                'officer': {
                    'firstName': 'Jane',
                    'lastName': 'Smith'
                },
                'actions': ['appointed']
            },
            {
                'officer': {
                    'firstName': 'John',
                    'lastName': 'Doe'
                },
                'actions': ['ceased']
            },
            {
                'officer': {
                    'firstName': 'Bob',
                    'lastName': 'Johnson'
                },
                'actions': ['appointed']
            }
        ]
    }
    
    result = does_officer_have_action(user, filing_data, 'directors', 'ceased')
    assert result is True


def test_does_officer_have_action_stops_at_first_user_match(app, session):
    """Assert does_officer_have_action stops processing after finding the user (doesn't check duplicates)."""
    user = create_user(firstname='John', lastname='Doe')
    filing_data = {
        'directors': [
            {
                'officer': {
                    'firstName': 'John',
                    'lastName': 'Doe'
                },
                'actions': ['appointed']  # First occurrence doesn't have 'ceased'
            },
            {
                'officer': {
                    'firstName': 'John',
                    'lastName': 'Doe'
                },
                'actions': ['ceased']  # Second occurrence has 'ceased' but should be ignored
            }
        ]
    }
    
    result = does_officer_have_action(user, filing_data, 'directors', 'ceased')
    assert result is False  # Should return False because it only checks the first match
