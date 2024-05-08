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

from flask import Blueprint, jsonify
from flask_cors import cross_origin

from legal_api.models import Configuration, UserRoles
from legal_api.utils.auth import jwt


bp = Blueprint('CONFIGURARION', __name__, url_prefix='/api/v2/admin/configuration')


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
