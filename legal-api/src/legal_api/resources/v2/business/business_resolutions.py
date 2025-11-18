# Copyright © 2020 Province of British Columbia
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
"""Retrieve the resolutions for the entity."""

from http import HTTPStatus

from flask import jsonify, request
from flask_cors import cross_origin

from legal_api.models import Business, Resolution
from legal_api.services import authorized
from legal_api.utils.auth import jwt

from .bp import bp


@bp.route("/<string:identifier>/resolutions", methods=["GET", "OPTIONS"])
@bp.route("/<string:identifier>/resolutions/<int:resolution_id>", methods=["GET", "OPTIONS"])
@cross_origin(origin="*")
@jwt.requires_auth
def get_resolutions(identifier, resolution_id=None):
    """Return a JSON of the resolutions."""
    business = Business.find_by_identifier(identifier)

    if not business:
        return jsonify({"message": f"{identifier} not found"}), HTTPStatus.NOT_FOUND

    # check authorization
    if not authorized(identifier, jwt, action=["view"]):
        return jsonify(
            {"message": f"You are not authorized to view resolutions for {identifier}."}
        ), HTTPStatus.UNAUTHORIZED

    # return the matching resolution
    if resolution_id:
        resolution, msg, code = _get_resolution(business, resolution_id)
        return jsonify(resolution or msg), code

    resolution_list = []

    resolution_type = request.args.get("type")
    if resolution_type:
        resolutions = Resolution.find_by_type(business.id, resolution_type.upper())
    else:
        resolutions = business.resolutions.all()

    for resolution in resolutions:
        resolution_json = resolution.json
        resolution_list.append(resolution_json)

    return jsonify(resolutions=resolution_list)


def _get_resolution(business, resolution_id=None):
    # find by ID
    resolution = None
    if resolution_id:
        rv = Resolution.find_by_id(resolution_id=resolution_id)
        if rv:
            resolution = {"resolution": rv.json}

    if not resolution:
        return None, {"message": f"{business.identifier} resolution not found"}, HTTPStatus.NOT_FOUND

    return resolution, None, HTTPStatus.OK
