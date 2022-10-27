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
from legal_api.models import Business, Filing
from legal_api.models.document import Document, DocumentType
from legal_api.reports.business_document import BusinessDocument
from legal_api.services import authorized
from legal_api.services.business import validate_document_request
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

    err = validate_document_request(document_name, business)
    if err:
        response_message = {'errors': err.msg}
        return jsonify(response_message), err.code

    if document_name:
        if 'application/pdf' in request.accept_mimetypes:
            return BusinessDocument(business, document_name).get_pdf()
        elif 'application/json' in request.accept_mimetypes:
            return BusinessDocument(business, document_name).get_json()
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

    if business.legal_type == Business.LegalTypes.COOP.value:
        coop_documents = _get_coop_documents_ist(business)
        for coop_doc_key, coop_doc_value in coop_documents.items():
            documents['documents'][coop_doc_key] = coop_doc_value

    return jsonify(documents), HTTPStatus.OK


def _get_coop_documents_ist(business):
    """Get certified memorandum and rules for coop."""
    coop_documents = {}

    if not business:
        return coop_documents

    base_url = current_app.config.get('LEGAL_API_BASE_URL')
    base_url = base_url[:base_url.find('/api')]
    business_id = business.id
    business_identifier = business.identifier

    coop_rules_document = Document.find_by_business_id_and_type(business_id, DocumentType.COOP_RULES.value)

    if coop_rules_document:
        coop_rules_filing = Filing.find_by_id(coop_rules_document.filing_id)
        coop_rules_doc_url = url_for('API2.get_documents', **{'identifier': business_identifier,
                                                              'filing_id': coop_rules_filing.id,
                                                              'legal_filing_name': None})
        coop_documents['certifiedRules'] = f'{base_url}{coop_rules_doc_url}/certifiedRules'

    coop_memorandum_document = Document.find_by_business_id_and_type(business_id, DocumentType.COOP_MEMORANDUM.value)

    if coop_memorandum_document:
        coop_memorandum_filing = Filing.find_by_id(coop_memorandum_document.filing_id)
        coop_memorandum_doc_url = url_for('API2.get_documents', **{'identifier': business_identifier,
                                                                   'filing_id': coop_memorandum_filing.id,
                                                                   'legal_filing_name': None})
        coop_documents['certifiedMemorandum'] = f'{base_url}{coop_memorandum_doc_url}/certifiedMemorandum'

    return coop_documents
