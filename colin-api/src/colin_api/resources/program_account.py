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
"""Program account details from BNIT link."""
from http import HTTPStatus

from flask import current_app, jsonify, request
from flask_restx import Namespace, Resource, cors

from colin_api.exceptions import GenericException
from colin_api.models import ProgramAccount
from colin_api.utils.auth import COLIN_SVC_ROLE, jwt
from colin_api.utils.util import cors_preflight


API = Namespace('ProgramAccount', description='ProgramAccount endpoint to get BNI DB link data.')


@cors_preflight('POST')
@API.route('/check-bn15s')
class ProgramAccountList(Resource):
    """Program Account List."""

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_roles([COLIN_SVC_ROLE])
    def post():
        """Check for program accounts."""
        json_input = request.get_json()
        identifiers = json_input.get('identifiers')
        if not identifiers:
            return jsonify({'message': 'Identifiers required'}), HTTPStatus.BAD_REQUEST

        try:
            bn15s = ProgramAccount.get_bn15s(identifiers=identifiers)
            return jsonify({'bn15s': bn15s}), HTTPStatus.OK

        except Exception as err:  # pylint: disable=broad-except; want to catch any exception here
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))
            return jsonify(
                {'message': 'Error when trying to check program accounts from COLIN'}
            ), HTTPStatus.INTERNAL_SERVER_ERROR


@cors_preflight('GET')
@API.route('/<string:identifier>')
@API.route('/<string:identifier>/<string:transaction_id>')
class ProgramAccountInfo(Resource):
    """Program Account information about."""

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_roles([COLIN_SVC_ROLE])
    def get(identifier: str, transaction_id: str = None):
        """Return the BNI DB link program account."""
        if not identifier:
            return jsonify({'message': 'Identifier required'}), HTTPStatus.NOT_FOUND

        try:
            program_account = ProgramAccount.get_program_account(transaction_id=transaction_id,
                                                                 cross_reference_program_no=identifier)
            if not program_account:
                return jsonify(
                    {'message': f'Program Account for {identifier}, {transaction_id} not found'}
                ), HTTPStatus.NOT_FOUND
            return program_account.as_dict(), HTTPStatus.OK

        except GenericException as err:  # pylint: disable=duplicate-code
            return jsonify(
                {'message': err.error}), err.status_code

        except Exception as err:  # pylint: disable=broad-except; want to catch any exception here
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))
            return jsonify(
                {'message': 'Error when trying to retrieve program account from COLIN'}
            ), HTTPStatus.INTERNAL_SERVER_ERROR
