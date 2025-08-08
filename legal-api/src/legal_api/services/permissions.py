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

# pylint: disable=too-many-lines
"""This manages all of the authentication and authorization service."""
from enum import Enum
from http import HTTPStatus

from flask import jsonify
from flask import current_app, g

from urllib3.util.retry import Retry

from legal_api.models.authorized_role_permission import AuthorizedRolePermission
from legal_api.services.cache import cache

class ListFilingsPermissionsAllowed(str, Enum):
    """Define an enum for permissions checks."""

    STAFF_FILINGS = 'STAFF_FILINGS'
    TRANSITION_FILING = 'TRANSITION_FILING'
    VOLUNTARY_DISSOLUTION_FILING = 'VOLUNTARY_DISSOLUTION_FILING'
    ADMIN_DISSOLUTION_FILING = 'ADMIN_DISSOLUTION_FILING'
    AGM_CHG_LOCATION_FILING = 'AGM_CHG_LOCATION_FILING'
    AGM_EXTENSION_FILING = 'AGM_EXTENSION_FILING'
    ALTERATION_FILING = 'ALTERATION_FILING'
    AMALGAMATION_FILING = 'AMALGAMATION_FILING'
    ANNUAL_REPORT_FILING = 'ANNUAL_REPORT_FILING'
    CONSENT_AMALGAMATION_OUT_FILING = 'CONSENT_AMALGAMATION_OUT_FILING'
    CONSENT_CONTINUATION_OUT_FILING = 'CONSENT_CONTINUATION_OUT_FILING'
    CONTINUATION_IN_FILING = 'CONTINUATION_IN_FILING'
    CORRECTION_FILING = 'CORRECTION_FILING'
    COURT_ORDER_FILING = 'COURT_ORDER_FILING'
    DELAY_DISSOLUTION_FILING = 'DELAY_DISSOLUTION_FILING'
    DIRECTOR_CHANGE_FILING = 'DIRECTOR_CHANGE_FILING'
    FIRM_CHANGE_FILING = 'FIRM_CHANGE_FILING'
    FIRM_CONVERSION_FILING = 'FIRM_CONVERSION_FILING'
    FIRM_DISSOLUTION_FILING = 'FIRM_DISSOLUTION_FILING'
    INCORPORATION_APPLICATION_FILING = 'INCORPORATION_APPLICATION_FILING'
    NOTICE_WITHDRAWAL_FILING = 'NOTICE_WITHDRAWAL_FILING'
    RESTORATION_REINSTATEMENT_FILING = 'RESTORATION_REINSTATEMENT_FILING'
    REGISTRATION_FILING = 'REGISTRATION_FILING'
    SPECIAL_RESOLUTION_FILING = 'SPECIAL_RESOLUTION_FILING'
    ADDRESS_CHANGE_FILING = 'ADDRESS_CHANGE_FILING'
    
