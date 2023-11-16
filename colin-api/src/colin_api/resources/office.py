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

from flask import current_app, jsonify
from flask_restx import Resource, cors

from colin_api.exceptions import GenericException
from colin_api.models import Business, Office
from colin_api.models.filing import DB
from colin_api.resources.business import API
from colin_api.utils.auth import COLIN_SVC_ROLE, jwt
from colin_api.utils.util import conditional_auth, cors_preflight


@cors_preflight('GET')
@API.route('/<string:legal_type>/<string:identifier>/office')
class OfficeInfo(Resource):
    """Meta information about the overall service."""

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_roles([COLIN_SVC_ROLE])
    def get(legal_type: str, identifier: str):
        """Return the registered and/or records office for a corporation."""
        if not identifier:
            return jsonify({'message': 'Identifier required'}), HTTPStatus.NOT_FOUND

        try:
            if legal_type in Business.CORP_TYPE_CONVERSION[Business.LearBusinessTypes.BCOMP.value]:
                identifier = identifier[-7:]
            cursor = DB.connection.cursor()
            offices = {}
            office_obj_list = Office.get_current(cursor=cursor, identifier=identifier)
            for office_obj in office_obj_list:
                if office_obj.office_type not in offices.keys():
                    offices.update(office_obj.as_dict())
            if not offices.keys():
                return jsonify(
                    {'message': f'registered/records office for {identifier} not found'}
                ), HTTPStatus.NOT_FOUND
            return {**offices}, HTTPStatus.OK

        except GenericException as err:  # pylint: disable=duplicate-code
            return jsonify(
                {'message': err.error}), err.status_code

        except Exception as err:  # pylint: disable=broad-except; want to catch any exception here
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))
            return jsonify(
                {'message': 'Error when trying to retrieve registered office from COLIN'}
            ), HTTPStatus.INTERNAL_SERVER_ERROR
