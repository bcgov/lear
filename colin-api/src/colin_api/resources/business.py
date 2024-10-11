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
from flask_restx import Namespace, Resource, cors

from colin_api.exceptions import GenericException
from colin_api.models import Business, CorpName
from colin_api.resources.db import DB
from colin_api.utils.auth import COLIN_SVC_ROLE, jwt
from colin_api.utils.util import cors_preflight


API = Namespace('businesses', description='Colin API Services - Businesses')


@cors_preflight('GET')
@API.route('/<string:identifier>/public', methods=['GET', 'OPTIONS'])
class BusinessPublicInfo(Resource):
    """Meta information about the overall service."""

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_auth
    def get(identifier: str):
        """Return the complete business info."""
        try:
            # strip prefix BC
            if identifier.startswith('BC'):
                identifier = identifier[-7:]

            # get business
            business = Business.find_by_identifier(identifier)
            if not business:
                return jsonify({'message': f'{identifier} not found'}), HTTPStatus.NOT_FOUND
            return jsonify(business.as_slim_dict()), HTTPStatus.OK

        except GenericException as err:  # pylint: disable=duplicate-code
            return jsonify({'message': err.error}), err.status_code

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))
            return jsonify(
                {'message': 'Error when trying to retrieve business record from COLIN'}
            ), HTTPStatus.INTERNAL_SERVER_ERROR


@cors_preflight('GET, POST')
@API.route('/<string:legal_type>/<string:identifier>', methods=['GET'])
@API.route('/<string:legal_type>', methods=['POST'])
class BusinessInfo(Resource):
    """Meta information about the overall service."""

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_roles([COLIN_SVC_ROLE])
    def get(legal_type: str, identifier: str):
        """Return the complete business info."""
        try:
            # convert identifier if BC legal_type
            identifier = Business.get_colin_identifier(identifier, legal_type)

            # get business
            business = Business.find_by_identifier(identifier)
            if not business:
                return jsonify({'message': f'{identifier} not found'}), HTTPStatus.NOT_FOUND
            return jsonify(business.as_dict()), HTTPStatus.OK

        except GenericException as err:  # pylint: disable=duplicate-code
            return jsonify({'message': err.error}), err.status_code

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))
            return jsonify(
                {'message': 'Error when trying to retrieve business record from COLIN'}
            ), HTTPStatus.INTERNAL_SERVER_ERROR

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_roles([COLIN_SVC_ROLE])
    def post(legal_type: str):
        """Create and return a new corp number for the given legal type."""
        # BC: BEN, BC, ULC, CC
        # C: CBEN, C, CUL, CCC
        if legal_type not in ['BC', 'C']:  # corp_type (id_typ_cd in system_id table)
            return jsonify({'message': 'Must provide a valid legal type.'}), HTTPStatus.BAD_REQUEST

        try:
            con = DB.connection
            con.begin()
            corp_num = Business.get_next_corp_num(con=con, corp_type=legal_type)
            con.commit()
        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            current_app.logger.error(err.with_traceback(None))
            if con:
                con.rollback()

        if corp_num:
            return jsonify({'corpNum': corp_num}), HTTPStatus.OK

        return jsonify({'message': 'Failed to get new corp number'}), HTTPStatus.INTERNAL_SERVER_ERROR


@cors_preflight('GET')
@API.route('/<string:legal_type>/<string:identifier>/names/<string:name_type>', methods=['GET'])
class BusinessNamesInfo(Resource):
    """Meta information about business names."""

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_roles([COLIN_SVC_ROLE])
    def get(legal_type, identifier, name_type):
        """Get active names by type code for a business."""
        if legal_type not in [x.value for x in Business.TypeCodes]:
            return jsonify({'message': 'Must provide a valid legal type.'}), HTTPStatus.BAD_REQUEST

        if name_type not in [x.value for x in CorpName.TypeCodes.__members__.values()]:
            return jsonify({'message': 'Must provide a valid name type code.'}), HTTPStatus.BAD_REQUEST

        try:
            # convert identifier if BC legal_type
            identifier = Business.get_colin_identifier(identifier, legal_type)

            con = DB.connection
            con.begin()
            cursor = con.cursor()

            name_objs = CorpName.get_current_by_type(cursor=cursor, corp_num=identifier, type_code=name_type)
            return jsonify({'names': [x.as_dict() for x in name_objs]}), HTTPStatus.OK

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            current_app.logger.error(err.with_traceback(None))
            return jsonify({'message': 'Something went wrong.'}), HTTPStatus.INTERNAL_SERVER_ERROR


