# Copyright © 2026 Province of British Columbia
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
"""Tests for the credential-lifecycle helpers."""

from unittest.mock import MagicMock, patch

import pytest
from business_model.models import DCDefinition, DCRevocationReason

from business_registry_digital_credentials import digital_credentials_lifecycle
from business_registry_digital_credentials.digital_credentials_lifecycle import (
    DigitalCredentialError,
    get_all_digital_credentials_for_business,
    issue_digital_credential,
    replace_digital_credential,
    revoke_digital_credential,
)

# get_all_digital_credentials_for_business ----------------------------------


class TestGetAllDigitalCredentialsForBusiness:
    """Tests for get_all_digital_credentials_for_business."""

    def test_returns_empty_when_no_business_users(self):
        """Returns empty list when the business has no business_users."""
        business = MagicMock()
        business.business_users = []
        assert get_all_digital_credentials_for_business(business) == []

    def test_returns_empty_when_no_active_connection(self):
        """Returns empty list when no business_user has an active connection."""
        business_user = MagicMock()
        conn = MagicMock(is_active=False)
        business_user.connections = [conn]
        business = MagicMock(business_users=[business_user])
        assert get_all_digital_credentials_for_business(business) == []

    def test_skips_when_multiple_active_connections(self):
        """Helper only considers users with exactly one active connection."""
        business_user = MagicMock()
        business_user.connections = [
            MagicMock(is_active=True),
            MagicMock(is_active=True),
        ]
        business = MagicMock(business_users=[business_user])
        assert get_all_digital_credentials_for_business(business) == []

    def test_returns_issued_non_revoked_credentials(self):
        """Returns only credentials that are issued and not revoked."""
        good = MagicMock(is_issued=True, is_revoked=False)
        not_issued = MagicMock(is_issued=False, is_revoked=False)
        revoked = MagicMock(is_issued=True, is_revoked=True)
        conn = MagicMock(is_active=True, credentials=[good, not_issued, revoked])
        business_user = MagicMock(connections=[conn])
        business = MagicMock(business_users=[business_user])
        assert get_all_digital_credentials_for_business(business) == [good]


# issue_digital_credential --------------------------------------------------


