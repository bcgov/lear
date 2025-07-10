from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest
import requests

from document_record_service import DocumentRecordService
from document_record_service.utils import RequestInfo

CONSUMER_DOCUMENT_ID = '1234567890'
CONSUMER_FILE_NAME = 'example_file.pdf'
TEMP_REG = 'TaA1aAAaaA'
CONSUMER_IDENTIFIER = 'BC1234567'
CONSUMER_REFERENCE_ID = '123456'
DOCUMENT_CLASS = 'CORP'
DOCUMENT_TYPE = 'CNTI'
DOCUMENT_SERVICE_ID = 'DS0000111111'
INVALID_DOC_SERVICE_ID = '4bc18c4c-18fa-40a2-8fe0-01e62f7e8d23.pdf'
DOCUMENT_TYPE_DESCRIPTION = 'Continuation In'
DOCUMENT_URL = 'https://example.com/storage'
FILE_DATA = b'%PDF-1.4...'

@pytest.mark.parametrize('test_name, has_file', [
    ('post_document_with_file_sucess', True),
    ('post_document_fail', True),
    ('post_document_no_file_sucess', False),
])
def test_post_class_document(app_ctx, test_name, has_file):
    POST_SUCCESS_RESPONSE = {
        'consumerDocumentId': CONSUMER_DOCUMENT_ID,
        'consumerFilename': CONSUMER_FILE_NAME,
        'consumerIdentifier': CONSUMER_IDENTIFIER,
        'consumerReferenceId': CONSUMER_REFERENCE_ID,
        'documentClass': DOCUMENT_CLASS,
        'documentServiceId': DOCUMENT_SERVICE_ID,
        'documentType': DOCUMENT_TYPE,
        'documentTypeDescription': DOCUMENT_TYPE_DESCRIPTION
    }

    POST_FAILED_RESPONSE = {'data': 'file not provided'}
    service = DocumentRecordService()
    file_data = FILE_DATA if has_file else None
    request_info = RequestInfo(
        consumer_doc_id=CONSUMER_DOCUMENT_ID,
        consumer_filename=CONSUMER_FILE_NAME,
        consumer_identifier=CONSUMER_IDENTIFIER,
        consumer_reference_id=CONSUMER_REFERENCE_ID,
        document_class=DOCUMENT_CLASS,
        document_type=DOCUMENT_TYPE,
        document_service_id=DOCUMENT_SERVICE_ID,
    )
    mock_response = MagicMock()
    mock_response.status_code = HTTPStatus.CREATED
    mock_response.json.return_value = {}

    mock_response_map = {
        'post_document_with_file_sucess': POST_SUCCESS_RESPONSE,
        'post_document_fail': POST_FAILED_RESPONSE,
        'post_document_no_file_sucess': dict(POST_SUCCESS_RESPONSE, documentURL=DOCUMENT_URL),
    }
    expected_return_value = mock_response_map[test_name]
    with patch.object(
        DocumentRecordService, 'post_class_document', return_value = expected_return_value
    ):
        with patch.object(requests, 'post', mock_response):
            if test_name == 'post_document_with_file_sucess':
                document_object = service.post_class_document(request_info, file_data)
            
                assert document_object == POST_SUCCESS_RESPONSE
            if test_name == 'post_document_no_file_sucess':
                document_object = service.post_class_document(request_info, has_file=False)
                assert document_object['documentURL'] == DOCUMENT_URL
            if test_name == 'post_document_fail':
                post_response = service.post_class_document(request_info, has_file=False)
                assert post_response == POST_FAILED_RESPONSE


@pytest.mark.parametrize('test_name, document_service_id', [
    ('update_document_success', DOCUMENT_SERVICE_ID),
    ('update_document_fail', INVALID_DOC_SERVICE_ID)
])
def test_update_document(app_ctx, test_name, document_service_id):
    UPDATE_SUCCESS_RESPONSE = {
        'consumerDocumentId': CONSUMER_DOCUMENT_ID,
        'consumerFilename': CONSUMER_FILE_NAME,
        'consumerIdentifier': CONSUMER_IDENTIFIER,
        'consumerReferenceId': CONSUMER_REFERENCE_ID,
        'documentClass': DOCUMENT_CLASS,
        'documentServiceId': DOCUMENT_SERVICE_ID,
        'documentType': DOCUMENT_TYPE,
        'documentTypeDescription': DOCUMENT_TYPE_DESCRIPTION
    }
    UPDATE_FAILED_RESPONSE = {'error': 'Document service id is invalid.'}
    service = DocumentRecordService()
    request_info = RequestInfo(
        document_service_id=document_service_id,
        consumer_identifier=CONSUMER_IDENTIFIER,
        consumer_reference_id=CONSUMER_REFERENCE_ID,
    )
    mock_response = MagicMock()
    mock_response.status_code = HTTPStatus.OK
    mock_response.json.return_value = {}
    mock_response_map = {
        'update_document_success': UPDATE_SUCCESS_RESPONSE,
        'update_document_fail': UPDATE_FAILED_RESPONSE
    }
    expected_return_value = mock_response_map[test_name]

    with patch.object(
        DocumentRecordService, 'update_document', return_value = expected_return_value
    ):
        with patch.object(requests, 'patch', mock_response):
            response = service.update_document(request_info)
            if test_name == 'update_document_success':
                assert response == UPDATE_SUCCESS_RESPONSE
            else:
                assert response == UPDATE_FAILED_RESPONSE

