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

from legal_api.models import Business, Filing, User, UserRoles
from legal_api.resources.v2.business.business_filings.business_filings import ListFilingResource
from legal_api.services.event_publisher import publish_to_queue
from legal_api.utils.auth import jwt
from legal_api.utils.datetime import date, datetime


bp = Blueprint('INTERNAL_SERVICE', __name__, url_prefix='/api/v2/internal')


@bp.route('/filings/future_effective', methods=['GET'])
@cross_origin(origin='*')
@jwt.has_one_of_roles([UserRoles.system])
def get_future_effective_filing_ids():
    """Return filing ids which should be effective now."""
    filing_ids = Filing.get_future_effective_filing_ids()
    return jsonify(filing_ids), HTTPStatus.OK


@bp.route('/expired_restoration', methods=['GET'])
@cross_origin(origin='*')
@jwt.has_one_of_roles([UserRoles.system])
def get_identifiers_of_expired_restoration():
    """Return all identifiers (if limited restoration has expired)."""
    businesses = Business.get_expired_restoration()
    return jsonify({'businesses': [{'identifier': business.identifier,
                                    'legalType': business.legal_type} for business in businesses]}), HTTPStatus.OK


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

    business = Business.find_by_tax_id(old_bn)
    if business:
        business.tax_id = new_bn
        business.save()

        response, response_code = create_registrars_notation_filing(business, user, old_bn)
        if response and (response_code != HTTPStatus.CREATED):
            current_app.logger.error('Unable to complete payment for registrars notation (bn move)')
            current_app.logger.error('%s, %s', response, response_code)
        publish_to_queue(
            data={'oldBn': old_bn, 'newBn': new_bn},
            subject=current_app.config.get('NATS_EMAILER_SUBJECT'),
            event_type='bc.registry.bnmove',
            identifier=business.identifier if business else None,
            message_id=None,
            is_wrapped=True
        )
        publish_to_queue(
            data={},
            subject=current_app.config.get('NATS_ENTITY_EVENT_SUBJECT'),
            event_type='bc.registry.business.bn',
            identifier=business.identifier if business else None,
            message_id=None,
            is_wrapped=True
        )
    else:
        current_app.logger.error('Unable to update tax_id for (%s), which is missing in lear', old_bn)
    return jsonify({'message': 'Successfully updated tax id.'}), HTTPStatus.OK


def create_registrars_notation_filing(business: Business, user: User, old_bn: str):
    """Create registrars notation filing while updating tax_id (BN Move)."""
    filing = Filing()
    filing.business_id = business.id
    filing.submitter_id = user.id
    filing.filing_json = {
        'filing': {
            'header': {
                'name': 'registrarsNotation',
                'date': date.today().isoformat(),
                'certifiedBy': 'system'
            },
            'business': {
                'identifier': business.identifier,
                'legalType': business.legal_type
            },
            'registrarsNotation': {
                'orderDetails': f'Business Number changed from {old_bn} to {business.tax_id}' +
                                ' based on a request from the CRA.'
            }
        }
    }
    filing.source = Filing.Source.LEAR.value
    filing.filing_date = datetime.utcnow()
    filing.effective_date = datetime.utcnow()
    filing.save()

    return ListFilingResource.complete_filing(business, filing, False, None)
