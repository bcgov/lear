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
"""Tests for digital credentials helpers and utility functions.

Test suite to ensure that helpers and utility functions for digital credentials are working as expected
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from legal_api.models import Business, CorpType, DCBusinessUser, DCDefinition, Party, PartyRole, User
from legal_api.services.digital_credentials_helpers import (
    extract_invitation_message_id,
    get_business_type,
    get_company_status,
    get_digital_credential_data,
    get_family_name,
    get_given_names,
    get_or_create_business_user,
    get_registered_on_dateint,
    get_roles,
)
from legal_api.services.digital_credentials_utils import FormattedUser, determine_allowed_business_types, is_account_based_access_enabled


@pytest.mark.parametrize(
    'test_user, expected',
    [
        (Party(**{'first_name': 'First', 'last_name': 'Last'}),
         {'first_name': 'first', 'last_name': 'last'}),
        (Party(**{'first_name': 'First', 'middle_initial': 'M',
         'last_name': 'Last'}), {'first_name': 'first m', 'last_name': 'last'}),
        (User(**{'firstname': 'First', 'lastname': 'Last'}),
         {'first_name': 'first', 'last_name': 'last'}),
        (User(**{'firstname': 'First', 'middlename': 'M', 'lastname': 'Last'}),
         {'first_name': 'first m', 'last_name': 'last'}),
        (User(), {'first_name': '', 'last_name': ''}),
        (Party(), {'first_name': '', 'last_name': ''}),
    ]
)
def test_formatted_user(app, session, test_user, expected):
    """Assert that the user is formatted correctly."""

    assert FormattedUser(test_user).__dict__ == expected

@pytest.mark.parametrize(
    'flag_value, valid_registration_types, valid_incorporation_types, expected',
    [
        ({"types" :['SP', 'BEN', 'GP']}, ['SP', 'GP'], ['BEN'], ['SP', 'BEN', 'GP']),
        ({"types" :['SP', 'BEN', 'GP', 'CBEN']}, ['SP', 'GP'], ['BEN'], ['SP', 'BEN', 'GP']),
        ({"types" :['SP']}, ['SP', 'GP'], ['BEN'], ['SP']),
        ({"types" :[]}, ['SP', 'GP'], ['BEN'], []),
        ({"types" :['SP', 'GP']}, [], ['BEN'], []),
        ({"types" :['SP', 'BEN']}, ['SP', 'GP'], [], ['SP'])
    ]
)
def test_determine_allowed_business_types(app, monkeypatch, flag_value, valid_registration_types, valid_incorporation_types, expected):
    """Test filtering of allowed business types based on flag values."""

    # Mock flag values
    monkeypatch.setattr('legal_api.services.flags.is_on', lambda _: True)
    monkeypatch.setattr('legal_api.services.flags.value', lambda _: flag_value)

    with app.app_context():
        result = determine_allowed_business_types(valid_registration_types, valid_incorporation_types)
        assert sorted(result) == sorted(expected)

@pytest.mark.parametrize(
    'flag_value, valid_registration_types, valid_incorporation_types, expected',
    [
        (['SP', 'BEN', 'GP'], ['SP', 'GP'], ['BEN'], []),
        ({}, ['SP'], ['BEN'], []),
        ({"types" : "SP"}, ['SP'], ['BEN'], []),
        ({"types" : 123}, ['SP'], ['BEN'], []),
        ({"type" : ['SP', 'BEN', 'GP']}, ['SP'], ['BEN'], []),
        ('not-a-object', ['SP'], ['BEN'], []),
        (123, ['SP'], ['BEN'], []), 
    ]
)
def test_determine_allowed_business_types_invalid_flags(app, monkeypatch, flag_value, valid_registration_types, valid_incorporation_types, expected):
    """Test filtering of allowed business types based on flag values."""

    # Mock flag values
    monkeypatch.setattr('legal_api.services.flags.is_on', lambda _: True)
    monkeypatch.setattr('legal_api.services.flags.value', lambda _: flag_value)

    with app.app_context():
        result = determine_allowed_business_types(valid_registration_types, valid_incorporation_types)
        assert sorted(result) == sorted(expected)

def test_determine_allowed_business_types_missing_flag(app, monkeypatch):
    """Test filtering of allowed business types based on flag value not set."""

    # Mock flag values
    monkeypatch.setattr('legal_api.services.flags.is_on', lambda _: False)

    with app.app_context():
        result = determine_allowed_business_types(['SP', 'GP'], ['BEN'])
        assert result == []


def test_is_account_based_access_enabled_flag_on(app, monkeypatch):
    """Test is_account_based_access_enabled returns True when flag is on."""
    
    # Mock flag to be on
    monkeypatch.setattr('legal_api.services.flags.is_on', lambda flag: flag == 'dbc-enable-account-based-access')
    
    with app.app_context():
        result = is_account_based_access_enabled()
        assert result is True


def test_is_account_based_access_enabled_flag_off(app, monkeypatch):
    """Test is_account_based_access_enabled returns False when flag is off."""
    
    # Mock flag to be off
    monkeypatch.setattr('legal_api.services.flags.is_on', lambda flag: False)
    
    with app.app_context():
        result = is_account_based_access_enabled()
        assert result is False


def test_is_account_based_access_enabled_different_flag(app, monkeypatch):
    """Test is_account_based_access_enabled handles different flag names correctly."""
    
    # Mock flag service to return True only for a different flag
    monkeypatch.setattr('legal_api.services.flags.is_on', lambda flag: flag == 'some-other-flag')
    
    with app.app_context():
        result = is_account_based_access_enabled()
        assert result is False


@pytest.mark.parametrize(
    'founding_date, expected_dateint',
    [
        (datetime(2023, 1, 15), '20230115'),
        (datetime(2020, 2, 29), '20200229'),
        (datetime(2026, 1, 1, 4, 16, 35, 986357, tzinfo=timezone.utc), '20251231'),
        (datetime(2025, 9, 4, 4, 16, 35, 986357, tzinfo=timezone.utc), '20250903'),
        (datetime(2025, 9, 4, 14, 16, 35, 986357, tzinfo=timezone.utc), '20250904'),
        (None, ''),
    ]
)
def test_get_registered_on_dateint(app, founding_date, expected_dateint):
    """Test get_registered_on_dateint function with various dates."""
    business = Business()
    business.founding_date = founding_date
    
    with app.app_context():
        result = get_registered_on_dateint(business)
        assert result == expected_dateint


def test_get_business_type(app, session):
    """Test get_business_type returns full description."""
    business = Business(legal_type='SP')
    
    with app.app_context():
        result = get_business_type(business)
        assert result == 'BC Sole Proprietorship'


def test_get_business_type_no_corp_type(app, session):
    """Test get_business_type returns legal_type when no CorpType found."""
    business = Business(legal_type='UNKNOWN')
    
    with app.app_context():
        result = get_business_type(business)
        assert result == 'UNKNOWN'


def test_get_company_status(app):
    """Test get_company_status returns state name."""
    business = Business(state=Business.State.ACTIVE)
    
    with app.app_context():
        result = get_company_status(business)
        assert result == 'ACTIVE'


def test_get_family_name(app):
    """Test get_family_name returns uppercase last name."""
    user = User(lastname='Smith')
    
    with app.app_context():
        result = get_family_name(user)
        assert result == 'SMITH'


def test_get_family_name_empty(app):
    """Test get_family_name returns empty string for None."""
    user = User(lastname=None)
    
    with app.app_context():
        result = get_family_name(user)
        assert result == ''


def test_get_given_names(app):
    """Test get_given_names returns uppercase first and middle names."""
    user = User(firstname='John', middlename='Michael')
    
    with app.app_context():
        result = get_given_names(user)
        assert result == 'JOHN MICHAEL'


def test_get_given_names_first_only(app):
    """Test get_given_names returns only first name when no middle."""
    user = User(firstname='John', middlename=None)
    
    with app.app_context():
        result = get_given_names(user)
        assert result == 'JOHN'


def test_get_given_names_empty(app):
    """Test get_given_names returns empty string when no names."""
    user = User(firstname=None, middlename=None)
    
    with app.app_context():
        result = get_given_names(user)
        assert result == ''


@patch('legal_api.models.DCBusinessUser.find_by')
def test_get_or_create_business_user_existing(mock_find, app, session):
    """Test get_or_create_business_user returns existing user."""
    user = User(id=1)
    business = Business(id=1)
    existing_bu = DCBusinessUser(id=1, business_id=1, user_id=1)
    mock_find.return_value = existing_bu
    
    with app.app_context():
        result = get_or_create_business_user(user, business)
        assert result == existing_bu
        mock_find.assert_called_once_with(business_id=1, user_id=1)


@patch('legal_api.models.DCBusinessUser.find_by')
@patch('legal_api.models.DCBusinessUser.save')
def test_get_or_create_business_user_new(mock_save, mock_find, app, session):
    """Test get_or_create_business_user creates new user."""
    user = User(id=1)
    business = Business(id=1)
    mock_find.return_value = None
    
    with app.app_context():
        result = get_or_create_business_user(user, business)
        assert result.business_id == 1
        assert result.user_id == 1
        mock_find.assert_called_once_with(business_id=1, user_id=1)


def test_extract_invitation_message_id_with_invitation(app):
    """Test extract_invitation_message_id from invitation field."""
    json_message = {
        "invitation": {
            "@id": "test-invitation-id-123"
        }
    }
    
    with app.app_context():
        result = extract_invitation_message_id(json_message)
        assert result == "test-invitation-id-123"


def test_extract_invitation_message_id_with_msg_id(app):
    """Test extract_invitation_message_id from invitation_msg_id field."""
    json_message = {
        "invitation_msg_id": "test-msg-id-456"
    }
    
    with app.app_context():
        result = extract_invitation_message_id(json_message)
        assert result == "test-msg-id-456"


def test_extract_invitation_message_id_with_null_invitation(app):
    """Test extract_invitation_message_id with null invitation."""
    json_message = {
        "invitation": None,
        "invitation_msg_id": "test-msg-id-789"
    }
    
    with app.app_context():
        result = extract_invitation_message_id(json_message)
        assert result == "test-msg-id-789"


@patch('legal_api.services.digital_credentials_helpers.DigitalCredentialsRulesService')
def test_get_roles_no_preconditions(mock_rules_class, app):
    """Test get_roles returns roles when no preconditions."""
    user = User(id=1)
    business = Business(id=1)
    
    mock_rules = MagicMock()
    mock_rules.get_preconditions.return_value = []
    mock_rules.user_has_business_party_role.return_value = True
    mock_rules.user_has_filing_party_role.return_value = False
    
    mock_party_role = MagicMock()
    mock_party_role.role = 'proprietor'
    mock_rules.user_business_party_roles.return_value = [mock_party_role]
    
    with app.app_context():
        result = get_roles(user, business, mock_rules, None)
        assert result == ['Proprietor']


@patch('legal_api.services.digital_credentials_helpers.DigitalCredentialsRulesService')
def test_get_roles_with_self_attested(mock_rules_class, app):
    """Test get_roles filters by self-attested roles."""
    user = User(id=1)
    business = Business(id=1)
    
    mock_rules = MagicMock()
    mock_rules.get_preconditions.return_value = ['proprietor', 'director']
    mock_rules.user_has_business_party_role.return_value = True
    mock_rules.user_has_filing_party_role.return_value = False
    
    mock_party_role1 = MagicMock()
    mock_party_role1.role = 'proprietor'
    mock_party_role2 = MagicMock()
    mock_party_role2.role = 'director'
    mock_rules.user_business_party_roles.return_value = [mock_party_role1, mock_party_role2]
    
    with app.app_context():
        result = get_roles(user, business, mock_rules, ['proprietor'])
        assert result == ['Proprietor']


@patch('legal_api.services.digital_credentials_helpers.DigitalCredentialsRulesService')
def test_get_digital_credential_data(mock_rules_class, app, session):
    """Test get_digital_credential_data returns complete credential data."""
    user = User(id=1, firstname='John', lastname='Smith')
    business = Business(id=1, identifier='FM1234567', legal_name='Test Business', legal_type='SP', tax_id='123456789', state=Business.State.ACTIVE)
    business_user = DCBusinessUser(id=1, business_id=1, user_id=1, business=business, user=user)
    
    mock_rules = MagicMock()
    mock_rules_class.return_value = mock_rules
    mock_rules.get_preconditions.return_value = []
    mock_rules.user_has_business_party_role.return_value = False
    mock_rules.user_has_filing_party_role.return_value = False
    
    with app.app_context():
        result = get_digital_credential_data(business_user, DCDefinition.CredentialType.business, None)
        
        assert len(result) == 10
        assert result[0] == {"name": "credential_id", "value": "00000001"}
        assert result[1] == {"name": "identifier", "value": "FM1234567"}
        assert result[2] == {"name": "business_name", "value": "Test Business"}


def test_get_digital_credential_data_non_business_type(app, session):
    """Test get_digital_credential_data returns None for non-business type."""
    user = User(id=1)
    business = Business(id=1)
    business_user = DCBusinessUser(id=1, business_id=1, user_id=1, business=business, user=user)
    
    with app.app_context():
        result = get_digital_credential_data(business_user, 'other_type', None)
        assert result is None
