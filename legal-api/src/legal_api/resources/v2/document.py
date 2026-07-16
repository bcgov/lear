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

from http import HTTPStatus

from flask import Blueprint, current_app, jsonify, request
from flask_cors import cross_origin

#from business_model.models import Document, Filing
from legal_api.models import Document, Filing
from legal_api.services import doc_service
from legal_api.services.minio import MinioService
from legal_api.utils.auth import jwt

bp = Blueprint("DOCUMENTS2", __name__, url_prefix="/api/v2/documents")

DOCUMENT_CLASS_DEFAULT = "CORP"
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
            "court_order": "CRTO"
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


@bp.route("/<string:file_name>/signatures", methods=["GET"])
@cross_origin()
@jwt.requires_auth
def get_signatures(file_name: str):
    """Return a pre-signed URL for the new document."""
    return MinioService.create_signed_put_url(file_name), HTTPStatus.OK


def is_draft_filing(file_key: str) -> bool:
    """Check if the filing is a draft filing."""
    document = Document.find_by_file_key(file_key)
    if not document:
        return True
    filing = Filing.find_by_id(document.filing_id)
    return filing and filing.status == Filing.Status.DRAFT.value


@bp.route("/<string:document_key>", methods=["DELETE"])
@cross_origin()
@jwt.requires_auth
def delete_minio_document(document_key):
    """Delete Minio document based on the provided document key and if it is a draft filing."""
    try:
        if is_draft_filing(document_key):
            MinioService.delete_file(document_key)
            return jsonify({"message": f"File {document_key} deleted successfully."}), HTTPStatus.OK
        return jsonify({"message": "Filing is not a draft."}), HTTPStatus.FORBIDDEN
    except Exception as e:
        current_app.logger.error(f"Error deleting file {document_key}: {e}")
        return jsonify(
            message=f"Error deleting file {document_key}."
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route("/<string:document_key>", methods=["GET"])
@cross_origin()
@jwt.requires_auth
def get_minio_document(document_key: str):
    """Get the document from Minio."""
    try:
        response = MinioService.get_file(document_key)
        return current_app.response_class(
                response=response.data,
                status=response.status,
                mimetype="application/pdf"
            )
    except Exception as e:
        current_app.logger.error(f"Error getting file {document_key}: {e}")
        return jsonify(
            message=f"Error getting file {document_key}."
        ), HTTPStatus.INTERNAL_SERVER_ERROR


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
        response = doc_service.create_document(doc_info, request.get_data())
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
    try:
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
    try:
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
    try:
        if is_draft_filing(document_key):
            bus_doc: Document = Document(file_key=document_key)
            response = doc_service.add_replace_document(bus_doc, request.get_data())
            if response.ok:
                return jsonify({"message": f"Document {document_key} replaced successfully."}), HTTPStatus.OK
            api_error = doc_service.get_content(response)
            current_app.logger.error(f"Error replacing file {document_key}: {api_error}")
            return jsonify(
                message=f"Error replacing file {document_key}."
            ), response.status_code
        return jsonify({"message": "Cannot replace when filing is not a draft."}), HTTPStatus.FORBIDDEN
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
    try:
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
