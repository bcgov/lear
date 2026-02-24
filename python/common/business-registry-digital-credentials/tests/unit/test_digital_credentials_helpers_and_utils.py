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

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from business_model.models import Business, CorpType, DCBusinessUser, DCDefinition, Party, PartyRole, User
from business_registry_digital_credentials.digital_credentials_helpers import (
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
from business_registry_digital_credentials.digital_credentials_rules import DigitalCredentialsRulesService
from business_registry_digital_credentials.digital_credentials_utils import (
    FormattedUser,
    determine_allowed_business_types,
)


@pytest.mark.parametrize(
    "test_user, expected",
    [
        (Party(**{"first_name": "First", "last_name": "Last"}), {"first_name": "first", "last_name": "last"}),
        (
            Party(**{"first_name": "First", "middle_initial": "M", "last_name": "Last"}),
            {"first_name": "first m", "last_name": "last"},
        ),
        (User(**{"firstname": "First", "lastname": "Last"}), {"first_name": "first", "last_name": "last"}),
        (
            User(**{"firstname": "First", "middlename": "M", "lastname": "Last"}),
            {"first_name": "first m", "last_name": "last"},
        ),
        (User(), {"first_name": "", "last_name": ""}),
        (Party(), {"first_name": "", "last_name": ""}),
    ],
)
def test_formatted_user(test_user, expected):
    """Assert that the user is formatted correctly."""

    assert FormattedUser(test_user).__dict__ == expected


@pytest.mark.parametrize(
    "flag_value, valid_registration_types, valid_incorporation_types, expected",
    [
        ({"types": ["SP", "BEN", "GP"]}, ["SP", "GP"], ["BEN"], ["SP", "BEN", "GP"]),
        ({"types": ["SP", "BEN", "GP", "CBEN"]}, ["SP", "GP"], ["BEN"], ["SP", "BEN", "GP"]),
        ({"types": ["SP"]}, ["SP", "GP"], ["BEN"], ["SP", "BEN", "GP"]),
        ({"types": []}, ["SP", "GP"], ["BEN"], ["SP", "BEN", "GP"]),
        ({"types": ["SP", "GP"]}, [], ["BEN"], ["SP", "BEN", "GP"]),
        ({"types": ["SP", "BEN"]}, ["SP", "GP"], [], ["SP", "BEN", "GP"]),
    ],
)
def test_determine_allowed_business_types(
    app, flag_value, valid_registration_types, valid_incorporation_types, expected
):
    """Test filtering of allowed business types based on flag values."""

    # The app fixture provides Flask context, so current_app.logger works
    result = determine_allowed_business_types(valid_registration_types, valid_incorporation_types)
    assert sorted(result) == sorted(expected)


@pytest.mark.parametrize(
    "flag_value, valid_registration_types, valid_incorporation_types, expected",
    [
        (["SP", "BEN", "GP"], ["SP", "GP"], ["BEN"], ["SP", "BEN", "GP"]),
        ({}, ["SP"], ["BEN"], ["SP", "BEN", "GP"]),
        ({"types": "SP"}, ["SP"], ["BEN"], ["SP", "BEN", "GP"]),
        ({"types": 123}, ["SP"], ["BEN"], ["SP", "BEN", "GP"]),
        ({"type": ["SP", "BEN", "GP"]}, ["SP"], ["BEN"], ["SP", "BEN", "GP"]),
        ("not-a-object", ["SP"], ["BEN"], ["SP", "BEN", "GP"]),
        (123, ["SP"], ["BEN"], ["SP", "BEN", "GP"]),
    ],
)
def test_determine_allowed_business_types_invalid_flags(
    app, flag_value, valid_registration_types, valid_incorporation_types, expected
):
    """Test filtering of allowed business types based on flag values."""

    # The app fixture provides Flask context, so current_app.logger works
    result = determine_allowed_business_types(valid_registration_types, valid_incorporation_types)
    assert sorted(result) == sorted(expected)


def test_determine_allowed_business_types_missing_flag(app):
    """Test filtering of allowed business types based on flag value not set."""

    # The app fixture provides Flask context, so current_app.logger works
    result = determine_allowed_business_types(["SP", "GP"], ["BEN"])
    assert result == ["SP", "BEN", "GP"]


# Helper function tests


def _make_party_role(role_value):
    """Create a mock PartyRole with the given role."""
    pr = MagicMock(spec=PartyRole)
    pr.role = role_value
    pr.party = MagicMock()
    return pr


class TestGetFamilyName:
    """Tests for get_family_name."""

    def test_returns_uppercase(self):
        """Returns lastname in uppercase."""
        user = MagicMock()
        user.lastname = "Smith"
        assert get_family_name(user) == "SMITH"

    def test_strips_whitespace(self):
        """Strips whitespace from lastname."""
        user = MagicMock()
        user.lastname = "  Smith  "
        assert get_family_name(user) == "SMITH"

    def test_none_lastname(self):
        """Returns empty string when lastname is None."""
        user = MagicMock()
        user.lastname = None
        assert get_family_name(user) == ""


class TestGetGivenNames:
    """Tests for get_given_names."""

    def test_first_and_middle(self):
        """Returns firstname and middlename in uppercase."""
        user = MagicMock()
        user.firstname = "John"
        user.middlename = "Michael"
        assert get_given_names(user) == "JOHN MICHAEL"

    def test_first_only(self):
        """Returns just firstname when no middlename."""
        user = MagicMock()
        user.firstname = "John"
        user.middlename = None
        assert get_given_names(user) == "JOHN"

    def test_none_values(self):
        """Returns empty string when both are None."""
        user = MagicMock()
        user.firstname = None
        user.middlename = None
        assert get_given_names(user) == ""


class TestGetRegisteredOnDateint:
    """Tests for get_registered_on_dateint."""

    def test_formats_date(self):
        """Returns date in YYYYMMDD format."""
        business = MagicMock()
        business.founding_date = datetime(2025, 1, 15)
        assert get_registered_on_dateint(business) == "20250115"

    def test_no_founding_date(self):
        """Returns empty string when no founding date."""
        business = MagicMock()
        business.founding_date = None
        assert get_registered_on_dateint(business) == ""


class TestGetCompanyStatus:
    """Tests for get_company_status."""

    def test_returns_state_name(self):
        """Returns the Business.State enum name."""
        business = MagicMock()
        business.state = Business.State.ACTIVE.value
        result = get_company_status(business)
        assert result == "ACTIVE"


class TestGetBusinessType:
    """Tests for get_business_type."""

    @patch("business_registry_digital_credentials.digital_credentials_helpers.CorpType.find_by_id")
    def test_returns_full_desc(self, mock_find):
        """Returns corp type full description."""
        mock_find.return_value = MagicMock(full_desc="BC Benefit Company")
        business = MagicMock()
        business.legal_type = "BEN"
        assert get_business_type(business) == "BC Benefit Company"

    @patch("business_registry_digital_credentials.digital_credentials_helpers.CorpType.find_by_id")
    def test_returns_legal_type_when_no_corp_type(self, mock_find):
        """Returns legal_type when CorpType not found."""
        mock_find.return_value = None
        business = MagicMock()
        business.legal_type = "BEN"
        assert get_business_type(business) == "BEN"


class TestGetOrCreateBusinessUser:
    """Tests for get_or_create_business_user."""

    @patch("business_registry_digital_credentials.digital_credentials_helpers.DCBusinessUser")
    def test_returns_existing(self, mock_dc_cls):
        """Returns existing business user."""
        existing = MagicMock(spec=DCBusinessUser)
        mock_dc_cls.find_by.return_value = existing
        user = MagicMock(id=1)
        business = MagicMock(id=2)
        result = get_or_create_business_user(user, business)
        assert result is existing

    @patch("business_registry_digital_credentials.digital_credentials_helpers.DCBusinessUser")
    def test_creates_new(self, mock_dc_cls):
        """Creates and saves new business user when not found."""
        mock_dc_cls.find_by.return_value = None
        new_bu = MagicMock()
        mock_dc_cls.return_value = new_bu
        user = MagicMock(id=1)
        business = MagicMock(id=2)
        result = get_or_create_business_user(user, business)
        assert result is new_bu
        new_bu.save.assert_called_once()


class TestExtractInvitationMessageId:
    """Tests for extract_invitation_message_id."""

    def test_with_invitation(self):
        """Extracts id from invitation object."""
        msg = {"invitation": {"@id": "msg-123"}}
        assert extract_invitation_message_id(msg) == "msg-123"

    def test_without_invitation(self):
        """Falls back to invitation_msg_id."""
        msg = {"invitation_msg_id": "msg-456"}
        assert extract_invitation_message_id(msg) == "msg-456"

    def test_with_none_invitation(self):
        """Falls back to invitation_msg_id when invitation is None."""
        msg = {"invitation": None, "invitation_msg_id": "msg-789"}
        assert extract_invitation_message_id(msg) == "msg-789"


class TestGetRoles:
    """Tests for get_roles."""

    def test_no_preconditions_returns_all_roles(self):
        """When no preconditions, returns all user roles formatted."""
        rules = MagicMock(spec=DigitalCredentialsRulesService)
        rules.get_preconditions.return_value = []
        rules.user_business_party_roles.return_value = [_make_party_role("director")]
        rules.user_filing_party_roles.return_value = []

        user = MagicMock()
        business = MagicMock()
        result = get_roles(user, business, rules, None)
        assert result == ["Director"]

    def test_preconditions_no_self_attested_returns_empty(self):
        """When preconditions exist but no self-attested roles, returns empty."""
        rules = MagicMock(spec=DigitalCredentialsRulesService)
        rules.get_preconditions.return_value = ["director"]

        user = MagicMock()
        business = MagicMock()
        result = get_roles(user, business, rules, None)
        assert result == []

    def test_preconditions_with_self_attested_filters(self):
        """When preconditions and self-attested roles, filters to intersection."""
        rules = MagicMock(spec=DigitalCredentialsRulesService)
        rules.get_preconditions.return_value = ["director", "proprietor"]
        rules.user_business_party_roles.return_value = [
            _make_party_role("director"),
            _make_party_role("proprietor"),
        ]
        rules.user_filing_party_roles.return_value = []

        user = MagicMock()
        business = MagicMock()
        result = get_roles(user, business, rules, ["director"])
        assert result == ["Director"]

    def test_role_formatting_replaces_underscore(self):
        """Roles with underscores are formatted to title case with spaces."""
        rules = MagicMock(spec=DigitalCredentialsRulesService)
        rules.get_preconditions.return_value = []
        rules.user_business_party_roles.return_value = [_make_party_role("completing_party")]
        rules.user_filing_party_roles.return_value = []

        user = MagicMock()
        business = MagicMock()
        result = get_roles(user, business, rules, None)
        assert result == ["Completing Party"]


class TestGetDigitalCredentialData:
    """Tests for get_digital_credential_data."""

    def test_non_business_type_returns_none(self):
        """Returns None for non-business credential types."""
        business_user = MagicMock()
        result = get_digital_credential_data(business_user, "not_business")
        assert result is None

    @patch("business_registry_digital_credentials.digital_credentials_helpers.get_roles", return_value=["Director"])
    @patch("business_registry_digital_credentials.digital_credentials_helpers.get_given_names", return_value="JOHN")
    @patch("business_registry_digital_credentials.digital_credentials_helpers.get_family_name", return_value="DOE")
    @patch("business_registry_digital_credentials.digital_credentials_helpers.get_company_status", return_value="ACTIVE")
    @patch(
        "business_registry_digital_credentials.digital_credentials_helpers.get_registered_on_dateint",
        return_value="20250115",
    )
    @patch(
        "business_registry_digital_credentials.digital_credentials_helpers.get_business_type",
        return_value="BC Benefit Company",
    )
    def test_business_type_returns_credential_data(
        self, mock_btype, mock_date, mock_status, mock_family, mock_given, mock_roles
    ):
        """Returns credential data list for business credential type."""
        business_user = MagicMock()
        business_user.id = 1
        business_user.business.identifier = "BC1234567"
        business_user.business.legal_name = "Test Business"
        business_user.business.tax_id = "123456789"

        result = get_digital_credential_data(business_user, DCDefinition.CredentialType.business)

        assert result is not None
        data_dict = {item["name"]: item["value"] for item in result}
        assert data_dict["credential_id"] == "00000001"
        assert data_dict["identifier"] == "BC1234567"
        assert data_dict["business_name"] == "Test Business"
        assert data_dict["business_type"] == "BC Benefit Company"
        assert data_dict["cra_business_number"] == "123456789"
        assert data_dict["registered_on_dateint"] == "20250115"
        assert data_dict["company_status"] == "ACTIVE"
        assert data_dict["family_name"] == "DOE"
        assert data_dict["given_names"] == "JOHN"
        assert data_dict["role"] == "Director"
