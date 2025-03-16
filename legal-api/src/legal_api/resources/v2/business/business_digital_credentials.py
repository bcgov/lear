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

"""API endpoints for managing an Digital Credentials resource."""
from datetime import datetime
from http import HTTPStatus

import jwt as pyjwt
from flask import Blueprint, current_app, jsonify, request
from flask_cors import cross_origin

from legal_api.decorators import can_access_digital_credentials
from legal_api.models import Business, DCBusinessUser, DCConnection, DCCredential, DCDefinition, DCRevocationReason, User
from legal_api.services import digital_credentials
from legal_api.services.digital_credentials_helpers import extract_invitation_message_id, get_digital_credential_data
from legal_api.services.digital_credentials_rules import DigitalCredentialsRulesService
from legal_api.utils.auth import jwt

from .bp import bp


rules = DigitalCredentialsRulesService()

bp_dc = Blueprint('DIGITAL_CREDENTIALS', __name__,
                  url_prefix='/api/v2/digitalCredentials')  # Blueprint for webhook


@bp.route('/<string:identifier>/digitalCredentials/invitation', methods=['POST'], strict_slashes=False)
@cross_origin(origin='*')
@jwt.requires_auth
@can_access_digital_credentials
def create_invitation(identifier):
    """Create a new connection invitation."""
    if not (business := Business.find_by_identifier(identifier)):
        return jsonify({'message': f'{identifier} not found.'}), HTTPStatus.NOT_FOUND

    if DCConnection.find_active_by(business_id=business.id):
        return jsonify({'message': f'{identifier} already have an active connection.'}), HTTPStatus.UNPROCESSABLE_ENTITY

    if (connections := DCConnection.find_by_filters([
        DCConnection.business_id == business.id,
        DCConnection.connection_state == DCConnection.State.INVITATION_SENT.value,
    ])):
        connection = connections[0]
    else:
        if not (response := digital_credentials.create_invitation()):
            return jsonify({'message': 'Unable to create an invitation.'}), HTTPStatus.INTERNAL_SERVER_ERROR

        invitation_message_id = extract_invitation_message_id(response)

        connection = DCConnection(
            connection_id=invitation_message_id,
            invitation_url=response['invitation_url'],
            is_active=False,
            connection_state=DCConnection.State.INVITATION_SENT.value,
            business_id=business.id
        )
        connection.save()

    return jsonify(connection.json), HTTPStatus.OK


@bp.route('/<string:identifier>/digitalCredentials/connections', methods=['GET', 'OPTIONS'], strict_slashes=False)
@cross_origin(origin='*')
@jwt.requires_auth
@can_access_digital_credentials
def get_connections(identifier):
    """
    Get connections for this business

    We currently only support one connection per business user.
    We still return a list of connections to be consistent with RESTful API naming conventions.
    """
    if not (token := pyjwt.decode(jwt.get_token_auth_header(), options={'verify_signature': False})):
        return jsonify({'message': 'Unable to decode JWT'}, HTTPStatus.UNAUTHORIZED)

    if not (business := Business.find_by_identifier(identifier)):
        return jsonify({'message': f'{identifier} not found.'}), HTTPStatus.NOT_FOUND

    if not (user := User.find_by_jwt_token(token)):
        return jsonify({'message': 'User not found'}, HTTPStatus.NOT_FOUND)

    if not (business_user := DCBusinessUser.find_by(business_id=business.id, user_id=user.id)):
        return jsonify({'message': 'Business User not found'}, HTTPStatus.NOT_FOUND)

    if not (connection := DCConnection.find_by_business_user_id(business_user_id=business_user.id)):
        return jsonify({'connections': []}), HTTPStatus.OK

    response = []
    response.append(connection.json)
    return jsonify({'connections': response}), HTTPStatus.OK


@bp.route('/<string:identifier>/digitalCredentials/connections/<string:connection_id>/attest',
          methods=['POST'], strict_slashes=False)
@cross_origin(origin='*')
@jwt.requires_auth
@can_access_digital_credentials
def attest_connection(identifier, connection_id):
    """Attest a connection."""
    if not Business.find_by_identifier(identifier):
        return jsonify({'message': f'{identifier} not found.'}), HTTPStatus.NOT_FOUND

    if not (connection := DCConnection.find_by_connection_id(connection_id=connection_id)):
        return jsonify({'message': f'{identifier} connection not found.'}), HTTPStatus.NOT_FOUND

    if digital_credentials.attest_connection(connection_id=connection.connection_id) is None:
        return jsonify({'message': 'Unable to request connection attestation.'}), HTTPStatus.INTERNAL_SERVER_ERROR

    return jsonify({'message': 'Connection attestation request sent.'}), HTTPStatus.OK


@bp.route('/<string:identifier>/digitalCredentials/connections/<string:connection_id>',
          methods=['DELETE'], strict_slashes=False)
