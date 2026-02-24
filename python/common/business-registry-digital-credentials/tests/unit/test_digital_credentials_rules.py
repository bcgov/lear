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
"""Tests for digital credentials rules service.

Test suite to ensure that role filtering in the rules service works as expected.
"""

from unittest.mock import MagicMock, patch

import pytest
from business_model.models import Business, Filing, Party, PartyRole, User
from business_registry_digital_credentials.digital_credentials_rules import DigitalCredentialsRulesService


@pytest.fixture
def rules_service():
    """Create a DigitalCredentialsRulesService instance."""
    return DigitalCredentialsRulesService()


@pytest.fixture
def mock_user():
    """Create a mock user."""
    return MagicMock(spec=User)


def _make_party_role(role_value):
    """Create a mock PartyRole with the given role."""
    pr = MagicMock(spec=PartyRole)
    pr.role = role_value
    pr.party = MagicMock()
    return pr


class TestUserBusinessPartyRoles:
    """Tests for user_business_party_roles filtering by valid_role_types."""

    @patch.object(DigitalCredentialsRulesService, "user_matches_party", return_value=True)
    def test_returns_valid_roles_only(self, mock_match, rules_service, mock_user):
        """Only proprietor, director, and partner roles should be returned."""
        business = MagicMock(spec=Business)
        business.party_roles.all.return_value = [
            _make_party_role("director"),
            _make_party_role("officer"),
            _make_party_role("proprietor"),
            _make_party_role("secretary"),
            _make_party_role("partner"),
        ]

        result = rules_service.user_business_party_roles(mock_user, business)
        role_values = [r.role for r in result]

        assert "director" in role_values
        assert "proprietor" in role_values
        assert "partner" in role_values
        assert "officer" not in role_values
        assert "secretary" not in role_values
        assert len(result) == 3

    @patch.object(DigitalCredentialsRulesService, "user_matches_party", return_value=True)
    def test_excludes_all_invalid_roles(self, mock_match, rules_service, mock_user):
        """Roles not in valid_role_types should be excluded."""
        business = MagicMock(spec=Business)
        business.party_roles.all.return_value = [
            _make_party_role("officer"),
            _make_party_role("completing_party"),
            _make_party_role("incorporator"),
        ]

        result = rules_service.user_business_party_roles(mock_user, business)
        assert len(result) == 0

    @patch.object(DigitalCredentialsRulesService, "user_matches_party", return_value=True)
    def test_returns_empty_when_no_roles(self, mock_match, rules_service, mock_user):
        """Empty list when user has no roles on business."""
        business = MagicMock(spec=Business)
        business.party_roles.all.return_value = []

        result = rules_service.user_business_party_roles(mock_user, business)
        assert result == []

class TestUserFilingPartyRoles:
    """Tests for user_filing_party_roles filtering by valid_role_types."""

    @patch.object(DigitalCredentialsRulesService, "user_matches_party", return_value=True)
    def test_returns_valid_roles_only(self, mock_match, rules_service, mock_user):
        """Only valid role types should be returned from filing party roles."""
        business = MagicMock(spec=Business)
        business.legal_type = Business.LegalTypes.BCOMP.value

        filing = MagicMock(spec=Filing)
        filing.filing_party_roles.filter.return_value.all.return_value = [
            _make_party_role("director"),
            _make_party_role("incorporator"),
            _make_party_role("partner"),
        ]

        with patch.object(rules_service, "valid_filings", return_value=[filing]):
            result = rules_service.user_filing_party_roles(mock_user, business)

        role_values = [r.role for r in result]
        assert "director" in role_values
        assert "partner" in role_values
        assert "incorporator" not in role_values
        assert len(result) == 2

    @patch.object(DigitalCredentialsRulesService, "user_matches_party", return_value=True)
    def test_excludes_all_invalid_roles(self, mock_match, rules_service, mock_user):
        """All invalid roles should be excluded from filing party roles."""
        business = MagicMock(spec=Business)
        business.legal_type = Business.LegalTypes.BCOMP.value

        filing = MagicMock(spec=Filing)
        filing.filing_party_roles.filter.return_value.all.return_value = [
            _make_party_role("incorporator"),
            _make_party_role("officer"),
        ]

        with patch.object(rules_service, "valid_filings", return_value=[filing]):
            result = rules_service.user_filing_party_roles(mock_user, business)

        assert len(result) == 0

    def test_returns_empty_when_no_filings(self, rules_service, mock_user):
        """Returns empty list when there are no valid filings."""
        business = MagicMock(spec=Business)
        business.legal_type = Business.LegalTypes.BCOMP.value

        with patch.object(rules_service, "valid_filings", return_value=[]):
            result = rules_service.user_filing_party_roles(mock_user, business)

        assert result == []

    def test_returns_empty_for_registration_type(self, rules_service, mock_user):
        """Returns empty list for registration type businesses (SP/GP)."""
        business = MagicMock(spec=Business)
        business.legal_type = Business.LegalTypes.SOLE_PROP.value

        filing = MagicMock(spec=Filing)
        with patch.object(rules_service, "valid_filings", return_value=[filing]):
            result = rules_service.user_filing_party_roles(mock_user, business)

        assert result == []


