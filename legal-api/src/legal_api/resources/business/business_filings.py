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
"""Searching on a business entity.

Provides all the search and retrieval from the business entity datastore.
"""
import datetime
from http import HTTPStatus
from typing import Tuple

from flask import g, jsonify, request
from flask_restplus import Resource, cors

from legal_api.exceptions import BusinessException
from legal_api.models import Business, Filing, User, db
from legal_api.services.authz import authorized
from legal_api.utils.auth import jwt
from legal_api.utils.util import cors_preflight

from .api_namespace import API


@cors_preflight('GET, POST, PUT, DELETE')
@API.route('/<string:identifier>/filings', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
@API.route('/<string:identifier>/filings/<int:filing_id>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
class ListFilingResource(Resource):
    """Meta information about the overall service."""

    @staticmethod
    @cors.crossdomain(origin='*')
    def get(identifier, filing_id=None):
        """Return a JSON object with meta information about the Service."""
        business = Business.find_by_identifier(identifier)

        if not business:
            return jsonify({'message': f'{identifier} not found'}), HTTPStatus.NOT_FOUND

        if filing_id:
            rv = db.session.query(Business, Filing). \
                filter(Business.id == Filing.business_id).\
                filter(Business.identifier == identifier).\
                filter(Filing.id == filing_id).\
                one_or_none()
            if not rv:
                return jsonify({'message': f'{identifier} no filings found'}), HTTPStatus.NOT_FOUND

            return jsonify(rv[1].json())

        rv = []
        filings = business.filings.all()
        for filing in filings:
            rv.append(filing.json())

        return jsonify(filings=rv)

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_auth
    def post(identifier, filing_id=None):
        """Create a new filing for the business."""
        return ListFilingResource.put(identifier, filing_id)

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_auth
    def put(identifier, filing_id):
        """Create a new filing for the business."""
        error = ListFilingResource._basic_checks(identifier, filing_id, request)
        if error:
            return jsonify(error[0]), error[1]

        json_input = request.get_json()

        if not authorized(identifier, jwt):
            return jsonify({'message':
                            f'You are not authorized to submit a filing for {identifier}.'}), \
                HTTPStatus.UNAUTHORIZED
        user = User.get_or_create_user_by_jwt(g.jwt_oidc_token_info)

        business = Business.find_by_identifier(identifier)
        if not business:
            return jsonify({'message': f'{identifier} not found'}), HTTPStatus.NOT_FOUND

        if request.method == 'PUT':
            rv = db.session.query(Business, Filing). \
                filter(Business.id == Filing.business_id).\
                filter(Business.identifier == identifier).\
                filter(Filing.id == filing_id).\
                one_or_none()
            if not rv:
                return jsonify({'message': f'{identifier} no filings found'}), HTTPStatus.NOT_FOUND
            filing = rv[1]
        else:
            filing = Filing()
            filing.business_id = business.id

        try:
            filing.submitter_id = user.id
            filing.filing_date = datetime.datetime.utcnow()
            filing.filing_json = json_input
            filing.save()
        except BusinessException as err:
            return jsonify({'message': err.error}), err.status_code

        return jsonify(filing.json()), \
            (HTTPStatus.CREATED if (request.method == 'POST') else HTTPStatus.ACCEPTED)

    @staticmethod
    def _basic_checks(identifier, filing_id, client_request) -> Tuple[dict, int]:
        json_input = client_request.get_json()
        if not json_input:
            return ({'message':
                     f'No filing json data in body of post for {identifier}.'},
                    HTTPStatus.BAD_REQUEST)

        if filing_id and client_request.method != 'PUT':  # checked since we're overlaying routes
            return ({'message':
                     f'Illegal to attempt to create a new filing over an existing filing for {identifier}.'},
                    HTTPStatus.FORBIDDEN)

        return None
