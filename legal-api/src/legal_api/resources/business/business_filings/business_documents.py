# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Searching on a business entity's documents.

Provides all the search and retrieval from the business entity documents.
"""
from http import HTTPStatus

from flask import jsonify
from flask_restx import Resource, cors

from legal_api.core import Filing
from legal_api.exceptions import ErrorCode, get_error_message
from legal_api.models import Business
from legal_api.services import authorized
from legal_api.utils.auth import jwt
from legal_api.utils.util import cors_preflight

from ..api_namespace import API
# noqa: I003; the multiple route decorators cause an erroneous error in line space counting


@cors_preflight('GET, POST')
@API.route('/<string:identifier>/filings/<int:filing_id>/documents', methods=['GET', 'OPTIONS'])
@API.route('/<string:identifier>/filings/<int:filing_id>/documents/<string:legal_filing_name>',
           methods=['GET', 'OPTIONS']
           )
class FilingDocumentsResource(Resource):
    """Business Comment service."""

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_auth
    def get(identifier: str, filing_id: int, legal_filing_name: str = None):
        """Return a JSON object with meta information about the Service."""
        # basic checks
        if not authorized(identifier, jwt, ['GET', ]):
            return jsonify(
                message=get_error_message(ErrorCode.NOT_AUTHORIZED, **{'identifier': identifier})
            ), HTTPStatus.UNAUTHORIZED

        if not (business := Business.find_by_identifier(identifier)):
            return jsonify(
                message=get_error_message(ErrorCode.MISSING_BUSINESS, **{'identifier': identifier})
                ), HTTPStatus.NOT_FOUND

        if not (filing := Filing.get(identifier, filing_id)):
            return jsonify(
                message=get_error_message(ErrorCode.FILING_NOT_FOUND,
                                          **{'filing_id': filing_id, 'identifier': identifier})
                ), HTTPStatus.NOT_FOUND

        if not legal_filing_name:
            return FilingDocumentsResource._get_document_list(business.identifier, filing)

        return {}, HTTPStatus.NOT_FOUND

    @staticmethod
    def _get_document_list(business_identifier, filing):
        if not (document_list := Filing.get_document_list(business_identifier, filing)):
            return {}, HTTPStatus.NOT_FOUND

        return jsonify(document_list), HTTPStatus.OK