class TestIssueDigitalCredential:
    """Tests for issue_digital_credential."""

    @patch.object(digital_credentials_lifecycle, "DCDefinition")
    def test_raises_when_definition_not_found(self, mock_definition_cls):
        """Raises when no DCDefinition matches."""
        mock_definition_cls.find_by.return_value = None
        # Preserve the real enum so isinstance check works.
        mock_definition_cls.CredentialType = DCDefinition.CredentialType
        business_user = MagicMock(id=1)
        with pytest.raises(DigitalCredentialError, match="Definition not found"):
            issue_digital_credential(business_user, DCDefinition.CredentialType.business)

    @patch.object(digital_credentials_lifecycle, "DCConnection")
    @patch.object(digital_credentials_lifecycle, "DCDefinition")
    def test_raises_when_active_connection_not_found(self, mock_definition_cls, mock_connection_cls):
        """Raises when there is no active DCConnection for the business user."""
        mock_definition_cls.find_by.return_value = MagicMock()
        mock_definition_cls.CredentialType = DCDefinition.CredentialType
        mock_connection_cls.find_active_by_business_user_id.return_value = None
        business_user = MagicMock(id=1)
        with pytest.raises(DigitalCredentialError, match="Active connection not found"):
            issue_digital_credential(business_user, DCDefinition.CredentialType.business)

    @patch.object(digital_credentials_lifecycle, "get_digital_credential_data", return_value=[])
    @patch.object(digital_credentials_lifecycle, "digital_credentials")
    @patch.object(digital_credentials_lifecycle, "DCConnection")
    @patch.object(digital_credentials_lifecycle, "DCDefinition")
    def test_raises_when_traction_issue_fails(self, mock_definition_cls, mock_connection_cls, mock_dc, mock_get_data):
        """Raises when Traction issuance returns no response."""
        mock_definition_cls.find_by.return_value = MagicMock()
        mock_definition_cls.CredentialType = DCDefinition.CredentialType
        mock_connection_cls.find_active_by_business_user_id.return_value = MagicMock()
        mock_dc.issue_credential.return_value = None
        with pytest.raises(DigitalCredentialError, match="Failed to issue credential"):
            issue_digital_credential(MagicMock(id=1), DCDefinition.CredentialType.business)

    @patch.object(digital_credentials_lifecycle, "DCCredential")
    @patch.object(digital_credentials_lifecycle, "get_digital_credential_data")
    @patch.object(digital_credentials_lifecycle, "digital_credentials")
    @patch.object(digital_credentials_lifecycle, "DCConnection")
    @patch.object(digital_credentials_lifecycle, "DCDefinition")
    def test_saves_credential_with_business_user_id(
        self,
        mock_definition_cls,
        mock_connection_cls,
        mock_dc,
        mock_get_data,
        mock_credential_cls,
    ):
        """Created DCCredential carries business_user_id (NOT NULL on the model)."""
        definition = MagicMock(id=10)
        connection = MagicMock(id=20, connection_id="conn-xyz")
        mock_definition_cls.find_by.return_value = definition
        mock_definition_cls.CredentialType = DCDefinition.CredentialType
        mock_connection_cls.find_active_by_business_user_id.return_value = connection
        mock_dc.issue_credential.return_value = {"cred_ex_id": "ex-1"}
        mock_get_data.return_value = [{"name": "credential_id", "value": "cid-1"}]

        business_user = MagicMock(id=42)
        issue_digital_credential(business_user, DCDefinition.CredentialType.business)

        mock_credential_cls.assert_called_once_with(
            definition_id=10,
            connection_id=20,
            business_user_id=42,
            credential_exchange_id="ex-1",
            credential_id="cid-1",
        )
        mock_credential_cls.return_value.save.assert_called_once()

    @patch.object(digital_credentials_lifecycle, "DCCredential")
    @patch.object(digital_credentials_lifecycle, "get_digital_credential_data", return_value=[])
    @patch.object(digital_credentials_lifecycle, "digital_credentials")
    @patch.object(digital_credentials_lifecycle, "DCConnection")
    @patch.object(digital_credentials_lifecycle, "DCDefinition")
    def test_accepts_credential_type_as_string(
        self,
        mock_definition_cls,
        mock_connection_cls,
        mock_dc,
        mock_get_data,
        mock_credential_cls,
    ):
        """credential_type as a name string is normalized to the enum."""
        mock_definition_cls.find_by.return_value = MagicMock(id=10)
        mock_definition_cls.CredentialType = DCDefinition.CredentialType
        mock_connection_cls.find_active_by_business_user_id.return_value = MagicMock(id=20, connection_id="c")
        mock_dc.issue_credential.return_value = {"cred_ex_id": "ex-1"}

        issue_digital_credential(MagicMock(id=1), "business")

        # find_by was called with the resolved enum member, not the raw string.
        passed_type = mock_definition_cls.find_by.call_args[0][0]
        assert passed_type == DCDefinition.CredentialType.business


# revoke_digital_credential -------------------------------------------------


