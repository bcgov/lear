# Copyright © 2019 Province of British Columbia
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
"""Retrieve the directors for the entity."""
from datetime import datetime
from http import HTTPStatus

from flask import jsonify, request
from flask_restx import Resource, cors

from legal_api.models import Business, PartyRole
from legal_api.services import authorized
from legal_api.utils.auth import jwt
from legal_api.utils.util import cors_preflight

from .api_namespace import API


@cors_preflight("GET,")
@API.route("/<string:identifier>/directors", methods=["GET", "OPTIONS"])
@API.route("/<string:identifier>/directors/<int:director_id>", methods=["GET", "OPTIONS"])
class DirectorResource(Resource):
    """Business Directors service."""

    @staticmethod
    @cors.crossdomain(origin="*")
    @jwt.requires_auth
    def get(identifier, director_id=None):
        """Return a JSON of the directors."""
        business = Business.find_by_identifier(identifier)

        if not business:
            return jsonify({"message": f"{identifier} not found"}), HTTPStatus.NOT_FOUND

        # check authorization
        if not authorized(identifier, jwt, action=["view"]):
            return jsonify({"message":
                            f"You are not authorized to view directors for {identifier}."}), \
                HTTPStatus.UNAUTHORIZED

        # return the matching director
        if director_id:
            director, msg, code = DirectorResource._get_director(business, director_id)
            return jsonify(director or msg), code

        # return all active directors as of date query param
        end_date = datetime.utcnow().strptime(request.args.get("date"), "%Y-%m-%d").date()\
            if request.args.get("date") else datetime.utcnow().date()

        party_list = []
        active_directors = PartyRole.get_active_directors(business.id, end_date)
        for director in active_directors:
            director_json = director.json
            if business.legal_type == Business.LegalTypes.COOP.value:
                del director_json["mailingAddress"]
            party_list.append(director_json)

        return jsonify(directors=party_list)

    @staticmethod
    def _get_director(business, director_id=None):
        # find by ID
        director = None
        if director_id:
            rv = PartyRole.find_by_internal_id(internal_id=director_id)
            if rv:
                director = {"director": rv.json}

        if not director:
            return None, {"message": f"{business.identifier} director not found"}, HTTPStatus.NOT_FOUND

        return director, None, HTTPStatus.OK
