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
"""Retrieve permissions for a user role."""
from http import HTTPStatus

from flask import Blueprint, jsonify
from flask_cors import cross_origin

from legal_api.models.authorized_role_permission import AuthorizedRolePermission
from legal_api.services.authz import get_authorized_user_role
from legal_api.utils.auth import jwt


bp = Blueprint('PERMISSIONS2', __name__, url_prefix='/api/v2/permissions')


@bp.route('', methods=['GET'])
@cross_origin(origin='*')
@jwt.requires_auth
def get_permissions():
    """Return a list of authorized permissions for the user."""
    authorized_role = get_authorized_user_role()
    if not authorized_role:
        return jsonify({'message': 'No authorized role found.', 'authorizedPermissions': []}), HTTPStatus.OK
    authorized_permissions = AuthorizedRolePermission.get_authorized_permissions_by_role_name(authorized_role)
    return jsonify({'authorizedPermissions': authorized_permissions}), HTTPStatus.OK