class PermissionService:
    """Service to manage permissions for user roles."""

    @staticmethod
    def get_authorized_permissions_for_user():
        """
        Returns a JSON response containing the authorized permissions for the current user.
        """
        authorized_role = PermissionService.get_authorized_user_role()
        if not authorized_role:
            return jsonify({
                'message': 'No authorized role found.',
                'authorizedPermissions': []
            }), HTTPStatus.OK

        cache_key = f'authorized_permissions_{authorized_role}'
        cached_permissions = cache.get(cache_key)

        if cached_permissions:
            authorized_permissions = cached_permissions
        else:
            authorized_permissions = AuthorizedRolePermission.get_authorized_permissions_by_role_name(authorized_role)
            cache.set(cache_key, authorized_permissions)

        return authorized_permissions
    
    @staticmethod
    def get_authorized_user_role() -> str:
        """Return the first matching authorized role from the JWT, based on priority."""
        from legal_api.services.authz import (
    STAFF_ROLE, SBC_STAFF_ROLE, CONTACT_CENTRE_STAFF_ROLE, MAXIMUS_STAFF_ROLE, PUBLIC_USER
    )
        role_priority = [
            STAFF_ROLE,
            SBC_STAFF_ROLE,
            CONTACT_CENTRE_STAFF_ROLE,
            MAXIMUS_STAFF_ROLE,
            PUBLIC_USER,
        ]

        token_info = getattr(g, 'jwt_oidc_token_info', {}) or {}

        roles_in_token = token_info.get('realm_access', {}).get('roles', [])
        for role in role_priority:
            if role in roles_in_token:
                return role
        return None
    
    @staticmethod
    def get_filing_permission_mapping():
        """Return dictionary containing rules for filings are allowed for different roles."""
        # pylint: disable=import-outside-toplevel
        from legal_api.core.filing import Filing as CoreFiling

        return {
                CoreFiling.FilingTypes.TRANSITION.value:
                ListFilingsPermissionsAllowed.TRANSITION_FILING.value
                ,
                CoreFiling.FilingTypesCompact.DISSOLUTION_VOLUNTARY.value:
            ListFilingsPermissionsAllowed.VOLUNTARY_DISSOLUTION_FILING.value
                ,
                CoreFiling.FilingTypesCompact.DISSOLUTION_ADMINISTRATIVE.value:
                ListFilingsPermissionsAllowed.ADMIN_DISSOLUTION_FILING.value
                ,
                CoreFiling.FilingTypes.AGMLOCATIONCHANGE.value:
                ListFilingsPermissionsAllowed.AGM_CHG_LOCATION_FILING.value
                ,
                CoreFiling.FilingTypes.AGMEXTENSION.value:
                ListFilingsPermissionsAllowed.AGM_EXTENSION_FILING.value
                ,
                CoreFiling.FilingTypes.ALTERATION.value:
                ListFilingsPermissionsAllowed.ALTERATION_FILING.value
                ,
                CoreFiling.FilingTypes.AMALGAMATIONAPPLICATION.value:
                ListFilingsPermissionsAllowed.AMALGAMATION_FILING.value
                ,
                CoreFiling.FilingTypes.ANNUALREPORT.value:
                ListFilingsPermissionsAllowed.ANNUAL_REPORT_FILING.value
                ,
                CoreFiling.FilingTypes.CONSENTAMALGAMATIONOUT.value:
                ListFilingsPermissionsAllowed.CONSENT_AMALGAMATION_OUT_FILING.value
                ,
                CoreFiling.FilingTypes.CONSENTCONTINUATIONOUT.value:
                ListFilingsPermissionsAllowed.CONSENT_CONTINUATION_OUT_FILING.value
                ,
                CoreFiling.FilingTypes.CONTINUATIONIN.value:
                ListFilingsPermissionsAllowed.CONTINUATION_IN_FILING.value
                ,
                CoreFiling.FilingTypes.CORRECTION.value:
                ListFilingsPermissionsAllowed.CORRECTION_FILING.value
                ,
                CoreFiling.FilingTypes.COURTORDER.value:
                ListFilingsPermissionsAllowed.COURT_ORDER_FILING.value
                ,
                CoreFiling.FilingTypes.DISSOLUTION.value:
                ListFilingsPermissionsAllowed.FIRM_CHANGE_FILING.value
                ,
                CoreFiling.FilingTypes.CHANGEOFDIRECTORS.value:
                ListFilingsPermissionsAllowed.DIRECTOR_CHANGE_FILING.value
                ,
                CoreFiling.FilingTypes.CHANGEOFREGISTRATION.value:
                ListFilingsPermissionsAllowed.FIRM_CHANGE_FILING.value
                ,
                CoreFiling.FilingTypes.CONVERSION.value:
                ListFilingsPermissionsAllowed.FIRM_CONVERSION_FILING.value
                ,
                CoreFiling.FilingTypes.INCORPORATIONAPPLICATION.value:
                ListFilingsPermissionsAllowed.INCORPORATION_APPLICATION_FILING.value
                ,
                CoreFiling.FilingTypes.NOTICEOFWITHDRAWAL.value:
                ListFilingsPermissionsAllowed.NOTICE_WITHDRAWAL_FILING.value
                ,
                CoreFiling.FilingTypes.RESTORATION.value:
                ListFilingsPermissionsAllowed.RESTORATION_REINSTATEMENT_FILING.value
                ,
                CoreFiling.FilingTypes.REGISTRATION.value:
                ListFilingsPermissionsAllowed.REGISTRATION_FILING.value
                ,
                CoreFiling.FilingTypes.SPECIALRESOLUTION.value:
                ListFilingsPermissionsAllowed.SPECIAL_RESOLUTION_FILING.value
                ,
                CoreFiling.FilingTypes.CHANGEOFADDRESS.value:
                ListFilingsPermissionsAllowed.ADDRESS_CHANGE_FILING.value
                    }
    
    @staticmethod
    def find_roles_for_filing_type(filing_type_value: str):
        """Find roles that are allowed to perform the given filing type."""
        allowable_permissions = PermissionService.get_filing_permission_mapping()
        roles_with_filing = allowable_permissions.get(filing_type_value, '')
        return roles_with_filing

    @staticmethod
    def has_permissions_for_action(filing_type: str) -> bool:
        """Check if the user has permissions for the action per permissions table."""
        authorized_permissions = PermissionService.get_authorized_permissions_for_user()
        if not authorized_permissions or not isinstance(authorized_permissions, list):
            current_app.logger.error('No authorized permissions found for user.')
            return False
        roles_in_filings = PermissionService.find_roles_for_filing_type(filing_type)
        if roles_in_filings in authorized_permissions:
            return True
        else:
            current_app.logger.warning(f'User does not have permission for filing type: {filing_type}')
        return False