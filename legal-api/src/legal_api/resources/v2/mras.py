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
"""API endpoints for managing MRAS resource."""
from http import HTTPStatus

from flask import Blueprint, jsonify
from flask_cors import cross_origin

from legal_api.models import UserRoles
from legal_api.services import MrasService
from legal_api.utils.auth import jwt


bp = Blueprint('MRAS2', __name__, url_prefix='/api/v2/mras')


@bp.route('/<string:identifier>', methods=['GET'])
@cross_origin(origins='*')
@jwt.has_one_of_roles([UserRoles.system])
def get_jurisdicions(identifier: str):
    """Return a list of foreign jurisdicions."""
    jurisdictions = MrasService.get_jurisdictions(identifier)

    if jurisdictions is None:
        return jsonify(
            message=f'Error getting foreign jurisdiction information for {identifier}.'
        ), HTTPStatus.INTERNAL_SERVER_ERROR

    return jsonify({
        'jurisdictions': jurisdictions
    }), HTTPStatus.OK
