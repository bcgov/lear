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

from legal_api.models import Configuration, UserRoles, db
from legal_api.services.utils import get_duplicate_keys
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

    duplicated_keys = get_duplicate_keys(data_list=configurations, key_attr='name')
    if len(duplicated_keys) > 0:
        duplicated_keys_str = ', '.join(duplicated_keys)
        return {'message': f'{duplicated_keys_str} are duplicated.'}, HTTPStatus.BAD_REQUEST

    numeric_names = {'NUM_DISSOLUTIONS_ALLOWED', 'MAX_DISSOLUTIONS_ALLOWED'}
    response = []

    try:
        for config_data in configurations:
            name = config_data.get('name')
            value = config_data.get('value')

            if name in numeric_names:
                if not is_valid_numeric_value(name, value):
                    raise ValueError(f'Invalid value for {name}.')

            config = Configuration.find_by_name(name)
            if not config:
                raise ValueError(f'{name} is an invalid key.')

            config.val = str(value)
            db.session.add(config)
            response.append(config.json)
        db.session.commit()
    except ValueError as e:
        # Rollback transaction
        db.session.rollback()
        return {'message': str(e)}, HTTPStatus.BAD_REQUEST

    return {'configurations': response}, HTTPStatus.OK


def is_valid_numeric_value(name, value):
    """Check if the numeric value is valid."""
    if name == 'NUM_DISSOLUTIONS_ALLOWED':
        max_value = Configuration.find_by_name('MAX_DISSOLUTIONS_ALLOWED').val
        return int(value) <= int(max_value)
    elif name == 'MAX_DISSOLUTIONS_ALLOWED':
        min_value = Configuration.find_by_name('NUM_DISSOLUTIONS_ALLOWED').val
        return int(value) >= int(min_value)
    return False
