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

from flask import current_app, g, jsonify, request, url_for, Response
from flask_cors import cross_origin

from legal_api.exceptions import ErrorCode, get_error_message
from legal_api.models import Business, Filing, User
from legal_api.models.document import Document, DocumentType
from legal_api.reports.business_document import BusinessDocument
from legal_api.services import authorized, flags, RequestContext
from legal_api.services.business import validate_document_request
from legal_api.utils.auth import jwt
from legal_api.utils.legislation_datetime import LegislationDatetime

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

    account_id = request.headers.get("Account-Id", None)
    user = User.get_or_create_user_by_jwt(g.jwt_oidc_token_info)

    # Hide business summary for tombstone corps
    if (
        not flags.is_on('enable-business-summary-for-migrated-corps', user=user, account_id=account_id) and
        business.is_tombstone and
        business.legal_type in Business.CORPS and
        document_name == 'summary'
    ):
        return {}, HTTPStatus.NOT_FOUND

    if document_name:
        rc = RequestContext(account_id=account_id, user=user)
        current_app.logger.info(
            f'Getting document {document_name} for business {identifier} with account_id {account_id}'
        )
        if 'application/pdf' in request.accept_mimetypes:
            pdf_content, status_code = (BusinessDocument(business, document_name, request_context=rc)
                                        .get_pdf())
            if status_code == HTTPStatus.OK:
                return Response(
                    pdf_content,
                    mimetype='application/pdf',
                    headers={
                        'Content-Type': 'application/pdf',
                    }
                )
            return pdf_content, status_code
        elif 'application/json' in request.accept_mimetypes:
            return BusinessDocument(business, document_name, request_context=rc).get_json()
    return {}, HTTPStatus.NOT_FOUND


def _get_document_list(business):
    """Get list of business documents."""
    base_url = current_app.config.get('LEGAL_API_BASE_URL')
    base_url = base_url[:base_url.find('/api')]
    doc_url = url_for('API2.get_business_documents', **{'identifier': business.identifier,
                                                        'document_name': None})
    documents = {'documents': {}}

    account_id = request.headers.get("Account-Id", None)
    user = User.get_or_create_user_by_jwt(g.jwt_oidc_token_info)

    # Hide business summary for tombstone corps
    if (
        not flags.is_on('enable-business-summary-for-migrated-corps', user=user, account_id=account_id) and
        business.is_tombstone and
        business.legal_type in Business.CORPS
    ):
        return jsonify(documents), HTTPStatus.OK

    business_documents = ['summary']
    for doc in business_documents:
        documents['documents'][doc] = f'{base_url}{doc_url}/{doc}'

    if business.legal_type == Business.LegalTypes.COOP.value:
        documents['documentsInfo'] = {}
        coop_documents, coop_info = _get_coop_documents_and_info(business)
        for k, v in coop_documents.items():
            documents['documents'][k] = v
        for k, v in coop_info.items():
            documents['documentsInfo'][k] = v

    return jsonify(documents), HTTPStatus.OK


# This is used as part of entity snapshot in business-edit-ui.
def _get_coop_documents_and_info(business):
    """Get certified memorandum and rules documents + info for coop."""
    documents, info = {}, {}

    if not business:
        return documents, info

    base_url = current_app.config.get('LEGAL_API_BASE_URL')
    base_url = base_url[:base_url.find('/api')]

    info['certifiedRules'], info['certifiedMemorandum'] = {}, {}

    sr_filings = Filing.get_filings_by_types(business.id, ['specialResolution'])
    cr_filings = Filing.get_filings_by_types(business.id, ['correction'])

    def filter_resolutions(filings, filing_type, key):
        return [
            f for f in filings
            if f.filing_json['filing'].get(filing_type, {}).get(key) is True
        ]

    rules_resolutions = (
        filter_resolutions(sr_filings, 'alteration', 'rulesInResolution') +
        filter_resolutions(cr_filings, 'correction', 'rulesInResolution')
    )

    memo_resolutions = (
        filter_resolutions(sr_filings, 'alteration', 'memorandumInResolution') +
        filter_resolutions(cr_filings, 'correction', 'memorandumInResolution')
    )

    def set_doc_info(doc_type, doc_label):
        if doc := Document.find_by_business_id_and_type(business.id, doc_type.value):
            filing = Filing.find_by_id(doc.filing_id)
            doc_url = url_for('API2.get_documents', identifier=business.identifier,
                              filing_id=filing.id, legal_filing_name=None)
            documents[doc_label] = f'{base_url}{doc_url}/{doc_label}'
            filing_date_str = LegislationDatetime.format_as_legislation_date(filing.filing_date)
            info[doc_label] = {
                'key': doc.file_key,
                'name': (
                    f'{business.identifier} - '
                    f'{doc_label.replace("certified", "Certified ")} - '
                    f'{filing_date_str}.pdf'
                ),
                'uploaded': filing.filing_date.isoformat()
            }

    set_doc_info(DocumentType.COOP_RULES, 'certifiedRules')
    set_doc_info(DocumentType.COOP_MEMORANDUM, 'certifiedMemorandum')

    if rules_resolutions:
        latest = max(f.filing_date for f in rules_resolutions)
        info['certifiedRules']['includedInResolution'] = True
        info['certifiedRules']['includedInResolutionDate'] = latest.isoformat()

    if memo_resolutions:
        latest = max(f.filing_date for f in memo_resolutions)
        info['certifiedMemorandum']['includedInResolution'] = True
        info['certifiedMemorandum']['includedInResolutionDate'] = latest.isoformat()

    return documents, info
