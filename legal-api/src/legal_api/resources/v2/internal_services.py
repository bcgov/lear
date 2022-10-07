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

from flask import Blueprint, current_app, jsonify, request
from flask_cors import cross_origin

from legal_api.models import Business, UserRoles
from legal_api.services import publish_event
from legal_api.utils.auth import jwt


bp = Blueprint('INTERNAL_SERVICE', __name__, url_prefix='/api/v2/internal')


@bp.route('/bnmove', methods=['POST'])
@cross_origin(origin='*')
@jwt.has_one_of_roles([UserRoles.system])
def update_bn_move():
    """Update the new tax id for a business for given old tax id."""
    json_input = request.get_json()
    if not json_input or \
            not (old_bn := json_input.get('oldBn')) or not (new_bn := json_input.get('newBn')):
        return ({'message': 'No oldBn or newBn in body of post.'}, HTTPStatus.BAD_REQUEST)

    business = Business.find_by_tax_id(old_bn)
    if business:
        business.tax_id = new_bn
        business.save()
        publish_event(business,
                      'bc.registry.bnmove',
                      {'oldBn': old_bn, 'newBn': new_bn},
                      current_app.config.get('NATS_EMAILER_SUBJECT'))
        publish_event(business,
                      'bc.registry.business.bn',
                      {},
                      current_app.config.get('NATS_ENTITY_EVENT_SUBJECT'))
    else:
        current_app.logger.error('Unable to update tax_id for (%s), which is missing in lear', old_bn)
    return jsonify({'message': 'Successfully updated tax id.'}), HTTPStatus.OK
