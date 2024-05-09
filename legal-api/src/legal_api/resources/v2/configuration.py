# Copyright © 2024 Province of British Columbia
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
"""API endpoints for managing Configuration resource."""
from http import HTTPStatus

from flask import Blueprint, jsonify, request
from flask_cors import cross_origin

from legal_api.models import Configuration, UserRoles
from legal_api.utils.auth import jwt


bp = Blueprint('CONFIGURATION', __name__, url_prefix='/api/v2/admin/configurations')


@bp.route('', methods=['GET'])
@cross_origin(origin='*')
@jwt.has_one_of_roles([UserRoles.staff])
def get_configurations():
    """Return a list of configurations."""
    configurations = Configuration.all()
    return jsonify({
        'configurations': [
            configuration.json for configuration in configurations
        ]
    }), HTTPStatus.OK


@bp.route('', methods=['POST'])
@cross_origin(origin='*')
# @jwt.has_one_of_roles([UserRoles.staff])
def save_configurations():
    configuration = Configuration()
    configuration.name = 'NUM_DISSOLUTIONS_ALLOWED'
    configuration.val = '100'
    configuration.save()

    return configuration, HTTPStatus.CREATED


@bp.route('', methods=['PUT'])
@cross_origin(origin='*')
# @jwt.has_one_of_roles([UserRoles.staff])
def update_configurations():
    """Update the configurations."""
    json_input = request.get_json()

    if not json_input:
        return ({'message': 'Request body cannot be blank'}), HTTPStatus.BAD_REQUEST

    configurations = json_input['configurations']

    valid, msg = has_validate_names(configurations)
    if not valid:
        return ({'message': msg}), HTTPStatus.BAD_REQUEST

    for data in configurations:
        if data.get('name', None):
            configuration = Configuration.find_by_name(data['name'])
            configuration.val = int(data.get('value', configuration.val))
            if not is_validate_max_num_value(data, configuration):
                return ({
                    'message': 'NUM_DISSOLUTIONS_ALLOWED must be less than MAX_DISSOLUTIONS_ALLOWED.'
                    }), HTTPStatus.BAD_REQUEST
            try:
                configuration.save()
            except ValueError as error:
                return ({'message': error}, HTTPStatus.BAD_REQUEST)

    return HTTPStatus.OK


def is_validate_max_num_value(input_data, configuration):
    """Check NUM_DISSOLUTIONS_ALLOWED, MAX_DISSOLUTIONS_ALLOWED."""
    num_dissolutions_allowed = input_data['value'] if input_data['name'] == 'NUM_DISSOLUTIONS_ALLOWED'\
        else configuration.val
    max_dissolutions_allowed = input_data['value'] if input_data['name'] == 'MAX_DISSOLUTIONS_ALLOWED'\
        else configuration.val
    return bool(int(num_dissolutions_allowed) <= int(max_dissolutions_allowed))


def has_validate_names(input_data):
    """Check if the names are valid and not duplicated."""
    valid_names = {'NUM_DISSOLUTIONS_ALLOWED', 'MAX_DISSOLUTIONS_ALLOWED', 'DISSOLUTIONS_ON_HOLD', 'NEW_DISSOLUTIONS_SCHEDULE'}
    name_count = {name: 0 for name in valid_names}

    for data in input_data:
        name = data.get('name')
        if name not in valid_names:
            return False, f'{name} is an invalid name'
        if name_count[name] == 1:
            return False, f'{name} is duplicated'
        else:
            name_count[name] += 1
    
    return True, None
