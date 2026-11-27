# Copyright © 2024 Province of British Columbia
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
"""Module for maintaining client documents."""

import re
from http import HTTPStatus

from flask import Blueprint, current_app, jsonify, request
from flask_cors import cross_origin
from sqlalchemy import or_

from business_model.models import Business, Document, Filing
from legal_api.services import authorized, doc_service
from legal_api.services.authz import (
    STAFF_ROLE,
    SYSTEM_ROLE,
    AuthServiceUnavailableError,
    has_any_roles,
    is_new_feature_enabled,
    log_unauthorized_request,
)
from legal_api.utils.auth import jwt

bp = Blueprint("DOCUMENTS2", __name__, url_prefix="/api/v2/documents")

CLIENT_DOCUMENTS_FEATURE = "authV2ClientDocuments"  # a value inside the enable-new-feature flag

DOCUMENT_CLASS_DEFAULT = "CORP"
# DRS class-DRS id, or a bare DRS id: anything else can reach DRS as a different id than the one checked here
DOCUMENT_KEY_PATTERN = re.compile(r"(?:[A-Z_]+-)?DS[0-9A-Z]+")
DOCUMENT_TYPE_DEFAULT = "COSD"
HEADER_ACCEPT = "Accept"
PARAM_FILENAME = "filename"
PARAM_FILEDATE = "filingDate"
PARAM_IDENTIFIER = "businessIdentifier"
PARAM_FILING_ID = "filingId"
DRS_PROPERTY_MAPPING = {
    PARAM_FILENAME: "consumerFilename",
    PARAM_FILEDATE: "consumerFilingDate",
    PARAM_IDENTIFIER: "consumerIdentifier",
    PARAM_FILING_ID: "consumerReferenceId"
}
DRS_MAPPING_DOC_CLASS = {
    "CP": "COOP",
    "GP": "FIRM",
    "SP": "FIRM",
    "DEFAULT": "CORP"
}
DRS_MAPPING_DOC_TYPE = {
    "continuationIn": {
        "documentTypes": {
            "authorization_file": "CNTA",
            "director_affidavit": "DIRECTOR_AFFIDAVIT"
        }
    },
    "continuationOut": {
        "documentTypes": {
            "continuation_out": "CNTO"
        }
    },
    "correction": {
        "documentTypes": {
            "coop_memorandum": "COOP_MEMORANDUM",
            "coop_rules": "COOP_RULES"
        }
    },
    "courtOrder": {
        "documentTypes": {
            "court_order": "CRTO",
            "supporting_document": "SUPP"
        }
    },
    "dissolution": {
        "documentTypes": {
            "affidavit": "COSD"
        }
    },
    "incorporationApplication": {
        "documentTypes": {
            "coop_memorandum": "COOP_MEMORANDUM",
            "coop_rules": "COOP_RULES"
        }
    },
    "specialResolution": {
        "documentTypes": {
            "coop_memorandum": "COOP_MEMORANDUM",
            "coop_rules": "COOP_RULES"
        }
    },
}




def _find_linked_documents(document_key: str) -> list[Document]:
    """Return the documents rows for the DRS document the key resolves to.

    - the DRS calls use only the id part of the key, so every spelling of a key must find the same rows
    """
    drs_ids = {get_drs_id_from_key(document_key), doc_service.get_drs_id(Document(file_key=document_key))}
    filters = [Document.file_key == document_key]
    for drs_id in drs_ids:
        filters.extend([Document.file_key == drs_id, Document.file_key.endswith(f"-{drs_id}", autoescape=True)])
    candidates = Document.query.filter(or_(*filters)).all()
    return [doc for doc in candidates if doc.file_key == document_key or doc_service.get_drs_id(doc) in drs_ids]


def is_draft_filing(file_key: str) -> bool:
    """Check if the filing is a draft filing."""
    for document in _find_linked_documents(file_key):
        filing = Filing.find_by_id(document.filing_id)
        if not filing or filing.status != Filing.Status.DRAFT.value:
            return False
    return True


def _get_linked_identifier(document: Document) -> str | None:
    """Return the business (or temp registration) identifier the document row belongs to."""
    if document.business_id and (business := Business.find_by_internal_id(document.business_id)):
        return business.identifier
    if document.filing_id and (filing := Filing.find_by_id(document.filing_id)):
        if filing.business_id and (business := Business.find_by_internal_id(filing.business_id)):
            return business.identifier
        return filing.temp_reg
    return None


