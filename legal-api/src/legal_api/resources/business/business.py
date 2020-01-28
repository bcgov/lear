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
from http import HTTPStatus

from flask import jsonify, request
from flask_restplus import Resource, cors

from legal_api.models import Business, Filing
from legal_api.utils.util import cors_preflight
from legal_api.services.filings import validate

from .api_namespace import API


@cors_preflight('GET, POST, PUT')
@API.route('/<string:identifier>', methods=['GET', 'OPTIONS'])
@API.route('/<string:identifier>', methods=['PUT'])
@API.route('', methods=['POST'])
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

    @staticmethod
    @cors.crossdomain(origin='*')
    def post():
        """Create an incorporation filing, return the filing."""
        return BusinessResource._save_incorporation_filing(request.get_json(), request)

    @staticmethod
    @cors.crossdomain(origin='*')
    def put(identifier):
        """Edit an incorporation filing. Return the filing."""
        return BusinessResource._save_incorporation_filing(request.get_json(), request, identifier)

    @staticmethod
    def _save_incorporation_filing(incorporation_body, client_request, business_id=None):
        """Create or update an incorporation filing."""
        # Check that there is a JSON filing
        if not incorporation_body:
            return {'message': f'No filing json data in body of post for incorporation'}, \
                HTTPStatus.BAD_REQUEST

        temp_corp_num = incorporation_body['filing']['incorporationApplication']['nameRequest']['nrNumber']
        # temp_corp_num = business_id
        # If this is an update to an incorporation filing, a temporary business identifier is passed in
        if business_id:
            business = Business.find_by_identifier(business_id)
            if not business:
                return {'message': f'No incorporation filing exists for id {business_id}'}, \
                    HTTPStatus.BAD_REQUEST
        else:
            # Ensure there are no current businesses with the NR/random identifier
            business = Business.find_by_identifier(temp_corp_num)

            if business:
                return {'message': f'Incorporation filing for {temp_corp_num} already exists'}, \
                    HTTPStatus.BAD_REQUEST
            # Create an empty business record, to be updated by the filer
            business = Business()
            business.identifier = temp_corp_num
            business.save()

        # Ensure the business identifier matches the NR in the filing
        err = validate(business, incorporation_body)
        if err:
            return jsonify(err.msg), err.code

        filing = Filing.get_filings_by_type(business.id, 'incorporationApplication')

        # There can only be zero or one incorporation filings, if there are none, this is an
        # initial request for incorporation. Create and insert a filing.
        if not filing:
            filing = Filing()
            filing.business_id = business.id
        elif len(filing) > 1:
            return {'message': 'more than one incorporation filing found for corp'}, HTTPStatus.BAD_REQUEST
        else:
            filing = filing[0]
        filing.filing_json = incorporation_body
        filing.save()
        return jsonify(filing.json),\
            (HTTPStatus.CREATED if (client_request.method == 'POST') else HTTPStatus.ACCEPTED)