@pytest.mark.parametrize('test_name, document_service_id', [
    ('delete_document_success', DOCUMENT_SERVICE_ID),
    ('delete_document_fail', INVALID_DOC_SERVICE_ID)
])
def test_delete_document(test_name, document_service_id):
    DELETE_SUCCESS_RESPONSE = {"data": "Document is deleted successfully!"}
    DELETE_FAILED_RESPONSE = {'error': 'Document service id is invalid.'}
    service = DocumentRecordService()

    mock_response = MagicMock()
    mock_response.status_code = HTTPStatus.OK
    mock_response.json.return_value = {}
    mock_response_map = {
        'delete_document_success': DELETE_SUCCESS_RESPONSE,
        'delete_document_fail': DELETE_FAILED_RESPONSE
    }
    expected_return_value = mock_response_map[test_name]

    with patch.object(
        DocumentRecordService, 'delete_document', return_value = expected_return_value
    ):
        with patch.object(requests, 'patch', mock_response):
            response = service.delete_document(document_service_id)
            if test_name == 'delete_document_success':
                assert response == DELETE_SUCCESS_RESPONSE
            else:
                assert response == DELETE_FAILED_RESPONSE

@pytest.mark.parametrize('test_name, document_class', [
    ('get_document_success', DOCUMENT_SERVICE_ID),
    ('get_document_fail', INVALID_DOC_SERVICE_ID)
])
def test_get_document(test_name, document_class):
    GET_SUCCESS_RESPONSE = {
        'consumerDocumentId': CONSUMER_DOCUMENT_ID,
        'consumerFilename': CONSUMER_FILE_NAME,
        'consumerIdentifier': CONSUMER_IDENTIFIER,
        'consumerReferenceId': CONSUMER_REFERENCE_ID,
        'documentClass': DOCUMENT_CLASS,
        'documentServiceId': DOCUMENT_SERVICE_ID,
        'documentType': DOCUMENT_TYPE,
        'documentTypeDescription': DOCUMENT_TYPE_DESCRIPTION
    }
    GET_FAILED_RESPONSE = {"error": "Document Class is required"}
    service = DocumentRecordService()
    request_info = RequestInfo(
        document_class=document_class,
        consumer_doc_id=CONSUMER_DOCUMENT_ID
    )
    mock_response = MagicMock()
    mock_response.status_code = HTTPStatus.OK
    mock_response.json.return_value = {}
    mock_response_map = {
        'get_document_success': GET_SUCCESS_RESPONSE,
        'get_document_fail': GET_FAILED_RESPONSE
    }
    expected_return_value = mock_response_map[test_name]

    with patch.object(
        DocumentRecordService, 'get_document', return_value = expected_return_value
    ):
        with patch.object(requests, 'get', mock_response):
            response = service.get_document(request_info)
            if test_name == 'get_document_success':
                assert response == GET_SUCCESS_RESPONSE
            else:
                assert response == GET_FAILED_RESPONSE


@pytest.mark.parametrize('test_name, document_service_id', [
    ('download_document_success', DOCUMENT_SERVICE_ID),
    ('download_document_fail', INVALID_DOC_SERVICE_ID)
])
def test_download_document(test_name, document_service_id):
    DOWNLOAD_SUCCESS_RESPONSE = FILE_DATA
    DOWNLOAD_FAILED_RESPONSE = {'error': 'Document service id is invalid.'}
    service = DocumentRecordService()

    mock_response = MagicMock()
    mock_response.status_code = HTTPStatus.OK
    mock_response.json.return_value = {}
    mock_response_map = {
        'download_document_success': DOWNLOAD_SUCCESS_RESPONSE,
        'download_document_fail': DOWNLOAD_FAILED_RESPONSE
    }
    expected_return_value = mock_response_map[test_name]

    with patch.object(
        DocumentRecordService, 'download_document', return_value = expected_return_value
    ):
        with patch.object(requests, 'get', mock_response):
            response = service.download_document(DOCUMENT_CLASS, document_service_id)
            if test_name == 'download_document_success':
                assert response == DOWNLOAD_SUCCESS_RESPONSE
            else:
                assert response == DOWNLOAD_FAILED_RESPONSE