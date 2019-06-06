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
import datetime
from http import HTTPStatus

from flask import jsonify, request
from flask_restplus import Namespace, Resource, cors

from legal_api.exceptions import BusinessException
from legal_api.models import Business, Filing, db
from legal_api.utils.util import cors_preflight


API = Namespace('businesses', description='Legal API Services - Businesses')


@cors_preflight('GET')
@API.route('/<string:identifier>')
class BusinessResource(Resource):
    """Meta information about the overall service."""

    @staticmethod
    @cors.crossdomain(origin='*')
    def get(identifier):
        """Return a JSON object with meta information about the Service."""
        business = Business.find_by_identifier(identifier)

        if not business:
            return jsonify({'message': f'{identifier} not found'}), HTTPStatus.NOT_FOUND

        return jsonify(business=business.json())


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

            return jsonify(rv[1].filing_json)

        rv = []
        filings = business.filings.all()
        for filing in filings:
            rv.append(filing.json())

        return jsonify(filings=rv)

    @staticmethod
    @cors.crossdomain(origin='*')
    def post(identifier, filing_id=None):
        """Create a new filing for the business."""
        json_input = request.get_json()
        if not json_input:
            return jsonify({'message':
                            f'No filing json data in body of post for {identifier}.'}), \
                HTTPStatus.BAD_REQUEST

        business = Business.find_by_identifier(identifier)
        if not business:
            return jsonify({'message': f'{identifier} not found'}), HTTPStatus.NOT_FOUND

        if filing_id:  # checked since we're overlaying routes
            return jsonify({'message':
                            f'Illegal to attempt to create a new filing over an existing filing for {identifier}.'}), \
                HTTPStatus.FORBIDDEN

        try:
            filing = Filing()
            filing.business_id = business.id
            filing.filing_date = datetime.datetime.utcnow()
            filing.filing_json = json_input
            filing.save()
        except BusinessException as err:
            return jsonify({'message': err.error}), err.status_code

        return jsonify(filing.filing_json), HTTPStatus.CREATED

    @staticmethod
    @cors.crossdomain(origin='*')
    def put(identifier, filing_id):
        """Create a new filing for the business."""
        json_input = request.get_json()
        if not json_input:
            return jsonify({'message':
                            f'No filing json data in body of post for {identifier}.'}), \
                HTTPStatus.BAD_REQUEST

        business = Business.find_by_identifier(identifier)
        if not business:
            return jsonify({'message': f'{identifier} not found'}), HTTPStatus.NOT_FOUND

        rv = db.session.query(Business, Filing). \
            filter(Business.id == Filing.business_id).\
            filter(Business.identifier == identifier).\
            filter(Filing.id == filing_id).\
            one_or_none()
        if not rv:
            return jsonify({'message': f'{identifier} no filings found'}), HTTPStatus.NOT_FOUND

        try:
            filing = rv[1]
            filing.filing_date = datetime.datetime.utcnow()
            filing.filing_json = json_input
            filing.save()
        except BusinessException as err:
            return jsonify({'message': err.error}), err.status_code

        return jsonify(filing.filing_json), HTTPStatus.ACCEPTED