class TestHasGeneralAccess:
    """Tests for _has_general_access."""

    def test_no_user(self, rules_service):
        """Returns False when no user is provided."""
        assert rules_service._has_general_access(None) is False

    def test_non_bcsc_user(self, rules_service):
        """Returns False when user login source is not BCSC."""
        user = MagicMock(spec=User)
        user.login_source = "BCEID"
        assert rules_service._has_general_access(user) is False

    def test_bcsc_user(self, rules_service):
        """Returns True when user login source is BCSC."""
        user = MagicMock(spec=User)
        user.login_source = "BCSC"
        assert rules_service._has_general_access(user) is True


class TestHasSpecificAccess:
    """Tests for _has_specific_access."""

    def test_no_business(self, rules_service, mock_user):
        """Returns False when no business is provided."""
        assert rules_service._has_specific_access(mock_user, None) is False

    @patch(
        "business_registry_digital_credentials.digital_credentials_rules.determine_allowed_business_types",
        return_value=["SP", "BEN", "GP"],
    )
    def test_non_allowed_business_type(self, mock_types, rules_service, mock_user):
        """Returns False when business type is not allowed."""
        business = MagicMock(spec=Business)
        business.legal_type = "CP"
        assert rules_service._has_specific_access(mock_user, business) is False

    @patch(
        "business_registry_digital_credentials.digital_credentials_rules.determine_allowed_business_types",
        return_value=["SP", "BEN", "GP"],
    )
    @patch.object(DigitalCredentialsRulesService, "user_filing_party_roles", return_value=[MagicMock()])
    def test_allowed_type_with_filing_role(self, mock_role, mock_types, rules_service, mock_user):
        """Returns True when business type is allowed and user has a filing role."""
        business = MagicMock(spec=Business)
        business.legal_type = "BEN"
        assert rules_service._has_specific_access(mock_user, business) is True

    @patch(
        "business_registry_digital_credentials.digital_credentials_rules.determine_allowed_business_types",
        return_value=["SP", "BEN", "GP"],
    )
    @patch.object(DigitalCredentialsRulesService, "user_filing_party_roles", return_value=[])
    @patch.object(DigitalCredentialsRulesService, "user_business_party_roles", return_value=[MagicMock()])
    def test_allowed_type_with_business_role(self, mock_biz_role, mock_filing_role, mock_types, rules_service, mock_user):
        """Returns True when business type is allowed and user has a business role."""
        business = MagicMock(spec=Business)
        business.legal_type = "SP"
        assert rules_service._has_specific_access(mock_user, business) is True


