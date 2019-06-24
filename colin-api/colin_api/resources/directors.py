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
"""Meta information about the service.

Currently this only provides API versioning information
"""
from flask import current_app, jsonify
from flask_restplus import Resource, cors

from colin_api.exceptions import GenericException
from colin_api.models import Director
from colin_api.resources.business import API
from colin_api.utils.util import cors_preflight


@cors_preflight('GET')
@API.route('/<string:identifier>/directors')
class DirectorsInfo(Resource):
    """Meta information about the overall service."""

    @staticmethod
    @cors.crossdomain(origin='*')
    def get(identifier):
        """Return the complete business info."""
        if not identifier:
            return jsonify({'message': 'Identifier required'}), 404

        try:
            directors = Director.get_current(identifier)
            if not directors:
                return jsonify({'message': f'directors for {identifier} not found'}), 404
            if len(directors) < 3:
                current_app.logger.error('Less than 3 directors for {}'.format(identifier))
            return jsonify({'directors': [x.as_dict() for x in directors]})

        except GenericException as err:  # pylint: disable=duplicate-code
            return jsonify(
                {'message': err.error}), err.status_code

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))
            return jsonify(
                {'message': 'Error when trying to retrieve directors from COLIN'}), 500