@cors_preflight('GET')
@API.route('/internal/<string:info_type>', methods=['GET'])
@API.route('/internal/<string:legal_type>/<string:identifier>/<string:info_type>', methods=['GET'])
@API.route('/internal/<string:legal_type>/<string:identifier>', methods=['PATCH'])
class InternalBusinessInfo(Resource):
    """Meta information used by internal services about businesses."""

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_roles([COLIN_SVC_ROLE])
    def get(info_type, legal_type=None, identifier=None):  # pylint: disable = too-many-return-statements;
        """Return specific business info for businesses."""
        try:
            con = DB.connection
            con.begin()
            cursor = con.cursor()

            if info_type == 'tax_ids':
                json_data = request.get_json()
                if not json_data or not json_data['identifiers']:
                    return jsonify({'message': 'No input data provided'}), HTTPStatus.BAD_REQUEST
                # remove the BC prefix
                identifiers = [x[-7:] if x.startswith('BC') else x
                               for x in json_data['identifiers']]
                bn_15s = Business._get_bn_15s(  # pylint: disable = protected-access; internal call
                    cursor=cursor,
                    identifiers=identifiers
                )
                return jsonify(bn_15s), HTTPStatus.OK

            if info_type == 'resolutions':
                if not legal_type or legal_type not in [x.value for x in Business.TypeCodes]:
                    return jsonify({'message': 'Must provide a valid legal type.'}), HTTPStatus.BAD_REQUEST

                if not identifier:
                    return jsonify(
                        {'message': f'Must provide a business identifier for {info_type}.'}
                    ), HTTPStatus.BAD_REQUEST

                # convert identifier if BC legal_type
                identifier = Business.get_colin_identifier(identifier, legal_type)

                return jsonify(
                    {'resolutionDates': Business.get_resolutions(cursor=cursor, corp_num=identifier)}
                ), HTTPStatus.OK

            return jsonify({'message': f'{info_type} not implemented.'}), HTTPStatus.NOT_IMPLEMENTED

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            current_app.logger.error(err.with_traceback(None))
            return jsonify({'message': 'Something went wrong.'}), HTTPStatus.INTERNAL_SERVER_ERROR

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_roles([COLIN_SVC_ROLE])
    def patch(legal_type, identifier):
        """Update the business corp state."""
        try:
            if legal_type not in [x.value for x in Business.TypeCodes]:
                return jsonify({'message': 'Must provide a valid legal type.'}), HTTPStatus.BAD_REQUEST

            json_data = request.get_json()
            if not json_data:
                return jsonify({'message': 'No input data provided'}), HTTPStatus.BAD_REQUEST

            json_data = json_data.get('batchProcessing', None)

            # ensure that the business in the batch processing matches the business in the URL
            if identifier != json_data['businessIdentifier']:
                return jsonify(
                    {'message': 'Error: Identifier in URL does not match identifier in batch processing'}
                ), HTTPStatus.BAD_REQUEST

            # convert identifier if BC legal_type
            identifier = Business.get_colin_identifier(identifier, legal_type)

            try:
                # get db connection and start a session, in case we need to roll back
                con = DB.connection
                con.begin()

                # create event and update corp state
                event_id = Business.add_involuntary_dissolution_warning_event(con, identifier, json_data)
                return jsonify({
                    'batchProcessing': {
                        'colinIds': [event_id]
                    }
                }), HTTPStatus.CREATED

            except Exception as db_err:
                current_app.logger.error('failed to file - rolling back partial db changes.')
                if con:
                    con.rollback()
                raise db_err

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))
            return jsonify(
                {'message': f'Error when trying to update corp state for business {identifier}'}
            ), HTTPStatus.INTERNAL_SERVER_ERROR
