# Copyright © 2022 Province of British Columbia
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

"""API endpoints for managing an Digital Credentials resource."""
from http import HTTPStatus

from flask import Blueprint, current_app, jsonify, request
from flask_cors import cross_origin

from legal_api.models import Business, DCConnection
from legal_api.services import digital_credentials
from legal_api.utils.auth import jwt

from .bp import bp


bp_dc = Blueprint('DIGITAL_CREDENTIALS', __name__, url_prefix='/api/v2/digitalCredentials')  # Blueprint for webhook


@bp.route('/<string:identifier>/digitalCredentials/invitation', methods=['POST', 'OPTIONS'], strict_slashes=False)
@cross_origin(origin='*')
@jwt.requires_auth
def create_invitation(identifier):
    """Create a new connection invitation."""
    business = Business.find_by_identifier(identifier)
    if not business:
        return jsonify({'message': f'{identifier} not found.'}), HTTPStatus.NOT_FOUND

    active_connection = DCConnection.find_active_by(business_id=business.id)
    if active_connection:
        return jsonify({'message': f'{identifier} already have an active connection.'}), HTTPStatus.UNPROCESSABLE_ENTITY

    # check whether this business has an existing connection which is not active
    connections = DCConnection.find_by(business_id=business.id, connection_state='invitation')
    if connections:
        connection = connections[0]
    else:
        invitation = digital_credentials.create_invitation()
        if not invitation:
            return jsonify({'message': 'Unable to create an invitation.'}), HTTPStatus.INTERNAL_SERVER_ERROR

        connection = DCConnection(
            connection_id=invitation['connection_id'],
            invitation_url=invitation['invitation_url'],
            is_active=False,
            connection_state='invitation',
            business_id=business.id
        )
        connection.save()

    return jsonify({'invitationUrl': connection.invitation_url}), HTTPStatus.OK


@bp.route('/<string:identifier>/digitalCredentials/connection', methods=['GET', 'OPTIONS'], strict_slashes=False)
@cross_origin(origin='*')
@jwt.requires_auth
def get_active_connection(identifier):
    """Get active connection for this business."""
    business = Business.find_by_identifier(identifier)
    if not business:
        return jsonify({'message': f'{identifier} not found.'}), HTTPStatus.NOT_FOUND

    connection = DCConnection.find_active_by(business_id=business.id)
    if not connection:
        return jsonify({'message': 'No active connection found.'}), HTTPStatus.NOT_FOUND

    return jsonify(connection.json), HTTPStatus.OK


@bp_dc.route('/topic/<string:topic_name>', methods=['POST', 'OPTIONS'], strict_slashes=False)
@cross_origin(origin='*')
def webhook_notification(topic_name: str):
    """To receive notification from aca-py admin api."""
    json_input = request.get_json()
    try:
        if topic_name == 'connections':
            connection = DCConnection.find_by_connection_id(json_input['connection_id'])
            if connection and json_input['state'] == 'active':
                connection.connection_state = 'active'
                connection.is_active = True
                connection.save()
    except Exception as err:
        current_app.logger.error(err)
        raise err

    return jsonify({'message': 'Webhook received.'}), HTTPStatus.OK
