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
"""Meta information about the service.

Currently this only provides API versioning information
"""
from http import HTTPStatus

from flask import current_app, jsonify
from flask_restx import Resource, cors

from colin_api.exceptions import GenericException
from colin_api.models import Business, ShareObject
from colin_api.models.filing import DB
from colin_api.resources.business import API
from colin_api.utils.auth import COLIN_SVC_ROLE, jwt
from colin_api.utils.util import cors_preflight


@cors_preflight('GET')
@API.route('/<string:legal_type>/<string:identifier>/sharestructure')
class ShareStruct(Resource):
    """Meta information about the overall service."""

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_roles([COLIN_SVC_ROLE])
    def get(legal_type: str, identifier: str):
        """Return the current directors for a business."""
        if not identifier:
            return jsonify({'message': 'Identifier required'}), HTTPStatus.BAD_REQUEST

        try:

            cursor = DB.connection.cursor()
            identifier = Business.get_colin_identifier(identifier, legal_type)
            shares = ShareObject.get_all(cursor=cursor, corp_num=identifier)
            if not shares:
                return jsonify({'message': f'No share structures found for {identifier}'}), HTTPStatus.NOT_FOUND
            for share in shares:
                if not share.end_event_id:
                    return jsonify(share.to_dict())
            return jsonify({'message': f'No current share structures found for {identifier}'}), HTTPStatus.NOT_FOUND

        except GenericException as err:  # pylint: disable=duplicate-code
            return jsonify(
                {'message': err.error}), err.status_code

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))
            return jsonify(
                {'message': 'Error when trying to retrieve share structure from COLIN'}
            ), HTTPStatus.INTERNAL_SERVER_ERROR
