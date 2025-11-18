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
"""Module for handling Minio document operations."""

from http import HTTPStatus

from flask import Blueprint, current_app, jsonify
from flask_cors import cross_origin

from legal_api.models import Document, Filing
from legal_api.services.minio import MinioService
from legal_api.utils.auth import jwt


bp = Blueprint("DOCUMENTS2", __name__, url_prefix="/api/v2/documents")


@bp.route("/<string:file_name>/signatures", methods=["GET"])
@cross_origin(origin="*")
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
@cross_origin(origin="*")
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
        return jsonify(message=f"Error deleting file {document_key}."), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route("/<string:document_key>", methods=["GET"])
@cross_origin(origin="*")
@jwt.requires_auth
def get_minio_document(document_key: str):
    """Get the document from Minio."""
    try:
        response = MinioService.get_file(document_key)
        return current_app.response_class(response=response.data, status=response.status, mimetype="application/pdf")
    except Exception as e:
        current_app.logger.error(f"Error getting file {document_key}: {e}")
        return jsonify(message=f"Error getting file {document_key}."), HTTPStatus.INTERNAL_SERVER_ERROR
