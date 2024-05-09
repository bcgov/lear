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


@bp.route('', methods=['PUT'])
@cross_origin(origin='*')
@jwt.has_one_of_roles([UserRoles.staff])
def update_configurations():
    """Update the configurations."""
    json_input = request.get_json()
    if not json_input:
        return {'message': 'Request body cannot be blank'}, HTTPStatus.BAD_REQUEST

    configurations = json_input.get('configurations', [])
    if not configurations:
        return {'message': 'Configurations list cannot be empty'}, HTTPStatus.BAD_REQUEST

    valid_names, msg = has_validate_names(configurations)
    if not valid_names:
        return ({'message': msg}), HTTPStatus.BAD_REQUEST

    numeric_names = {'NUM_DISSOLUTIONS_ALLOWED', 'MAX_DISSOLUTIONS_ALLOWED'}

    for config_data in configurations:
        name = config_data.get('name')
        value = config_data.get('value')

        if name in numeric_names:
            if not is_valid_numeric_value(name, value):
                return {'message': f'Invalid value for {name}.'}, HTTPStatus.BAD_REQUEST

        config = Configuration.find_by_name(name)
        config.val = str(value)
        try:
            config.save()
        except ValueError as e:
            return {'message': str(e)}, HTTPStatus.BAD_REQUEST

    return {'message': 'Configurations updated successfully'}, HTTPStatus.OK


def is_valid_numeric_value(name, value):
    """Check if the numeric value is valid."""
    if name == 'NUM_DISSOLUTIONS_ALLOWED':
        max_value = Configuration.find_by_name('MAX_DISSOLUTIONS_ALLOWED').val
        return int(value) <= int(max_value)
    elif name == 'MAX_DISSOLUTIONS_ALLOWED':
        min_value = Configuration.find_by_name('NUM_DISSOLUTIONS_ALLOWED').val
        return int(value) >= int(min_value)
    return False


def has_validate_names(input_data):
    """Check if the names are valid and not duplicated."""
    valid_names = {'NUM_DISSOLUTIONS_ALLOWED', 'MAX_DISSOLUTIONS_ALLOWED',
                   'DISSOLUTIONS_ON_HOLD', 'NEW_DISSOLUTIONS_SCHEDULE'}
    name_count = {name: 0 for name in valid_names}

    for data in input_data:
        name = data.get('name')
        if name not in valid_names:
            return False, f'{name} is an invalid key.'
        if name_count[name] == 1:
            return False, f'{name} is duplicated.'
        else:
            name_count[name] += 1

    return True, None
