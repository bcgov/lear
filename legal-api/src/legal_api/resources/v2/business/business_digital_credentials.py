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
from datetime import datetime
from http import HTTPStatus

from flask import Blueprint, current_app, jsonify, request
from flask_cors import cross_origin

from legal_api.models import Business, DCConnection, DCDefinition, DCIssuedCredential
from legal_api.services import digital_credentials
from legal_api.utils.auth import jwt

from .bp import bp


bp_dc = Blueprint('DIGITAL_CREDENTIALS', __name__, url_prefix='/api/v2/digitalCredentials')  # Blueprint for webhook


@bp.route('/<string:identifier>/digitalCredentials/invitation', methods=['POST'], strict_slashes=False)
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


@bp.route('/<string:identifier>/digitalCredentials', methods=['GET', 'OPTIONS'], strict_slashes=False)
@cross_origin(origin='*')
@jwt.requires_auth
def get_issued_credentials(identifier):
    """Get all issued credentials."""
    business = Business.find_by_identifier(identifier)
    if not business:
        return jsonify({'message': f'{identifier} not found.'}), HTTPStatus.NOT_FOUND

    connection = DCConnection.find_active_by(business_id=business.id)
    if not connection:
        return jsonify({'issuedCredentials': []}), HTTPStatus.OK

    issued_credentials = DCIssuedCredential.find_by(dc_connection_id=connection.id)
    if not issued_credentials:
        return jsonify({'issuedCredentials': []}), HTTPStatus.OK

    response = []
    for issued_credential in issued_credentials:
        definition = DCDefinition.find_by_id(issued_credential.dc_definition_id)
        response.append({
            'legalName': business.legal_name,
            'credentialType': definition.credential_type.name,
            'isIssued': issued_credential.is_issued,
            'dateOfIssue': issued_credential.date_of_issue.isoformat() if issued_credential.date_of_issue else '',
            'isRevoked': issued_credential.is_revoked
        })
    return jsonify({'issuedCredentials': response}), HTTPStatus.OK


@bp.route('/<string:identifier>/digitalCredentials/<string:credential_type>', methods=['POST'], strict_slashes=False)
@cross_origin(origin='*')
@jwt.requires_auth
def send_credential(identifier, credential_type):
    """Issue credentials to the connection."""
    business = Business.find_by_identifier(identifier)
    if not business:
        return jsonify({'message': f'{identifier} not found'}), HTTPStatus.NOT_FOUND

    connection = DCConnection.find_active_by(business_id=business.id)
    definition = DCDefinition.find_by_credential_type(DCDefinition.CredentialType[credential_type])

    issued_credentials = DCIssuedCredential.find_by(dc_connection_id=connection.id,
                                                    dc_definition_id=definition.id)
    if issued_credentials and issued_credentials[0].credential_exchange_id:
        return jsonify({'message': 'Already requested to issue credential.'}), HTTPStatus.INTERNAL_SERVER_ERROR

    response = digital_credentials.issue_credential(
        connection_id=connection.connection_id,
        definition=definition,
        data=_get_data_for_credential(definition.credential_type, business)
    )
    if not response:
        return jsonify({'message': 'Failed to issue credential.'}), HTTPStatus.INTERNAL_SERVER_ERROR

    issued_credential = DCIssuedCredential(
        dc_definition_id=definition.id,
        dc_connection_id=connection.id,
        credential_exchange_id=response['credential_exchange_id']
    )
    issued_credential.save()

    return jsonify({'message': 'Issue Credential is initiated.'}), HTTPStatus.OK


def _get_data_for_credential(credential_type: DCDefinition.CredentialType, business: Business):
    if credential_type == DCDefinition.CredentialType.business:
        return [
            {
                'name': 'legalName',
                'value': business.legal_name
            },
            {
                'name': 'foundingDate',
                'value': business.founding_date.isoformat()
            },
            {
                'name': 'taxId',
                'value': business.tax_id or ''
            },
            {
                'name': 'homeJurisdiction',
                'value': 'BC'  # for corp types that are not -xpro, the jurisdiction is BC
            },
            {
                'name': 'legalType',
                'value': business.legal_type
            },
            {
                'name': 'identifier',
                'value': business.identifier
            }
        ]

    return None


@bp_dc.route('/topic/<string:topic_name>', methods=['POST'], strict_slashes=False)
@cross_origin(origin='*')
@jwt.requires_auth
def webhook_notification(topic_name: str):
    """To receive notification from aca-py admin api."""
    json_input = request.get_json()
    try:
        if topic_name == 'connections':
            connection = DCConnection.find_by_connection_id(json_input['connection_id'])
            # Trinsic Wallet will send `active` only when it’s used the first time.
            # Looking for `response` state to handle it.
            if connection and not connection.is_active and json_input['state'] in ('response', 'active'):
                connection.connection_state = 'active'
                connection.is_active = True
                connection.save()
        elif topic_name == 'issue_credential':
            issued_credential = DCIssuedCredential.find_by_credential_exchange_id(json_input['credential_exchange_id'])
            if issued_credential and json_input['state'] == 'credential_issued':
                issued_credential.date_of_issue = datetime.utcnow()
                issued_credential.is_issued = True
                issued_credential.save()
    except Exception as err:
        current_app.logger.error(err)
        raise err

    return jsonify({'message': 'Webhook received.'}), HTTPStatus.OK
