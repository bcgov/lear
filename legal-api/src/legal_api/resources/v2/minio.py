from flask import Blueprint, request, jsonify, current_app
from flask_cors import cross_origin
from http import HTTPStatus
from legal_api.services.minio import MinioService
from minio.error import S3Error
from legal_api.utils.auth import jwt
from legal_api.models import Filing

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
    except S3Error as e:
        current_app.logger.error(f'Error deleting file {document_key}: {e}')
        return jsonify(
            message=f'Error deleting file {document_key}.'
        ), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        current_app.logger.error(f'Unexpected error: {e}')
        return jsonify(
            message='Unexpected error occurred.'
        ), HTTPStatus.INTERNAL_SERVER_ERROR