def _is_client_document_denied(document_key: str, action: str) -> bool:
    """Return True (and log) when the authV2ClientDocuments gate is on and the caller cannot access the document.

    - no documents row for the key (upload not yet linked to a filing): allowed
    - row with no resolvable business: staff / system only
    """
    if not is_new_feature_enabled(CLIENT_DOCUMENTS_FEATURE):
        return False
    for document in _find_linked_documents(document_key):
        if identifier := _get_linked_identifier(document):
            is_allowed = authorized(identifier, jwt, [action])
        else:
            is_allowed = has_any_roles(jwt, [STAFF_ROLE, SYSTEM_ROLE])
        if not is_allowed:
            log_unauthorized_request("client document", document_key)
            return True
    return False


def _is_client_document_update_denied(document_key: str) -> bool:
    """Return True (and log) when the authV2ClientDocuments gate is on and the caller is not staff / system."""
    if not is_new_feature_enabled(CLIENT_DOCUMENTS_FEATURE) or has_any_roles(jwt, [STAFF_ROLE, SYSTEM_ROLE]):
        return False
    log_unauthorized_request("client document", document_key)
    return True


def _invalid_key_response(document_key: str):
    """Return the 400 for a document key that is not a DRS class-DRS id, or None when the key is well formed."""
    if DOCUMENT_KEY_PATTERN.fullmatch(document_key):
        return None
    return jsonify(message="Invalid document key."), HTTPStatus.BAD_REQUEST


def _forbidden_response():
    """Return the 403 for a denied client document request."""
    return jsonify(message="You are not authorized to access this document."), HTTPStatus.FORBIDDEN





