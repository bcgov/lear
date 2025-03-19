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
"""This module is a wrapper for Document Record Service."""

import base64
from typing import Optional
import requests
from flask import current_app, request
from flask_babel import _
import PyPDF2

from legal_api.constants import DocumentTypeEnum

class DocumentRecordService:
    """Document Storage class."""


    @staticmethod
    def upload_document(document_class: str, document_type: str) -> dict:
        """Upload document to Docuemtn Record Service."""
        query_params = request.args.to_dict()
        file = request.data.get('file')
         # Ensure file exists
        if not file:
            current_app.logger.debug('No file found in request.')
            return {'data': 'File not provided'}
        current_app.logger.debug(f'Upload file to document record service {file.filename}')
        DOC_API_URL = current_app.config.get('DOC_API_URL', '') # pylint: disable=invalid-name
        url = f'{DOC_API_URL}/documents/{document_class}/{document_type}'

        # Validate file size and encryption status before submitting to DRS.
        validation_error = DocumentRecordService.validate_pdf(file, request.content_length, document_type)
        if validation_error:
            return {
                'error': validation_error
            }

        try:
             # Read and encode the file content as base64
            file_content = file.read()
            file_base64 = base64.b64encode(file_content).decode('utf-8')

            response_body = requests.post(
                url,
                params=query_params,
                json={
                    'filename': file.filename,
                    'content': file_base64,
                    'content_type': file.content_type,
                },
                headers={
                    'x-apikey': current_app.config.get('DOC_API_KEY', ''),
                    'Account-Id': current_app.config.get('DOC_API_ACCOUNT_ID', ''),
                    'Content-Type': file.content_type
                }
            ).json()

            current_app.logger.debug(f'Upload file to document record service {response_body}')
            return {
                'documentServiceId': response_body['documentServiceId'],
                'consumerDocumentId': response_body['consumerDocumentId'],
                'consumerFilename': response_body['consumerFilename']
            }
        except Exception as e:
            current_app.logger.debug(f"Error on uploading document {e}")
            return {}

    @staticmethod
    def update_document(document: bytes, document_service_id: str, document_name: str) -> dict:
        """Update a document on Document Record Service (DRS)."""

        DOC_API_URL = current_app.config.get('DOC_API_URL', '')
        url = f"{DOC_API_URL}/documents/{document_service_id}?consumerFilename={document_name}"

        headers = {
            'x-apikey': current_app.config.get('DOC_API_KEY', ''),
            'Account-Id': current_app.config.get('DOC_API_ACCOUNT_ID', ''),
            'Content-Type': 'application/pdf'
        }

        try:
            response = requests.put(url, data=document, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as error:
            current_app.logger.error(f"Error updating document on DRS: {error}")
            return {"error": str(error), "response": error.response.json() if error.response else None}

    @staticmethod
    def delete_document(document_service_id: str) -> dict:
        """Delete document from Document Record Service."""
        DOC_API_URL = current_app.config.get('DOC_API_URL', '') # pylint: disable=invalid-name
        url = f'{DOC_API_URL}/documents/{document_service_id}'

        try:
            response = requests.patch(
                url, json={ 'removed': True },
                headers={
                    'x-apikey': current_app.config.get('DOC_API_KEY', ''),
                    'Account-Id': current_app.config.get('DOC_API_ACCOUNT_ID', ''),
                }
            ).json()
            current_app.logger.debug(f'Delete document from document record service {response}')
            return response
        except Exception as e:
            current_app.logger.debug(f'Error on deleting document {e}')
            return {}

    @staticmethod
    def get_document(document_class: str, document_service_id: str) -> dict:
        """Get document record from Document Record Service."""
        DOC_API_URL = current_app.config.get('DOC_API_URL', '') # pylint: disable=invalid-name
        url = f'{DOC_API_URL}/searches/{document_class}?documentServiceId={document_service_id}'
        try:
            response = requests.get(
                url,
                headers={
                    'x-apikey': current_app.config.get('DOC_API_KEY', ''),
                    'Account-Id': current_app.config.get('DOC_API_ACCOUNT_ID', ''),
                }
            ).json()
            current_app.logger.debug(f'Get document from document record service {response}')
            return response[0]
        except Exception as e:
            current_app.logger.debug(f'Error on getting a document object {e}')
            return {}

    @staticmethod
    def download_document(document_class: str, document_service_id: str) -> dict:
        """Download document from Document Record Service."""
        doc_object = DocumentRecordService.get_document(document_class, document_service_id)

        response = requests.get(doc_object['documentURL']) # Download file from storage
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)

        return response

    @staticmethod
    def update_business_identifier(business_identifier: str, document_service_id: str):
        """Update business identifier up on approval."""
        DOC_API_URL = current_app.config.get('DOC_API_URL', '') # pylint: disable=invalid-name
        url = f'{DOC_API_URL}/documents/{document_service_id}'

        try:
            response = requests.patch(
                url, json={ 'consumerIdentifer': business_identifier },
                headers={
                    'x-apikey': current_app.config.get('DOC_API_KEY', ''),
                    'Account-Id': current_app.config.get('DOC_API_ACCOUNT_ID', ''),
                }
            ).json()
            current_app.logger.debug(f'Update business identifier - {business_identifier}')
            return response
        except Exception as e:
            current_app.logger.debug(f'Error on deleting document {e}')
            return {}

    @staticmethod
    def validate_pdf(file, content_length, document_type) -> Optional[list]:
        """Validate the PDF file."""
        msg = []
        verify_paper_size = document_type in [
            DocumentTypeEnum.CNTO,
            DocumentTypeEnum.DIRECTOR_AFFIDAVIT
        ]

        try:
            pdf_reader = PyPDF2.PdfFileReader(file)
            if verify_paper_size:
                # Check that all pages in the pdf are letter size and able to be processed.
                if any(x.mediaBox.getWidth() != 612 or x.mediaBox.getHeight() != 792 for x in pdf_reader.pages):
                    msg.append({'error': _('Document must be set to fit onto 8.5” x 11” letter-size paper.'),
                                'path': file.filename})                
            if content_length > 30000000:
                msg.append({'error': _('File exceeds maximum size.'), 'path': file.filename})

            if pdf_reader.isEncrypted:
                msg.append({'error': _('File must be unencrypted.'), 'path': file.filename})

        except Exception as e:
            msg.append({'error': _('Invalid file.'), 'path': file.filename})
            current_app.logger.debug(e)

        if msg:
            return msg

        return None
