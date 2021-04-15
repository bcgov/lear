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
from http import HTTPStatus

from flask import current_app, jsonify, request
from flask_restx import Resource, cors

from colin_api.exceptions import GenericException
from colin_api.models import Business, Party
from colin_api.models.filing import DB
from colin_api.resources.business import API
from colin_api.utils.util import cors_preflight


@cors_preflight('GET')
@API.route('/<string:legal_type>/<string:identifier>/parties')
class PartiesInfo(Resource):
    """Meta information about the overall service."""

    @staticmethod
    @cors.crossdomain(origin='*')
    def get(legal_type: str, identifier: str):
        """Return the current directors for a business."""
        if not identifier:
            return jsonify({'message': 'Identifier required'}), HTTPStatus.NOT_FOUND

        try:
            if legal_type in Business.CORP_TYPE_CONVERSION[Business.LearBusinessTypes.BCOMP.value]:
                identifier = identifier[-7:]
            party_type = request.args.get('partyType', 'Director')
            cursor = DB.connection.cursor()
            directors = Party.get_current(cursor=cursor, corp_num=identifier, role_type=party_type)
            if not directors:
                return jsonify({'message': f'directors for {identifier} not found'}), HTTPStatus.NOT_FOUND
            if len(directors) < 3:
                current_app.logger.error('Less than 3 directors for {}'.format(identifier))
            return jsonify({'directors': [x.as_dict() for x in directors]}), HTTPStatus.OK

        except GenericException as err:  # pylint: disable=duplicate-code
            return jsonify(
                {'message': err.error}), err.status_code

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))
            return jsonify(
                {'message': 'Error when trying to retrieve directors from COLIN'}), HTTPStatus.INTERNAL_SERVER_ERROR
