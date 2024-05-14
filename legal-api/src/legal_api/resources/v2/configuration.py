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
from sqlalchemy import any_

from legal_api.models import Configuration, UserRoles, db
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
    error_message = validate_configurations(configurations)
    if error_message:
        return {'message': error_message}, HTTPStatus.BAD_REQUEST

    response = []
    try:
        for config_data in configurations:
            name = config_data.get('name')
            value = config_data.get('value')
            config = Configuration.find_by_name(name)
            config.val = str(value)
            db.session.add(config)
            response.append(config.json)
        db.session.commit()
    except ValueError as e:
        # Rollback transaction
        db.session.rollback()
        return {'message': str(e)}, HTTPStatus.BAD_REQUEST

    return {'configurations': response}, HTTPStatus.OK


def validate_configurations(configurations):
    """Validate the configurations before updating."""
    if not configurations:
        return 'Configurations list cannot be empty'

    # Extract names from the requested configuration updates
    names = [config['name'] for config in configurations]
    if len(names) != len(set(names)):
        return 'Duplicate names error.'

    if err := validate_invalid_names(names):
        return err

    if err := validate_data_types(configurations):
        return err

    if err := validate_dissolutions_config(configurations):
        return err

    return None  # No errors found


def validate_data_types(configurations):
    """Validate the data types of the configurations."""
    try:
        for config in configurations:
            name = config.get('name')
            value = config.get('value')
            Configuration.validate_configuration_value(name, value)
    except ValueError as e:
        return str(e)

    return None


def validate_invalid_names(names):
    """Validate if there are any invalid names in configurations to be updated."""
    # Query the database for these names
    existing_configs = Configuration.query.filter(Configuration.name.ilike(any_(names))).all()

    # Check if the number of unique names in the request matches the number of names found in the database
    if len(existing_configs) != len(set(names)):
        return 'Invalid name error.'

    return None


def validate_dissolutions_config(configurations):
    """Validate the dissolutions configuration."""
    num_dissolutions_match = find_config_by_name(configurations, 'NUM_DISSOLUTIONS_ALLOWED')
    max_dissolutions_match = find_config_by_name(configurations, 'MAX_DISSOLUTIONS_ALLOWED')

    # don't need to validate
    if not num_dissolutions_match and not max_dissolutions_match:
        return None

    if num_dissolutions_match:
        num_dissolutions_allowed = int(num_dissolutions_match.get('value'))
    else:
        num_dissolutions_allowed = Configuration.find_by_name('NUM_DISSOLUTIONS_ALLOWED').val
    num_dissolutions_allowed = int(num_dissolutions_allowed)

    if max_dissolutions_match:
        max_dissolutions_allowed = int(max_dissolutions_match.get('value'))
    else:
        max_dissolutions_allowed = Configuration.find_by_name('MAX_DISSOLUTIONS_ALLOWED').val
    max_dissolutions_allowed = int(max_dissolutions_allowed)

    if num_dissolutions_allowed > max_dissolutions_allowed:
        return 'NUM_DISSOLUTIONS_ALLOWED is greater than MAX_DISSOLUTIONS_ALLOWED.'

    return None


def find_config_by_name(configurations, name):
    """Search for a specific configuration by name from configuration payload."""
    return next((config for config in configurations if config['name'] == name), None)
