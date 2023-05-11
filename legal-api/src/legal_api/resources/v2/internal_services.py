# Copyright © 2022 Province of British Columbia
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
"""Calls used by internal services."""
from http import HTTPStatus

from flask import Blueprint, current_app, g, jsonify, request
from flask_cors import cross_origin

from legal_api.models import Filing, LegalEntity, User, UserRoles
from legal_api.resources.v2.business.business_filings.business_filings import ListFilingResource
from legal_api.services import publish_event
from legal_api.utils.auth import jwt
from legal_api.utils.datetime import date, datetime


bp = Blueprint('INTERNAL_SERVICE', __name__, url_prefix='/api/v2/internal')


@bp.route('/bnmove', methods=['POST'])
@cross_origin(origin='*')
@jwt.has_one_of_roles([UserRoles.system])
def update_bn_move():
    """Update the new tax id for a business for given old tax id."""
    user = User.get_or_create_user_by_jwt(g.jwt_oidc_token_info)
    json_input = request.get_json()
    if not json_input or \
            not (old_bn := json_input.get('oldBn')) or not (new_bn := json_input.get('newBn')):
        return ({'message': 'No oldBn or newBn in body of post.'}, HTTPStatus.BAD_REQUEST)

    legal_entity = LegalEntity.find_by_tax_id(old_bn)
    if legal_entity:
        legal_entity.tax_id = new_bn
        legal_entity.save()

        response, response_code = create_registrars_notation_filing(legal_entity, user, old_bn)
        if response and (response_code != HTTPStatus.CREATED):
            current_app.logger.error('Unable to complete payment for registrars notation (bn move)')
            current_app.logger.error('%s, %s', response, response_code)

        publish_event(legal_entity,
                      'bc.registry.bnmove',
                      {'oldBn': old_bn, 'newBn': new_bn},
                      current_app.config.get('NATS_EMAILER_SUBJECT'))
        publish_event(legal_entity,
                      'bc.registry.business.bn',
                      {},
                      current_app.config.get('NATS_ENTITY_EVENT_SUBJECT'))
    else:
        current_app.logger.error('Unable to update tax_id for (%s), which is missing in lear', old_bn)
    return jsonify({'message': 'Successfully updated tax id.'}), HTTPStatus.OK


def create_registrars_notation_filing(legal_entity: LegalEntity, user: User, old_bn: str):
    """Create registrars notation filing while updating tax_id (BN Move)."""
    filing = Filing()
    filing.legal_entity_id = legal_entity.id
    filing.submitter_id = user.id
    filing.filing_json = {
        'filing': {
            'header': {
                'name': 'registrarsNotation',
                'date': date.today().isoformat(),
                'certifiedBy': 'system'
            },
            'business': {
                'identifier': legal_entity.identifier,
                'legalType': legal_entity.entity_type
            },
            'registrarsNotation': {
                'orderDetails': f'Business Number changed from {old_bn} to {legal_entity.tax_id }' +
                                ' based on a request from the CRA.'
            }
        }
    }
    filing.source = Filing.Source.LEAR.value
    filing.filing_date = datetime.utcnow()
    filing.effective_date = datetime.utcnow()
    filing.save()

    return ListFilingResource.complete_filing(legal_entity, filing, False, None)
