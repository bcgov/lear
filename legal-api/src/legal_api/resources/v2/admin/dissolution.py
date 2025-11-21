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
"""API endpoints for managing Involuntary Dissolution resources."""
from http import HTTPStatus

from flask import jsonify
from flask_cors import cross_origin

from legal_api.models import UserRoles
from legal_api.services import InvoluntaryDissolutionService
from legal_api.utils.auth import jwt

from .bp import bp_admin


@bp_admin.route("/dissolutions/statistics", methods=["GET"])
@cross_origin(origin="*")
@jwt.has_one_of_roles([UserRoles.staff])
def get_statistics():
    """Return a JSON object with statistic information."""
    count = InvoluntaryDissolutionService.get_businesses_eligible_count()
    data = {
        "eligibleCount": count
    }

    return jsonify({
        "data": data
    }), HTTPStatus.OK
