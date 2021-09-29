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
from typing import Final

from flask import jsonify, request
from flask_cors import cross_origin

from legal_api.core import Filing
from legal_api.exceptions import ErrorCode, get_error_message
from legal_api.models import Business
from legal_api.services import authorized
from legal_api.utils.auth import jwt
from legal_api.utils.util import cors_preflight

# from ..api_namespace import API
from ..bp import bp
# noqa: I003; the multiple route decorators cause an erroneous error in line space counting


DOCUMENTS_BASE_ROUTE: Final = '/<string:identifier>/filings/<int:filing_id>/documents'


@cors_preflight('GET, POST')
@bp.route(DOCUMENTS_BASE_ROUTE, methods=['GET', 'OPTIONS'])
@bp.route(DOCUMENTS_BASE_ROUTE + '/<string:legal_filing_name>', methods=['GET', 'OPTIONS'])
@cross_origin(origin='*')
@jwt.requires_auth
def get_documents(identifier: str, filing_id: int, legal_filing_name: str = None):
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
        return _get_document_list(business.identifier, filing)

    return {}, HTTPStatus.NOT_FOUND


def _get_document_list(business_identifier, filing):
    # b = API.base_path()
    # u = API.base_url()
    if not (document_list := Filing.get_document_list(business_identifier, filing, request)):
        return {}, HTTPStatus.NOT_FOUND

    return jsonify(document_list), HTTPStatus.OK
