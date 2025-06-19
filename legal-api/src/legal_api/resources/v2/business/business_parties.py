# Copyright © 2021 Province of British Columbia
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
"""Retrieve the parties for the entity."""
from datetime import datetime, timezone
from http import HTTPStatus

from flask import jsonify, request
from flask_cors import cross_origin

from legal_api.models import Business, PartyRole, PartyClass
from legal_api.services import authorized
from legal_api.utils.auth import jwt

from .bp import bp


@bp.route('/<string:identifier>/parties', methods=['GET', 'OPTIONS'])
@bp.route('/<string:identifier>/parties/<int:party_id>', methods=['GET', 'OPTIONS'])
@cross_origin(origin='*')
@jwt.requires_auth
def get_parties(identifier, party_id=None):
    """Return a JSON of the parties."""
    business = Business.find_by_identifier(identifier)

    if not business:
        return jsonify({'message': f'{identifier} not found'}), HTTPStatus.NOT_FOUND

    # check authorization
    if not authorized(identifier, jwt, action=['view']):
        return jsonify({'message':
                        f'You are not authorized to view parties for {identifier}.'}), \
            HTTPStatus.UNAUTHORIZED

    if party_id:
        party_roles = PartyRole.get_party_roles_by_party_id(business.id, party_id)
        if not party_roles:
            return jsonify({'message': f'Party {party_id} not found'}), HTTPStatus.NOT_FOUND
    else:
        end_date = datetime.strptime(request.args.get('date'), '%Y-%m-%d').date() \
            if request.args.get('date') else datetime.now(timezone.utc).date()
        if str(request.args.get('all', None)).lower() == 'true':
            end_date = None

        class_type_str = request.args.get('classType')
        if class_type_str:
            try:
                class_type_enum = PartyClass.PartyClassType[class_type_str.upper()]
            except KeyError:
                valid_types = [e.name for e in PartyClass.PartyClassType]
                return jsonify({"message": f"Invalid classType '{class_type_str}'. Valid types: {valid_types}"}), HTTPStatus.BAD_REQUEST

            party_roles = PartyRole.get_party_roles_by_class_type(
                business.id,
                class_type_enum,
                end_date
            )
        else:
            party_roles = PartyRole.get_party_roles(business.id, end_date, request.args.get('role'))

    party_role_dict = {}
    party_list = []
    for party_role in party_roles:
        party_role_json = party_role.json
        party_role_dict.setdefault(party_role.party_id, []).append(
            {'roleType': party_role_json['role'].replace('_', ' ').title(),
             'appointmentDate': party_role_json['appointmentDate'],
             'cessationDate': party_role_json['cessationDate']})
    for key, value in party_role_dict.items():
        party = [x for x in party_roles if x.party_id == key][0]
        party_json = party.json
        del party_json['role']
        del party_json['appointmentDate']
        del party_json['cessationDate']
        party_json['roles'] = value
        party_list.append(party_json)

    if party_id:
        return {'party': party_list[0]}
    else:
        return jsonify(parties=party_list)