@cross_origin(origin='*')
@jwt.requires_auth
@can_access_digital_credentials
def delete_connection(identifier, connection_id):
    """Delete a connection."""
    if not Business.find_by_identifier(identifier):
        return jsonify({'message': f'{identifier} not found.'}), HTTPStatus.NOT_FOUND

    if not (connection := DCConnection.find_by_connection_id(connection_id=connection_id)):
        return jsonify({'message': f'{identifier} connection not found.'}), HTTPStatus.NOT_FOUND

    if (connection.connection_state != DCConnection.State.INVITATION_SENT.value and
            digital_credentials.remove_connection_record(connection_id=connection.connection_id) is None):
        return jsonify({'message': 'Failed to remove connection record.'}), HTTPStatus.INTERNAL_SERVER_ERROR

    connection.delete()
    return jsonify({'message': 'Connection has been deleted.'}), HTTPStatus.OK


@bp.route('/<string:identifier>/digitalCredentials/activeConnection', methods=['DELETE'], strict_slashes=False)
@cross_origin(origin='*')
@jwt.requires_auth
@can_access_digital_credentials
def delete_active_connection(identifier):
    """Delete an active connection for this business."""
    if not (business := Business.find_by_identifier(identifier)):
        return jsonify({'message': f'{identifier} not found.'}), HTTPStatus.NOT_FOUND

    if not (connection := DCConnection.find_active_by(business_id=business.id)):
        return jsonify({'message': f'{identifier} active connection not found.'}), HTTPStatus.NOT_FOUND

    if digital_credentials.remove_connection_record(connection_id=connection.connection_id) is None:
        return jsonify({'message': 'Failed to remove connection record.'}), HTTPStatus.INTERNAL_SERVER_ERROR

    connection.delete()
    return jsonify({'message': 'Connection has been deleted.'}), HTTPStatus.OK


@bp.route('/<string:identifier>/digitalCredentials', methods=['GET', 'OPTIONS'], strict_slashes=False)
@cross_origin(origin='*')
@jwt.requires_auth
@can_access_digital_credentials
def get_issued_credentials(identifier):
    """Get all issued credentials."""
    if not (business := Business.find_by_identifier(identifier)):
        return jsonify({'message': f'{identifier} not found.'}), HTTPStatus.NOT_FOUND

    if not (connection := DCConnection.find_active_by(business_id=business.id)):
        return jsonify({'issuedCredentials': []}), HTTPStatus.OK

    if not (issued_credentials := DCCredential.find_by(connection_id=connection.id)):
        return jsonify({'issuedCredentials': []}), HTTPStatus.OK

    response = []
    for issued_credential in issued_credentials:
        definition = DCDefinition.find_by_id(issued_credential.definition_id)
        response.append({
            'legalName': business.legal_name,
            'credentialType': definition.credential_type.name,
            'credentialId': issued_credential.credential_id,
            'isIssued': issued_credential.is_issued,
            'dateOfIssue': issued_credential.date_of_issue.isoformat() if issued_credential.date_of_issue else '',
            'isRevoked': issued_credential.is_revoked
        })
    return jsonify({'issuedCredentials': response}), HTTPStatus.OK


@bp.route('/<string:identifier>/digitalCredentials/<string:credential_type>', methods=['POST'], strict_slashes=False)
@cross_origin(origin='*')
@jwt.requires_auth
@can_access_digital_credentials
def send_credential(identifier, credential_type):
    """Issue credentials to the connection."""
    if not (token := pyjwt.decode(jwt.get_token_auth_header(), options={'verify_signature': False})):
        return jsonify({'message': 'Unable to decode JWT'}, HTTPStatus.UNAUTHORIZED)

    if not (business := Business.find_by_identifier(identifier)):
        return jsonify({'message': f'{identifier} not found'}), HTTPStatus.NOT_FOUND

    if not (user := User.find_by_jwt_token(token)):
        return jsonify({'message': 'User not found'}, HTTPStatus.NOT_FOUND)

    connection = DCConnection.find_active_by(business_id=business.id)
    if not connection.last_attested:
        return jsonify({'message': 'Connection not attested.'}), HTTPStatus.UNAUTHORIZED
    elif not connection.is_attested:
        return jsonify({'message': 'Connection failed attestation.'}), HTTPStatus.UNAUTHORIZED

    definition = DCDefinition.find_by(DCDefinition.CredentialType[credential_type],
                                      digital_credentials.business_schema_id,
                                      digital_credentials.business_cred_def_id)

    issued_credentials = DCCredential.find_by(
        connection_id=connection.id, definition_id=definition.id)
    if issued_credentials and issued_credentials[0].credential_exchange_id:
        return jsonify({'message': 'Already requested to issue credential.'}), HTTPStatus.INTERNAL_SERVER_ERROR

    json_input = request.get_json()
    preconditions_met = json_input.get(
        'preconditionsMet', None) if json_input else None

    credential_data = get_digital_credential_data(
        user, business, definition.credential_type, preconditions_met)
    credential_id = next(
        (item['value'] for item in credential_data if item['name'] == 'credential_id'), None)

    if not (response := digital_credentials.issue_credential(
        connection_id=connection.connection_id,
        definition=definition,
        data=credential_data
    )):
        return jsonify({'message': 'Failed to issue credential.'}), HTTPStatus.INTERNAL_SERVER_ERROR

    issued_credential = DCCredential(
        definition_id=definition.id,
        connection_id=connection.id,
        credential_exchange_id=response['cred_ex_id'],
        credential_id=credential_id
    )
    issued_credential.save()

    return jsonify(issued_credential.json), HTTPStatus.OK


