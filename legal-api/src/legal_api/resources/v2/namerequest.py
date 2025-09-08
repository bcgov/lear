# Copyright © 2021 Province of British Columbia
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
"""Searching on a namerequest.

Provides a proxy endpoint to retrieve name request data.
"""
from flask import Blueprint, abort, current_app, jsonify, make_response, request
from flask_cors import cross_origin

from legal_api.utils.auth import jwt
from legal_api.services import namex
from legal_api.services.bootstrap import AccountService
from legal_api.services.permissions import ListActionsPermissionsAllowed, PermissionService


bp = Blueprint('NAMEREQUEST2', __name__, url_prefix='/api/v2/nameRequests')


@bp.route('/<string:identifier>/validate', methods=['GET'])
@cross_origin(origin='*')
@jwt.requires_auth
def validate_with_contact_info(identifier):
    """Return a JSON object with name request information."""
    try:
        nr_response = namex.query_nr_number(identifier)
        # Errors in general will just pass though,
        # 404 is overriden as it is giving namex-api specific messaging
        if nr_response.status_code == 404:
            return make_response(jsonify(message='{} not found.'.format(identifier)), 404)

        nr_json = nr_response.json()

        # Check if the user has ADD_ENTITY_NO_AUTHENTICATION permission. If so, do not need to validate email and phone
        authorized_permissions = PermissionService.get_authorized_permissions_for_user()

        allowed_permission = ListActionsPermissionsAllowed.ADD_ENTITY_NO_AUTHENTICATION.value

        if allowed_permission in authorized_permissions:
            return jsonify(nr_json)

        # Check the NR is affiliated with this account
        orgs_response = AccountService.get_account_by_affiliated_identifier(identifier)
               
         # If affiliated with the account, return the NR
        if len(orgs_response['orgs']):
            return jsonify(nr_json)

        # The request must include email or phone number
        email = request.args.get('email', None)
        phone = request.args.get('phone', None)
        if not (email or phone):
            return make_response(jsonify(message='The request must include email or phone number.'), 403)

        # If NR is not affiliated, validate the email and phone
        nr_phone = nr_json.get('applicants').get('phoneNumber')
        nr_email = nr_json.get('applicants').get('emailAddress')
        if (phone and phone != nr_phone) or (email and email != nr_email):
            return make_response(jsonify(message='Invalid email or phone number.'), 400)

        return jsonify(nr_json)
    except Exception as err:
        current_app.logger.error(err)
        abort(500)
        return {}, 500  # to appease the linter
