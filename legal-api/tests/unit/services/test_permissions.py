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

"""
Tests to assure the permissions for filllings.
"""
import pytest
from unittest.mock import patch, MagicMock

from legal_api.services.authz import STAFF_ROLE, PUBLIC_USER
from legal_api.services.permissions import PermissionService
from legal_api.core.filing import Filing as CoreFiling


@pytest.fixture
def mock_token_info(monkeypatch):
    """Patch token with mock data."""
    mock_g = MagicMock()
    monkeypatch.setattr('legal_api.services.permissions.g', mock_g)
    return mock_g


def test_has_permission_with_incorrect_permission(mock_token_info, app):
    """Should return False when user does not have the permission for the action."""
    mock_token_info.jwt_oidc_token_info = {'realm_access': {'roles': [PUBLIC_USER]}}
    with app.app_context():
        with patch.object(PermissionService, 'get_authorized_permissions_for_user', return_value=['ADDRESS_CHANGE_FILING']):
            result = PermissionService.has_permissions_for_action(CoreFiling.FilingTypes.AMALGAMATIONAPPLICATION.value, 
                                                                 legal_type='BC', filing_sub_type='amalgamation')
            assert result is False


def test_has_permission_with_correct_permission(mock_token_info):
    """Should return True when user has the correct permission for the action."""
    mock_token_info.jwt_oidc_token_info = {'realm_access': {'roles': [STAFF_ROLE]}}

    with patch.object(PermissionService, 'get_authorized_permissions_for_user', return_value=['AMALGAMATION_FILING']):
        result = PermissionService.has_permissions_for_action(CoreFiling.FilingTypes.AMALGAMATIONAPPLICATION.value, legal_type='BC', filing_sub_type='amalgamation')
        assert result is True


def test_permission_fallback_on_role_priority(mock_token_info):
    """Should use the highest priority role from token."""
    mock_token_info.jwt_oidc_token_info = {'realm_access': {'roles': [PUBLIC_USER, STAFF_ROLE]}}

    with patch.object(PermissionService, 'get_authorized_permissions_for_user', return_value=['ALTERATION_FILING']):
        result = PermissionService.has_permissions_for_action(CoreFiling.FilingTypes.ALTERATION.value, legal_type='BC', filing_sub_type='alteration')
        assert result is True


def test_find_roles_for_filing_type_existing():
    """Should return the mapped permission name for a known filing type."""
    permission = PermissionService.find_roles_for_filing_type(CoreFiling.FilingTypes.AGMEXTENSION.value, legal_type='BC', filing_sub_type='extension')
    assert permission == 'AGM_EXTENSION_FILING'


def test_find_roles_for_filing_type_unknown():
    """Should return empty string for unknown filing type."""
    permission = PermissionService.find_roles_for_filing_type('UNKNOWN_FILING', legal_type='BC', filing_sub_type='unknown')
    assert permission == ''

def test_staff_filing_with_staff_filings_permission(mock_token_info, app):
    """Should return True for staff filing types when user has STAFF_FILINGS permission."""
    mock_token_info.jwt_oidc_token_info = {'realm_access': {'roles': [STAFF_ROLE]}}

    with patch.object(PermissionService, 'get_authorized_permissions_for_user', return_value=['STAFF_FILINGS']):
        result = PermissionService.has_permissions_for_action(CoreFiling.FilingTypes.AMALGAMATIONOUT.value, legal_type='BC', filing_sub_type='')
        assert result is True

def test_staff_filing_without_staff_filings_permission(mock_token_info, app):
    """Should return False for staff filing types when user does not have STAFF_FILINGS permission."""
    from flask import current_app

    mock_token_info.jwt_oidc_token_info = {'realm_access': {'roles': [PUBLIC_USER]}}

    with app.app_context():
        with patch.object(PermissionService, 'get_authorized_permissions_for_user', return_value=[]):
            result = PermissionService.has_permissions_for_action(CoreFiling.FilingTypes.PUTBACKON.value, legal_type='BC', filing_sub_type='')
            assert result is False

def test_staff_filing_with_no_staff_permissions_but_regular_filing_permission(mock_token_info, app):
    """Should return False for staff filing types when user has no permissions."""
    from flask import current_app

    mock_token_info.jwt_oidc_token_info = {'realm_access': {'roles': [PUBLIC_USER]}}

    with app.app_context():
        with patch.object(PermissionService, 'get_authorized_permissions_for_user', return_value=['']):
            result = PermissionService.has_permissions_for_action(CoreFiling.FilingTypes.PUTBACKON.value, legal_type='BC', filing_sub_type='')
            assert result is False

        with patch.object(PermissionService, 'get_authorized_permissions_for_user', return_value=['ALTERATION_FILING']):
            result = PermissionService.has_permissions_for_action(CoreFiling.FilingTypes.ALTERATION.value, legal_type='BC', filing_sub_type='')
            assert result is True
