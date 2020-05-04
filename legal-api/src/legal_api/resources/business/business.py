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

from flask import g, jsonify, request
from flask_restplus import Resource, cors

from legal_api.models import Business, User
from legal_api.resources.business.business_filings import ListFilingResource
from legal_api.services import authorized
from legal_api.services.filings import validate
from legal_api.utils.auth import jwt
from legal_api.utils.util import cors_preflight

from .api_namespace import API


@cors_preflight('GET, POST')
@API.route('/<string:identifier>', methods=['GET', 'OPTIONS'])
@API.route('', methods=['POST', 'OPTIONS'])
class BusinessResource(Resource):
    """Meta information about the overall service."""

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_auth
    def get(identifier):
        """Return a JSON object with meta information about the Service."""
        # check authorization
        # if not authorized(identifier, jwt, action=['view']):
        #     return jsonify({'message':
        #                     f'You are not authorized to view business {identifier}.'}), \
        #         HTTPStatus.UNAUTHORIZED

        business = Business.find_by_identifier(identifier)

        if not business:
            return jsonify({'message': f'{identifier} not found'}), HTTPStatus.NOT_FOUND

        return jsonify(business=business.json())

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_auth
    def post():
        """Create a business from an incorporation filing, return the filing."""
        draft = (request.args.get('draft', None).lower() == 'true') \
            if request.args.get('draft', None) else False

        json_input = request.get_json()

        # validate filing
        err = validate(None, json_input)
        if err:
            json_input['errors'] = err.msg
            return jsonify(json_input), err.code

        # create business
        business, err_msg, err_code = BusinessResource._create_business(json_input, request)
        if err_msg:
            if isinstance(err_msg, list):
                json_input['errors'] = [err for err in err_msg]
            elif err_msg:
                json_input['errors'] = [err_msg, ]
            return jsonify(json_input), err_code

        # create filing
        user = User.get_or_create_user_by_jwt(g.jwt_oidc_token_info)
        business, filing, err_msg, err_code = ListFilingResource._save_filing(  # pylint: disable=protected-access
            request, business.identifier, user, None)
        if err_msg or draft:
            reply = filing.json if filing else json_input
            reply['errors'] = [err_msg, ]
            return jsonify(reply), err_code or HTTPStatus.CREATED

        # complete filing
        response, response_code = ListFilingResource.complete_filing(business, filing, draft)
        if response:
            return response, response_code

        # all done
        return jsonify(filing.json), HTTPStatus.CREATED

    @staticmethod
    def _create_business(incorporation_body, client_request):
        """Create a business from an incorporation filing."""
        # Check that there is a JSON filing
        if not incorporation_body:
            return None, {'message': f'No filing json data in body of post for incorporation'}, \
                HTTPStatus.BAD_REQUEST

        temp_corp_num = incorporation_body['filing']['incorporationApplication']['nameRequest']['nrNumber']

        # check authorization
        if not authorized(temp_corp_num, jwt, action=['edit']):
            return None, {'message': f'You are not authorized to incorporate for {temp_corp_num}.'}, \
                HTTPStatus.UNAUTHORIZED

        # Ensure there are no current businesses with the NR/random identifier
        business = Business.find_by_identifier(temp_corp_num)

        if business:
            return None, {'message': f'Incorporation filing for {temp_corp_num} already exists'}, \
                HTTPStatus.BAD_REQUEST

        # Create an empty business record, to be updated by the filer
        business = Business()
        business.identifier = temp_corp_num
        business.save()

        return business, None, (HTTPStatus.CREATED if (client_request.method == 'POST') else HTTPStatus.ACCEPTED)