class TestAreDigitalCredentialsAllowed:
    """Tests for are_digital_credentials_allowed."""

    @patch.object(DigitalCredentialsRulesService, "_has_general_access", return_value=True)
    @patch.object(DigitalCredentialsRulesService, "_has_specific_access", return_value=True)
    def test_allowed(self, mock_specific, mock_general, rules_service, mock_user):
        """Returns True when both general and specific access are met."""
        business = MagicMock(spec=Business)
        assert rules_service.are_digital_credentials_allowed(mock_user, business) is True

    @patch.object(DigitalCredentialsRulesService, "_has_general_access", return_value=False)
    def test_no_general_access(self, mock_general, rules_service, mock_user):
        """Returns False when general access is not met."""
        business = MagicMock(spec=Business)
        assert rules_service.are_digital_credentials_allowed(mock_user, business) is False

    @patch.object(DigitalCredentialsRulesService, "_has_general_access", return_value=True)
    @patch.object(DigitalCredentialsRulesService, "_has_specific_access", return_value=False)
    def test_no_specific_access(self, mock_specific, mock_general, rules_service, mock_user):
        """Returns False when specific access is not met."""
        business = MagicMock(spec=Business)
        assert rules_service.are_digital_credentials_allowed(mock_user, business) is False


class TestGetPreconditions:
    """Tests for get_preconditions."""

    @patch.object(DigitalCredentialsRulesService, "user_is_completing_party", return_value=True)
    def test_completing_party_returns_empty(self, mock_cp, rules_service, mock_user):
        """Returns empty list when user is the completing party."""
        business = MagicMock(spec=Business)
        assert rules_service.get_preconditions(mock_user, business) == []

    @patch.object(DigitalCredentialsRulesService, "user_is_completing_party", return_value=False)
    def test_returns_business_roles(self, mock_cp, rules_service, mock_user):
        """Returns business party roles when user has them."""
        business = MagicMock(spec=Business)
        role = _make_party_role("director")
        with patch.object(rules_service, "user_business_party_roles", return_value=[role]), \
             patch.object(rules_service, "user_filing_party_roles", return_value=[]):
            result = rules_service.get_preconditions(mock_user, business)
        assert result == ["director"]

    @patch.object(DigitalCredentialsRulesService, "user_is_completing_party", return_value=False)
    def test_returns_combined_roles(self, mock_cp, rules_service, mock_user):
        """Returns both business and filing party roles."""
        business = MagicMock(spec=Business)
        biz_role = _make_party_role("proprietor")
        filing_role = _make_party_role("director")
        with patch.object(rules_service, "user_business_party_roles", return_value=[biz_role]), \
             patch.object(rules_service, "user_filing_party_roles", return_value=[filing_role]):
            result = rules_service.get_preconditions(mock_user, business)
        assert "proprietor" in result
        assert "director" in result


class TestUserIsCompletingParty:
    """Tests for user_is_completing_party."""

    def test_no_valid_filings(self, rules_service, mock_user):
        """Returns False when there are no valid filings."""
        business = MagicMock(spec=Business)
        with patch.object(rules_service, "valid_filings", return_value=[]):
            assert rules_service.user_is_completing_party(mock_user, business) is False

    @patch.object(DigitalCredentialsRulesService, "user_submitted_filing", return_value=True)
    @patch.object(DigitalCredentialsRulesService, "user_matches_completing_party", return_value=True)
    def test_is_completing_party(self, mock_match, mock_submit, rules_service, mock_user):
        """Returns True when user submitted the filing and matches completing party."""
        business = MagicMock(spec=Business)
        filing = MagicMock(spec=Filing)
        with patch.object(rules_service, "valid_filings", return_value=[filing]):
            assert rules_service.user_is_completing_party(mock_user, business) is True

    @patch.object(DigitalCredentialsRulesService, "user_submitted_filing", return_value=False)
    def test_did_not_submit_filing(self, mock_submit, rules_service, mock_user):
        """Returns False when user did not submit the filing."""
        business = MagicMock(spec=Business)
        filing = MagicMock(spec=Filing)
        with patch.object(rules_service, "valid_filings", return_value=[filing]):
            assert rules_service.user_is_completing_party(mock_user, business) is False


class TestUserSubmittedFiling:
    """Tests for user_submitted_filing."""

    def test_user_submitted(self, rules_service):
        """Returns True when user id matches filing submitter_id."""
        user = MagicMock(spec=User)
        user.id = 1
        filing = MagicMock(spec=Filing)
        filing.submitter_id = 1
        assert rules_service.user_submitted_filing(user, filing) is True

    def test_user_did_not_submit(self, rules_service):
        """Returns False when user id does not match filing submitter_id."""
        user = MagicMock(spec=User)
        user.id = 1
        filing = MagicMock(spec=Filing)
        filing.submitter_id = 2
        assert rules_service.user_submitted_filing(user, filing) is False


