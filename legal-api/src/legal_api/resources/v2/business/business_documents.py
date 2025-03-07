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
from legal_api.services import authorized, flags
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

    # Hide business summary for tombstone corps
    if (
        not flags.is_on('enable-business-summary-for-migrated-corps') and
        business.is_tombstone and
        business.legal_type in Business.CORPS and
        document_name == "summary"
    ):
        return {}, HTTPStatus.NOT_FOUND

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
    documents = {'documents': {}}

    # Hide business summary for tombstone corps
    if (
        not flags.is_on('enable-business-summary-for-migrated-corps') and
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
    sr_rules_resolution = [sr for sr in sr_filings
                           if sr.filing_json['filing'].get('alteration', {}).get('rulesInResolution') is True]
    sr_memorandum_resolution = [sr for sr in sr_filings
                                if sr.filing_json['filing'].get('alteration', {}).get('memorandumInResolution') is True]
    if rules_document := Document.find_by_business_id_and_type(business.id, DocumentType.COOP_RULES.value):
        rules_filing = Filing.find_by_id(rules_document.filing_id)
        rules_doc_url = url_for('API2.get_documents', **{'identifier': business.identifier,
                                                         'filing_id': rules_filing.id,
                                                         'legal_filing_name': None})
        documents['certifiedRules'] = f'{base_url}{rules_doc_url}/certifiedRules'
        filing_date_str = LegislationDatetime.format_as_legislation_date(rules_filing.filing_date)
        file_name = f'{business.identifier} - Certified Rules - {filing_date_str}.pdf'
        info['certifiedRules'] = {
            'key': rules_document.file_key,
            'name': file_name,
            'uploaded': rules_filing.filing_date.isoformat()
        }
    if sr_rules_resolution:
        info['certifiedRules']['includedInResolution'] = True
        info['certifiedRules']['includedInResolutionDate'] = sr_rules_resolution[0].filing_date.isoformat()

    if memorandum_document := Document.find_by_business_id_and_type(
            business.id, DocumentType.COOP_MEMORANDUM.value):
        memorandum_filing = Filing.find_by_id(memorandum_document.filing_id)
        memorandum_doc_url = url_for('API2.get_documents', **{'identifier': business.identifier,
                                                              'filing_id': memorandum_filing.id,
                                                              'legal_filing_name': None})
        documents['certifiedMemorandum'] = f'{base_url}{memorandum_doc_url}/certifiedMemorandum'
        filing_date_str = LegislationDatetime.format_as_legislation_date(memorandum_filing.filing_date)
        file_name = f'{business.identifier} - Certified Memorandum - {filing_date_str}.pdf'
        info['certifiedMemorandum'] = {
            'key': memorandum_document.file_key,
            'name': file_name,
            'uploaded': memorandum_filing.filing_date.isoformat()
        }
    if sr_memorandum_resolution:
        info['certifiedMemorandum']['includedInResolution'] = True
        info['certifiedMemorandum']['includedInResolutionDate'] = sr_memorandum_resolution[0].filing_date.isoformat()

    return documents, info
