# Copyright © 2021 Province of British Columbia
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
"""Retrieve the specified report for the entity."""
from http import HTTPStatus

from flask import current_app, jsonify, request, url_for
from flask_cors import cross_origin

from legal_api.exceptions import ErrorCode, get_error_message
from legal_api.models import Business
from legal_api.reports.business_document import BusinessDocument
from legal_api.services import authorized
from legal_api.utils.auth import jwt

from .bp import bp


@bp.route('/<string:identifier>/documents', methods=['GET', 'OPTIONS'])
@bp.route('/<string:identifier>/documents/<string:document_name>', methods=['GET', 'OPTIONS'])
@cross_origin(origin='*')
@jwt.requires_auth
def get_business_documents(identifier: str, document_name: str = None):
    """Return the business documents."""
    # basic checks
    if not authorized(identifier, jwt, ['view', ]):
        return jsonify(
            message=get_error_message(ErrorCode.NOT_AUTHORIZED, **{'identifier': identifier})
        ), HTTPStatus.UNAUTHORIZED

    business = Business.find_by_identifier(identifier)

    if not business:
        return jsonify(
            message=get_error_message(ErrorCode.MISSING_BUSINESS, **{'identifier': identifier})
        ), HTTPStatus.NOT_FOUND

    if not document_name:
        return _get_document_list(business)

    if document_name and ('application/pdf' in request.accept_mimetypes):
        return BusinessDocument(business, document_name).get_pdf()
    return {}, HTTPStatus.NOT_FOUND


def _get_document_list(business):
    """Get list of business documents."""
    base_url = current_app.config.get('LEGAL_API_BASE_URL')
    base_url = base_url[:base_url.find('/api')]
    doc_url = url_for('API2.get_business_documents', **{'identifier': business.identifier,
                                                        'document_name': None})
    business_documents = ['summary']
    documents = {'documents': {}}

    for doc in business_documents:
        documents['documents'][doc] = f'{base_url}{doc_url}/{doc}'

    return jsonify(documents), HTTPStatus.OK
