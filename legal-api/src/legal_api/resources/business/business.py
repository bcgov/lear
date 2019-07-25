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

from flask import jsonify
from flask_restplus import Resource, cors

from legal_api.models import Business
from legal_api.utils.util import cors_preflight

from .api_namespace import API


@cors_preflight('GET,')
@API.route('/<string:identifier>', methods=['GET', 'OPTIONS'])
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