@bp.route('/<string:identifier>/digitalCredentials/<string:credential_id>/revoke',
          methods=['POST'], strict_slashes=False)
@cross_origin(origin='*')
@jwt.requires_auth
@can_access_digital_credentials
def revoke_credential(identifier, credential_id):
    """Revoke a credential."""
    if not (business := Business.find_by_identifier(identifier)):
        return jsonify({'message': f'{identifier} not found.'}), HTTPStatus.NOT_FOUND

    if not (connection := DCConnection.find_active_by(business_id=business.id)):
        return jsonify({'message': f'{identifier} active connection not found.'}), HTTPStatus.NOT_FOUND

    issued_credential = DCCredential.find_by_credential_id(
        credential_id=credential_id)
    if not issued_credential or issued_credential.is_revoked:
        return jsonify({'message': f'{identifier} issued credential not found.'}), HTTPStatus.NOT_FOUND

    reissue = request.get_json().get('reissue', False)
    reason = DCRevocationReason.SELF_REISSUANCE if reissue else DCRevocationReason.SELF_REVOCATION

    if digital_credentials.revoke_credential(connection.connection_id,
                                             issued_credential.credential_revocation_id,
                                             issued_credential.revocation_registry_id,
                                             reason) is None:
        return jsonify({'message': 'Failed to revoke credential.'}), HTTPStatus.INTERNAL_SERVER_ERROR

    issued_credential.is_revoked = True
    issued_credential.save()
    return jsonify({'message': 'Credential has been revoked.'}), HTTPStatus.OK


@bp.route('/<string:identifier>/digitalCredentials/<string:credential_id>', methods=['DELETE'], strict_slashes=False)
@cross_origin(origin='*')
@jwt.requires_auth
@can_access_digital_credentials
def delete_credential(identifier, credential_id):
    """Delete a credential."""
    if not Business.find_by_identifier(identifier):
        return jsonify({'message': f'{identifier} not found.'}), HTTPStatus.NOT_FOUND

    if not (issued_credential := DCCredential.find_by_credential_id(credential_id=credential_id)):
        return jsonify({'message': f'{identifier} issued credential not found.'}), HTTPStatus.NOT_FOUND

    if (digital_credentials.fetch_credential_exchange_record(issued_credential.credential_exchange_id) is not None and
            digital_credentials.remove_credential_exchange_record(issued_credential.credential_exchange_id) is None):
        return jsonify({'message': 'Failed to remove credential exchange record.'}), HTTPStatus.INTERNAL_SERVER_ERROR

    issued_credential.delete()
    return jsonify({'message': 'Credential has been deleted.'}), HTTPStatus.OK


@bp_dc.route('/topic/<string:topic_name>', methods=['POST'], strict_slashes=False)
@cross_origin(origin='*')
def webhook_notification(topic_name: str):
    """To receive notification from aca-py admin api."""
    json_input = request.get_json()
    state = json_input.get('state', None)
    try:
        # Using https://didcomm.org/connections/1.0 protocol the final state is 'active'
        # Using https://didcomm.org/didexchange/1.0 protocol the final state is 'completed'
        if topic_name == 'connections' and state in (
                DCConnection.State.ACTIVE.value, DCConnection.State.COMPLETED.value):
            if (connection := DCConnection.find_by_connection_id(
                    extract_invitation_message_id(json_input))):
                if not connection.is_active:
                    connection.connection_id = json_input['connection_id']
                    connection.connection_state = state
                    connection.is_active = True
                    connection.save()
        elif topic_name == 'issuer_cred_rev' and state == 'issued':
            cred_ex_id = json_input.get('cred_ex_id', None)
            if cred_ex_id and (issued_credential := DCCredential.find_by_credential_exchange_id(
                    cred_ex_id)):
                issued_credential.credential_revocation_id = json_input['cred_rev_id']
                issued_credential.revocation_registry_id = json_input['rev_reg_id']
                issued_credential.save()
        elif topic_name == 'issue_credential_v2_0' and state == 'done':
            cred_ex_id = json_input.get('cred_ex_id', None)
            if (issued_credential := DCCredential.find_by_credential_exchange_id(
                    cred_ex_id)):
                issued_credential.date_of_issue = datetime.utcnow()
                issued_credential.is_issued = True
                issued_credential.save()
        elif topic_name == 'present_proof_v2_0' and state == 'done':
            connection_id = json_input.get('connection_id', None)
            verified = json_input.get('verified', 'false') == 'true'
            if connection_id and (connection := DCConnection.find_by_connection_id(
                    connection_id)):
                connection.is_attested = verified
                connection.last_attested = datetime.utcnow()
                connection.save()
    except Exception as err:
        current_app.logger.error(err)
        raise err

    return jsonify({'message': 'Webhook received.'}), HTTPStatus.OK
