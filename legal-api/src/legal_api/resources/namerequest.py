# Copyright © 2019 Province of British Columbia
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

import requests
from flask import abort, current_app, jsonify, make_response
from flask_restplus import Namespace, Resource, cors

from legal_api.utils.util import cors_preflight


API = Namespace('NameRequest', description='NameRequest')


@cors_preflight('GET')
@API.route('/<string:identifier>', methods=['GET', 'OPTIONS'])
class NameRequest(Resource):
    """Proxied name request to namex-api."""

    @staticmethod
    @cors.crossdomain(origin='*')
    def get(identifier):
        """Return a JSON object with name request information."""
        try:
            auth_url = current_app.config.get('NAMEX_AUTH_SVC_URL')
            username = current_app.config.get('NAMEX_SERVICE_CLIENT_USERNAME')
            secret = current_app.config.get('NAMEX_SERVICE_CLIENT_SECRET')
            namex_url = current_app.config.get('NAMEX_SVC_URL')

            # Get access token for namex-api in a different keycloak realm
            auth = requests.post(auth_url, auth=(username, secret), headers={
                'Content-Type': 'application/x-www-form-urlencoded'}, data={'grant_type': 'client_credentials'})

            # Return the auth response if an error occurs
            if auth.status_code != 200:
                return jsonify(auth.json())

            token = dict(auth.json())['access_token']

            # Perform proxy call using the inputted identifier (e.g. NR 1234567)
            nr_response = requests.get(namex_url + 'requests/' + identifier, headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
                })

            # Errors in general will just pass though,
            # 404 is overriden as it is giving namex-api specific messaging
            if nr_response.status_code == 404:
                abort(make_response(jsonify(message='{} not found.'.format(identifier)), 404))

            return jsonify(nr_response.json())
        except Exception as err:
            current_app.logger.error(err)
            abort(500)