@bp.route("/client/<string:filing_type>/<string:entity_type>/<string:document_type>", methods=["POST"])
@cross_origin()
@jwt.requires_auth
def create_client_document(filing_type, entity_type, document_type):
    """
    Create a new document record where the payload is the document binary data. Additional information associated with
    the document is submitted with following request parameters:
        filename: The document file name.
        businessIdentifier: The business identifier for change filings where the business exists: include if available.

    The combination of filing_type, entity_type, and document_type is used to derive a DRS document class and document
    type. If no mapping is found the default values of DOCUMENT_CLASS_DEFAULT and DOCUMENT_TYPE_DEFAULT are used.
        
    The response JSON key is the unique identifier for the document record. The caller is expected to store
    this value in the documents table file_key column.
    
    filing_type: One of the filing types that supports the submission of client documents. For example:
                 courtOrder, continuationOut, continuationIn, correction, dissolution, incorporationApplication,
                 specialResolution.
    entity_type: One of the entity/legal business types. For example:
                 BC, BEN, C, CC, CP, CUL, GP, SP, ULC, CBEN, CCC
    document_type: One of the business document types stored in the documents table. For example:
                   affidavit, court_order, continuation_out, authorization_file, director_affidavit,
                   coop_memorandum, coop_rules
    return: Flask response. The response JSON payload key is the unique identifier for the document record.
            Status codes:
            CREATED: success
            INTERNAL_SERVER_ERROR: default when any exception.
            Any response code returned from the DRS API.
    """
    try:
        doc_info: dict = build_create_info(filing_type, entity_type, document_type, request.args)
        response = doc_service.create_document(doc_info, request.get_data(), content_type=request.content_type)
        response_json = doc_service.get_content(response)
        if response.ok:
            file_key = doc_info.get("documentClass") + "-" + response_json.get("documentServiceId")
            current_app.logger.info(f"create_document successful file_key={file_key}")
            response_json["key"] = file_key
            return jsonify(response_json), HTTPStatus.CREATED

        current_app.logger.error(f"Error creating document record: {response_json}")
        return jsonify(
            message="Error creating document record."
        ), response.status_code
    except Exception as e:
        current_app.logger.error(f"Error creating document record: {e}")
        return jsonify(
            message="Error creating document record."
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route("/client/<string:document_key>", methods=["DELETE"])
@cross_origin()
@jwt.requires_auth
def delete_client_document(document_key):
    """
    Delete client document based on the provided document key and if it is a draft filing.

    document_key: DRS document class-DRS ID returned by a previously successful POST request.
    return: Flask response. Status codes:
            OK: success
            FORBIDDEN: Filing is not in a state where an update is allowed.
            INTERNAL_SERVER_ERROR: default when any exception.
            Any response code returned from the DRS API, typically NOT_FOUND.
    """
    if invalid_key := _invalid_key_response(document_key):
        return invalid_key
    try:
        if _is_client_document_denied(document_key, "edit"):
            return _forbidden_response()
        if is_draft_filing(document_key):
            bus_doc: Document = Document(file_key=document_key)
            response = doc_service.delete_document(bus_doc)
            if response.ok:
                return jsonify({"message": f"Document {document_key} deleted successfully."}), HTTPStatus.OK
            api_error = doc_service.get_content(response)
            current_app.logger.error(f"Error deleting file {document_key}: {api_error}")
            return jsonify(
                message=f"Error deleting file {document_key}."
            ), response.status_code
        return jsonify({"message": "Filing is not a draft."}), HTTPStatus.FORBIDDEN
    except AuthServiceUnavailableError:
        raise
    except Exception as e:
        current_app.logger.error(f"Error deleting file {document_key}: {e}")
        return jsonify(
            message=f"Error deleting file {document_key}."
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route("/client/<string:document_key>", methods=["GET"])
@cross_origin()
@jwt.requires_auth
def get_client_document(document_key):
    """
    Get a client document based on the provided document key returned by a previously successful POST request.
    By default the document binary data representing the document itself is returned. If the request includes
    and Accept=application/json header then the DRS response is JSON with a storage download URL for the
    document accessed by the downloadURL property.

    document_key: DRS document class-DRS ID returned by a previously successful POST request.
    return: Flask response. Status codes:
            OK: success
            Any response code returned from the DRS API, typically NOT_FOUND.
            INTERNAL_SERVER_ERROR: default when any exception.
    """
    if invalid_key := _invalid_key_response(document_key):
        return invalid_key
    try:
        if _is_client_document_denied(document_key, "view"):
            return _forbidden_response()
        doc_class = get_drs_class_from_key(document_key)
        drs_id = get_drs_id_from_key(document_key)
        accept = request.headers.get(HEADER_ACCEPT)
        doc_binary = accept is None or accept != doc_service.APP_JSON
        response = doc_service.get_document(drs_id, doc_class, doc_binary)
        if response.ok:
            if doc_binary:
                return current_app.response_class(
                        response=response.content,
                        status=response.status_code,
                        mimetype="application/pdf"
                    )
            return jsonify(doc_service.get_content(response)), HTTPStatus.OK
        api_error = doc_service.get_content(response)
        current_app.logger.error(f"Error getting file {document_key}: {api_error}")
        return jsonify(
            message=f"Error getting file {document_key}."
        ), response.status_code
    except AuthServiceUnavailableError:
        raise
    except Exception as e:
        current_app.logger.error(f"Error getting file {document_key}: {e}")
        return jsonify(
            message=f"Error getting file {document_key}."
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route("/client/<string:document_key>", methods=["PUT"])
@cross_origin()
@jwt.requires_auth
def replace_client_document(document_key):
    """
    Replace a client document by document key returned from a previously successful POST request.
    The filing must be in a draft/incomplete state.

    document_key: DRS document class-DRS ID returned by a previously successful POST request.
    return: Flask response. Status codes:
            OK: success
            FORBIDDEN: Filing is not in a state where an update is allowed.
            INTERNAL_SERVER_ERROR: default when any exception.
            Any response code returned from the DRS API.
    """
    if invalid_key := _invalid_key_response(document_key):
        return invalid_key
    try:
        if _is_client_document_denied(document_key, "edit"):
            return _forbidden_response()
        if is_draft_filing(document_key):
            bus_doc: Document = Document(file_key=document_key)
            response = doc_service.add_replace_document(bus_doc, request.get_data(), content_type=request.content_type)
            if response.ok:
                return jsonify({"message": f"Document {document_key} replaced successfully."}), HTTPStatus.OK
            api_error = doc_service.get_content(response)
            current_app.logger.error(f"Error replacing file {document_key}: {api_error}")
            return jsonify(
                message=f"Error replacing file {document_key}."
            ), response.status_code
        return jsonify({"message": "Cannot replace when filing is not a draft."}), HTTPStatus.FORBIDDEN
    except AuthServiceUnavailableError:
        raise
    except Exception as e:
        current_app.logger.error(f"Error replacing file {document_key}: {e}")
        return jsonify(
            message=f"Error adding file {document_key}."
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route("/client/<string:document_key>", methods=["PATCH"])
@cross_origin()
@jwt.requires_auth
def update_client_document_info(document_key):
    """
    Update information associated with a client document by document key returned from a previously successful POST
    request. Typically update after a filing completes with the business identifier, filing date, and filing identifier
    (filings table record id). The expected request payload typically includes:
        filingId: the filings record ID.
        filingDate: the filings record filing date/timestamp in the ISO format.
        businessIdentifier: the businesses record identifier.

    document_key: DRS document class-DRS ID returned by a previously successful POST request.
    return: Flask response. Status codes:
            OK: success
            INTERNAL_SERVER_ERROR: default when any exception.
            Any response code returned from the DRS API.
    """
    if invalid_key := _invalid_key_response(document_key):
        return invalid_key
    try:
        if _is_client_document_update_denied(document_key):
            return _forbidden_response()
        bus_doc: Document = Document(file_key=document_key)
        request_json: dict = request.get_json()
        update_payload: dict = {}
        if request_json.get(PARAM_FILEDATE):
            update_payload[DRS_PROPERTY_MAPPING.get(PARAM_FILEDATE)] = request_json.get(PARAM_FILEDATE)
        if request_json.get(PARAM_IDENTIFIER):
            update_payload[DRS_PROPERTY_MAPPING.get(PARAM_IDENTIFIER)] = request_json.get(PARAM_IDENTIFIER)
        if request_json.get(PARAM_FILING_ID):
            update_payload[DRS_PROPERTY_MAPPING.get(PARAM_FILING_ID)] = request_json.get(PARAM_FILING_ID)
        if request_json.get(PARAM_FILENAME):
            update_payload[DRS_PROPERTY_MAPPING.get(PARAM_FILENAME)] = request_json.get(PARAM_FILENAME)
        current_app.logger.info(f"update doc info mapping\n{request_json}\nto\n{update_payload}")
        response = doc_service.update_document_record(bus_doc, update_payload)
        if response.ok:
            return jsonify({"message": f"Document record {document_key} updated successfully."}), HTTPStatus.OK
        api_error = doc_service.get_content(response)
        current_app.logger.error(f"Error updating document record {document_key}: {api_error}")
        return jsonify(
            message=f"Error updating document record {document_key}."
        ), response.status_code
    except Exception as e:
        current_app.logger.error(f"Error updating document record {document_key}: {e}")
        return jsonify(
            message=f"Error updating document record {document_key}."
        ), HTTPStatus.INTERNAL_SERVER_ERROR


def get_drs_id_from_key(document_key: str) -> str:
    """
    Extract the DRS identifier GUID from the business document file key.

    document_key: Existing documents table record containing the DRS identifier as the file_key value.
    return: The DRS identifier.
    """
    tokens = document_key.split("-")
    if tokens and len(tokens) > 1:
        return tokens[1]
    return document_key


def get_drs_class_from_key(document_key: str) -> str:
    """
    Extract the DRS document class from the business document file key.

    document_key: Existing documents table record containing the DRS identifier as the file_key value.
    return: The DRS document class or DOCUMENT_CLASS_DEFAULT.
    """
    tokens = document_key.split("-")
    if tokens and len(tokens) > 1:
        return tokens[0]
    return DOCUMENT_CLASS_DEFAULT


def build_create_info(filing_type: str, entity_type: str, document_type: str, request_params: dict) -> dict:
    """
    Build the DRS create document information from the request indcluding document class and document type.

    return: The document service request information.
    """
    info: dict = {
        "documentClass": DRS_MAPPING_DOC_CLASS.get(entity_type, DOCUMENT_CLASS_DEFAULT)
    }
    doc_type = DOCUMENT_TYPE_DEFAULT
    if DRS_MAPPING_DOC_TYPE.get(filing_type) and DRS_MAPPING_DOC_TYPE[filing_type]["documentTypes"].get(document_type):
        doc_type = DRS_MAPPING_DOC_TYPE[filing_type]["documentTypes"].get(document_type)
    info["documentType"] = doc_type
    if request_params.get(PARAM_IDENTIFIER):
        info[DRS_PROPERTY_MAPPING.get(PARAM_IDENTIFIER)] = request_params.get(PARAM_IDENTIFIER)
    if request_params.get(PARAM_FILENAME):
        info[DRS_PROPERTY_MAPPING.get(PARAM_FILENAME)] = request_params.get(PARAM_FILENAME)
    if request_params.get(PARAM_FILING_ID):
        info[DRS_PROPERTY_MAPPING.get(PARAM_FILING_ID)] = str(request_params.get(PARAM_FILING_ID))
    if request_params.get(PARAM_FILEDATE):
        info[DRS_PROPERTY_MAPPING.get(PARAM_FILEDATE)] = request_params.get(PARAM_FILEDATE)
    return info
