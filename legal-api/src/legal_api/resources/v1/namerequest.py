# Copyright © 2020 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Searching on a namerequest.

Provides a proxy endpoint to retrieve name request data.
"""

from flask import abort, current_app, jsonify, make_response
from flask_restx import Namespace, Resource, cors

from legal_api.services import namex
from legal_api.utils.util import cors_preflight


API = Namespace("NameRequest", description="NameRequest")


@cors_preflight("GET")
@API.route("/<string:identifier>", methods=["GET", "OPTIONS"])
class NameRequest(Resource):
    """Proxied name request to namex-api."""

    @staticmethod
    @cors.crossdomain(origin="*")
    def get(identifier):
        """Return a JSON object with name request information."""
        try:
            nr_response = namex.query_nr_number(identifier)
            # Errors in general will just pass though,
            # 404 is overriden as it is giving namex-api specific messaging
            if nr_response.status_code == 404:
                return make_response(jsonify(message="{} not found.".format(identifier)), 404)

            return jsonify(nr_response.json())
        except Exception as err:
            current_app.logger.error(err)
            abort(500)
            return {}, 500  # to appease the linter
