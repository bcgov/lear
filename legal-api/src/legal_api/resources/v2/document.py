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

from legal_api.models import Filing
from legal_api.services.minio import MinioService
from legal_api.utils.auth import jwt


bp = Blueprint('minio', __name__, url_prefix='/api/v2/documents')


def is_complete_filing(filing_id: int) -> bool:
    """Check if the filing is complete."""
    filing = Filing.query.get(filing_id)
    return filing and filing.status == 'COMPLETED'


@bp.route('/<string:document_key>', methods=['DELETE', 'OPTIONS'])
@cross_origin(origin='*')
@jwt.requires_auth
def delete_minio_document(document_key):
    """Delete Minio document based on the provided file key and filing ID???."""
    try:

        MinioService.delete_file(document_key)
        return jsonify({'message': f'File {document_key} deleted successfully.'}), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f'Error deleting file {document_key}: {e}')
        return jsonify(
            message=f'Error deleting file {document_key}.'
        ), HTTPStatus.INTERNAL_SERVER_ERROR