class TestRevokeDigitalCredential:
    """Tests for revoke_digital_credential."""

    def test_raises_when_not_issued(self):
        """Raises when the credential has not yet been issued."""
        credential = MagicMock(is_issued=False, is_revoked=False)
        with pytest.raises(DigitalCredentialError, match="not issued yet or is revoked already"):
            revoke_digital_credential(credential, DCRevocationReason.UPDATED_INFORMATION)

    def test_raises_when_already_revoked(self):
        """Raises when the credential is already revoked."""
        credential = MagicMock(is_issued=True, is_revoked=True)
        with pytest.raises(DigitalCredentialError, match="not issued yet or is revoked already"):
            revoke_digital_credential(credential, DCRevocationReason.UPDATED_INFORMATION)

    def test_raises_when_no_active_connection(self):
        """Raises when the credential's connection is missing or inactive."""
        credential = MagicMock(is_issued=True, is_revoked=False, connection=None)
        with pytest.raises(DigitalCredentialError, match="Active connection not found"):
            revoke_digital_credential(credential, DCRevocationReason.UPDATED_INFORMATION)

    @patch.object(digital_credentials_lifecycle, "digital_credentials")
    def test_raises_when_traction_revoke_fails(self, mock_dc):
        """Raises when Traction returns None on revoke."""
        connection = MagicMock(is_active=True, connection_id="c")
        credential = MagicMock(is_issued=True, is_revoked=False, connection=connection)
        mock_dc.revoke_credential.return_value = None
        with pytest.raises(DigitalCredentialError, match="Failed to revoke credential"):
            revoke_digital_credential(credential, DCRevocationReason.UPDATED_INFORMATION)

    @patch.object(digital_credentials_lifecycle, "digital_credentials")
    def test_marks_revoked_and_saves(self, mock_dc):
        """On success, sets is_revoked=True and saves the credential."""
        connection = MagicMock(is_active=True, connection_id="c")
        credential = MagicMock(is_issued=True, is_revoked=False, connection=connection)
        mock_dc.revoke_credential.return_value = {"ok": True}

        revoke_digital_credential(credential, DCRevocationReason.UPDATED_INFORMATION)

        assert credential.is_revoked is True
        credential.save.assert_called_once()


# replace_digital_credential ------------------------------------------------


class TestReplaceDigitalCredential:
    """Tests for replace_digital_credential."""

    @patch.object(digital_credentials_lifecycle, "issue_digital_credential")
    @patch.object(digital_credentials_lifecycle, "revoke_digital_credential")
    @patch.object(digital_credentials_lifecycle, "digital_credentials")
    def test_revokes_then_issues_then_deletes(self, mock_dc, mock_revoke, mock_issue):
        """Replacement path: revoke existing → issue new → delete old."""
        credential = MagicMock(is_issued=True, is_revoked=False)
        mock_dc.fetch_credential_exchange_record.return_value = {"id": "ex-1"}
        mock_dc.remove_credential_exchange_record.return_value = {"removed": True}

        replace_digital_credential(
            credential,
            DCDefinition.CredentialType.business,
            DCRevocationReason.UPDATED_INFORMATION,
        )

        mock_revoke.assert_called_once_with(credential, DCRevocationReason.UPDATED_INFORMATION)
        mock_issue.assert_called_once_with(credential.connection.business_user, DCDefinition.CredentialType.business)
        credential.delete.assert_called_once()

    @patch.object(digital_credentials_lifecycle, "issue_digital_credential")
    @patch.object(digital_credentials_lifecycle, "revoke_digital_credential")
    @patch.object(digital_credentials_lifecycle, "digital_credentials")
    def test_skips_revoke_when_already_revoked(self, mock_dc, mock_revoke, mock_issue):
        """Does not call revoke when the existing credential is already revoked."""
        credential = MagicMock(is_issued=True, is_revoked=True)
        mock_dc.fetch_credential_exchange_record.return_value = None

        replace_digital_credential(
            credential,
            DCDefinition.CredentialType.business,
            DCRevocationReason.UPDATED_INFORMATION,
        )

        mock_revoke.assert_not_called()
        mock_issue.assert_called_once()

    @patch.object(digital_credentials_lifecycle, "issue_digital_credential")
    @patch.object(digital_credentials_lifecycle, "revoke_digital_credential")
    @patch.object(digital_credentials_lifecycle, "digital_credentials")
    def test_raises_when_remove_exchange_record_fails(self, mock_dc, mock_revoke, mock_issue):
        """Raises when the credential exchange record exists but removal fails."""
        credential = MagicMock(is_issued=True, is_revoked=True)
        mock_dc.fetch_credential_exchange_record.return_value = {"id": "ex-1"}
        mock_dc.remove_credential_exchange_record.return_value = None

        with pytest.raises(DigitalCredentialError, match="Failed to remove credential exchange record"):
            replace_digital_credential(
                credential,
                DCDefinition.CredentialType.business,
                DCRevocationReason.UPDATED_INFORMATION,
            )
        mock_issue.assert_not_called()
        credential.delete.assert_not_called()
