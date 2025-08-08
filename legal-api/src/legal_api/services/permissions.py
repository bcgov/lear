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
from http import HTTPStatus

from flask import jsonify

from legal_api.models.authorized_role_permission import AuthorizedRolePermission
from legal_api.services import cache
from legal_api.services.authz import (
    STAFF_ROLE, SBC_STAFF_ROLE, CONTACT_CENTRE_STAFF_ROLE, MAXIMUS_STAFF_ROLE, PUBLIC_USER
    )
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