class TestUserMatchesCompletingParty:
    """Tests for user_matches_completing_party."""

    def test_no_completing_party_roles(self, rules_service, mock_user):
        """Returns False when no completing party roles found."""
        filing = MagicMock(spec=Filing)
        with patch.object(rules_service, "completing_party_roles", return_value=[]):
            assert rules_service.user_matches_completing_party(mock_user, filing) is False

    @patch.object(DigitalCredentialsRulesService, "user_matches_party", return_value=True)
    def test_matches_completing_party(self, mock_match, rules_service, mock_user):
        """Returns True when user matches a completing party."""
        filing = MagicMock(spec=Filing)
        role = _make_party_role("completing_party")
        with patch.object(rules_service, "completing_party_roles", return_value=[role]):
            assert rules_service.user_matches_completing_party(mock_user, filing) is True

    @patch.object(DigitalCredentialsRulesService, "user_matches_party", return_value=False)
    def test_does_not_match_completing_party(self, mock_match, rules_service, mock_user):
        """Returns False when user does not match any completing party."""
        filing = MagicMock(spec=Filing)
        role = _make_party_role("completing_party")
        with patch.object(rules_service, "completing_party_roles", return_value=[role]):
            assert rules_service.user_matches_completing_party(mock_user, filing) is False


class TestUserMatchesParty:
    """Tests for user_matches_party."""

    def test_matching_names(self, rules_service):
        """Returns True when user and party names match."""
        user = User(firstname="John", lastname="Doe")
        party = Party(first_name="John", last_name="Doe")
        assert rules_service.user_matches_party(user, party) is True

    def test_non_matching_names(self, rules_service):
        """Returns False when names do not match."""
        user = User(firstname="John", lastname="Doe")
        party = Party(first_name="Jane", last_name="Smith")
        assert rules_service.user_matches_party(user, party) is False

    def test_case_insensitive(self, rules_service):
        """Name matching is case insensitive."""
        user = User(firstname="JOHN", lastname="DOE")
        party = Party(first_name="john", last_name="doe")
        assert rules_service.user_matches_party(user, party) is True


class TestValidFilings:
    """Tests for valid_filings."""

    @patch("business_model.models.Filing.get_filings_by_types", return_value=[MagicMock(spec=Filing)])
    def test_returns_filings(self, mock_get, rules_service):
        """Returns filings from Filing.get_filings_by_types."""
        business = MagicMock(spec=Business)
        business.id = 1
        result = rules_service.valid_filings(business)
        assert len(result) == 1
        mock_get.assert_called_once_with(1, rules_service.valid_filing_types)

    @patch("business_model.models.Filing.get_filings_by_types", return_value=[])
    def test_returns_empty(self, mock_get, rules_service):
        """Returns empty list when no filings found."""
        business = MagicMock(spec=Business)
        business.id = 1
        assert rules_service.valid_filings(business) == []


class TestCompletingPartyRoles:
    """Tests for completing_party_roles."""

    @patch("business_model.models.PartyRole.get_party_roles_by_filing", return_value=[MagicMock(spec=PartyRole)])
    def test_returns_roles(self, mock_get, rules_service):
        """Returns completing party roles from PartyRole.get_party_roles_by_filing."""
        filing = MagicMock(spec=Filing)
        filing.id = 1
        result = rules_service.completing_party_roles(filing)
        assert len(result) == 1


class TestFilingPartyRoles:
    """Tests for filing_party_roles."""

    @patch("business_model.models.PartyRole.get_party_roles_by_filing", return_value=[MagicMock(spec=PartyRole)])
    def test_returns_roles(self, mock_get, rules_service):
        """Returns party roles from PartyRole.get_party_roles_by_filing."""
        filing = MagicMock(spec=Filing)
        filing.id = 1
        result = rules_service.filing_party_roles(filing)
        assert len(result) == 1
