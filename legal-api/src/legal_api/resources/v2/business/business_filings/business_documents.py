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
from typing import Final, Optional

import requests
from flask import current_app, jsonify, request
from flask_cors import cross_origin

from legal_api.core import Filing
from legal_api.exceptions import ErrorCode, get_error_message
from legal_api.models import Business, Document
from legal_api.models import Filing as FilingModel
from legal_api.reports import get_pdf
from legal_api.resources.v2.business.bp import bp
from legal_api.services import MinioService, authorized
from legal_api.utils.auth import jwt
from legal_api.utils.legislation_datetime import LegislationDatetime
from legal_api.utils.util import cors_preflight

# noqa: I003; the multiple route decorators cause an erroneous error in line space counting


DOCUMENTS_BASE_ROUTE: Final = "/<string:identifier>/filings/<int:filing_id>/documents"


@cors_preflight("GET, POST")
@bp.route(DOCUMENTS_BASE_ROUTE, methods=["GET", "OPTIONS"])
@bp.route(DOCUMENTS_BASE_ROUTE + "/<string:legal_filing_name>", methods=["GET", "OPTIONS"])
@bp.route(DOCUMENTS_BASE_ROUTE + "/static/<string:file_key>", methods=["GET", "OPTIONS"])
@cross_origin(origin="*")
@jwt.requires_auth
def get_documents(identifier: str, # noqa: PLR0911, PLR0912
                  filing_id: int,
                  legal_filing_name: Optional[str] = None,
                  file_key: Optional[str] = None):
    """Return a JSON object with meta information about the Service."""
    # basic checks
    if not authorized(identifier, jwt, ["view", ]):
        return jsonify(
            message=get_error_message(ErrorCode.NOT_AUTHORIZED, identifier=identifier)
        ), HTTPStatus.UNAUTHORIZED

    if identifier.startswith("T"):
        filing_model = FilingModel.get_temp_reg_filing(identifier)
        business = Business.find_by_internal_id(filing_model.business_id)
    else:
        business = Business.find_by_identifier(identifier)

    if not business and not identifier.startswith("T"):
        return jsonify(
            message=get_error_message(ErrorCode.MISSING_BUSINESS, identifier=identifier)
        ), HTTPStatus.NOT_FOUND

    filing = Filing.get(identifier, filing_id)
    if filing and identifier.startswith("T") and filing.id != filing_id:
        withdrawn_filing = Filing.get_by_withdrawn_filing_id(filing_id=filing_id,
                                                             withdrawn_filing_id=filing.id,
                                                             filing_type=Filing.FilingTypes.NOTICEOFWITHDRAWAL)
        if withdrawn_filing:
            filing = withdrawn_filing

    if not filing:
        return jsonify(
            message=get_error_message(ErrorCode.FILING_NOT_FOUND,
                                      filing_id=filing_id, identifier=identifier)
        ), HTTPStatus.NOT_FOUND

    if not legal_filing_name and not file_key:
        if identifier.startswith("T") and filing.status == Filing.Status.COMPLETED and \
                filing.filing_type != Filing.FilingTypes.NOTICEOFWITHDRAWAL:
            return {"documents": {}}, HTTPStatus.OK
        return _get_document_list(business, filing)

    if "application/pdf" in request.accept_mimetypes:
        file_name = (legal_filing_name or file_key)
        if not _is_document_available(business, filing, file_name):
            return jsonify(
                message=get_error_message(ErrorCode.DOCUMENT_NOT_FOUND,
                                          file_name=file_name, filing_id=filing_id, identifier=identifier)
            ), HTTPStatus.NOT_FOUND

        if legal_filing_name:
            if legal_filing_name.lower().startswith("receipt"):
                return _get_receipt(business, filing, jwt.get_token_auth_header())

            return get_pdf(filing.storage, legal_filing_name)
        elif file_key and (document := Document.find_by_file_key(file_key)):
            if document.filing_id == filing.id:  # make sure the file belongs to this filing
                response = MinioService.get_file(document.file_key)
                return current_app.response_class(
                    response=response.data,
                    status=response.status,
                    mimetype="application/pdf"
                )

    return {}, HTTPStatus.NOT_FOUND


def _is_document_available(business, filing, file_name):
    """Check if the document is available."""
    document_list = Filing.get_document_list(business, filing, jwt)
    documents = {}
    if legal_filings := document_list.get("documents").pop("legalFilings", None):
        for doc in legal_filings:
            documents = {**documents, **doc}
    if static_documents := document_list.get("documents").pop("staticDocuments", None):
        for file in static_documents:  # file_key is the last part of the url
            documents = {**documents, file["url"].split("/")[-1]: file["url"]}
    if docs := document_list.get("documents"):
        documents = {**documents, **docs}

    return file_name in documents


def _get_document_list(business, filing):
    """Get list of document outputs."""
    if not (document_list := Filing.get_document_list(business, filing, jwt)):
        return {}, HTTPStatus.NOT_FOUND

    return jsonify(document_list), HTTPStatus.OK


def _get_receipt(business: Business, filing: Filing, token):
    """Get the receipt for the filing."""
    if filing.status not in (
            Filing.Status.COMPLETED,
            Filing.Status.CORRECTED,
            Filing.Status.PAID,
            Filing.Status.WITHDRAWN
    ):
        return {}, HTTPStatus.BAD_REQUEST

    effective_date = None
    filing_date = filing.storage.payment_completion_date or filing.storage.filing_date
    if (
        filing.storage.effective_date.date() != filing_date.date() or
        filing.filing_type == "noticeOfWithdrawal"
    ):
        effective_date = LegislationDatetime.format_as_report_string(filing.storage.effective_date)

    headers = {"Authorization": "Bearer " + token}

    corp_name = _get_corp_name(business, filing.storage)

    url = f'{current_app.config.get("PAYMENT_SVC_URL")}/{filing.storage.payment_token}/receipts'
    receipt = requests.post(
        url,
        json={
            "corpName": corp_name,
            "filingDateTime": LegislationDatetime.format_as_report_string(filing_date),
            "effectiveDateTime": effective_date if effective_date else "",
            "filingIdentifier": str(filing.id),
            "businessNumber": business.tax_id if business and business.tax_id else ""
        },
        headers=headers
    )

    if receipt.status_code != HTTPStatus.CREATED:
        current_app.logger.error("Failed to get receipt pdf for filing: %s", filing.id)

    return receipt.content, receipt.status_code


def _get_corp_name(business, filing):
    """Get the corp name for the filing."""
    if business:
        return business.legal_name

    filing_json = filing.filing_json.get("filing", {})
    name_request = filing_json.get(filing.filing_type, {}).get("nameRequest", {})

    legal_name = name_request.get("legalName") or filing_json.get("business", {}).get("legalName")
    if legal_name:
        return legal_name

    legal_type = name_request.get("legalType") or filing_json.get("business", {}).get("legal_type")
    if legal_type:
        return Business.BUSINESSES.get(legal_type, {}).get("numberedDescription", "")

    return ""
