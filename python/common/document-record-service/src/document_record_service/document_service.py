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

from datetime import datetime, timezone
from typing import Optional

import PyPDF2
import requests
from flask import current_app

from document_record_service.constants import DocumentTypes
from document_record_service.utils import RequestInfo


class DocumentRecordService:
    """Service for interacting with the Document Record Service (DRS)."""


    def __init__(self):
        self.headers = {
            "x-apikey": current_app.config.get("DOC_API_KEY", ""),
            "Account-Id": current_app.config.get("DOC_API_ACCOUNT_ID", ""),
        }
        self.base_url = current_app.config.get("DOC_API_URL", "")

    def _now_iso_utc(self):
        dt = datetime.now(timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    def post_document(self, request_info: RequestInfo, file: bytes = None, has_file: bool = True) -> dict:
        """Upload a document to the Document Record Service (DRS).

        Args:
            request_info (RequestInfo): Object containing document request metadata.
            file (bytes, optional): Byte content of the PDF file. Defaults to None.
            has_file (bool, optional): Whether the file is expected. Defaults to True.

        Returns:
            dict: JSON response from DRS or error message.
        """
        if has_file and file == None:
            current_app.logger.info("No file found in request.")
            return {"data": "File not provided"}
        request_info.consumer_filedate = self._now_iso_utc()
        url = f'{current_app.config.get("DOC_API_URL", "")}/documents/{request_info.document_class}/{request_info.document_type}'
        url += f"?{request_info.url_params}"
        try:
            response_body = requests.post(
                url,
                data=file,
                headers={
                    **self.headers,
                    "Content-Type": "application/pdf",
                },
            ).json()
            current_app.logger.info(f"Upload file to document record service {response_body}")

            return response_body

        except Exception as e:
            current_app.logger.info(f"Error on uploading document {e}")
            return {}

    def update_document(self, request_info: RequestInfo) -> dict:
        """Update the metadata of an existing document in the DRS.

        Args:
            request_info (RequestInfo): Object containing updated document request metadata.

        Returns:
            dict: JSON response or error details.
        """
        url = f"{self.base_url}/documents/{request_info.document_service_id}"

        try:

            request_info.consumer_filedate = self._now_iso_utc()
            response = requests.patch(
                url,
                json=request_info.json,
                headers=self.headers,
            )
            
            response.raise_for_status()

            return response.json()
        except requests.exceptions.RequestException as error:
            current_app.logger.error(f"Error updating document on DRS: {error}")
            return {"error": str(error), "response": error.response.json() if error.response else None}

    def delete_document(self, document_service_id: str) -> dict:
        """Soft-delete a document in the DRS by marking it as removed.

        Args:
            document_service_id (str): The unique identifier of an existing document service document.

        Returns:
            dict: JSON response from DRS or error message.
        """
        url = f"{self.base_url}/documents/{document_service_id}"

        try:
            response = requests.patch(
                url,
                json={"removed": True},
                headers=self.headers,
            ).json()
            current_app.logger.info(f"Delete document from document record service {document_service_id}")
            return response
        except Exception as e:
            current_app.logger.info(f"Error on deleting document {e}")
            return {}

    def get_document(self, request_info: RequestInfo) -> dict:
        """Retrieve a document record from DRS based on search parameters.

        Args:
            request_info (RequestInfo): Object containing search parameters.

        Returns:
            dict: JSON response with document data or empty dict on error.
        """
        url = f"{self.base_url}/searches/{request_info.document_class}"
        url += f"?{request_info.url_params}"
        try:
            response = requests.get(
                url,
                headers=self.headers,
            ).json()
            current_app.logger.info(f"Get document from document record service {request_info}")

            return response
        except Exception as e:
            current_app.logger.info(f"Error on getting a document object {e}")
            return {}

    @staticmethod
    def download_document(document_class: str, document_service_id: str) -> bytes:
        """Download the actual binary content of a document from google storage.

        Args:
            document_class (str): Class/category of the document.
            document_service_id (str): Unique ID of the document in DRS.

        Returns:
            bytes: Byte content of the document if successful, None otherwise.
        """
        response = DocumentRecordService().get_document(RequestInfo(document_class, document_service_id))
        try:
            if not (isinstance(response, list) and response):
                raise ValueError("Response is not a valid non-empty list.")
            document_url = response[0].get("documentURL", "")

            if not document_url:
                raise ValueError("Missing 'documentURL' in scanningInformation.")

            download_response = requests.get(document_url)
            download_response.raise_for_status()  # Raise for HTTP errors
            current_app.logger.info(f"Document downloaded successfully from {document_service_id}")

            return download_response.content

        except (requests.RequestException, ValueError, KeyError) as e:
            current_app.logger.info(f"Error downloading document: {e}")
            return None

    @staticmethod
    def validate_pdf(file, content_length, document_type) -> Optional[list]:
        """Validate PDF content based on file size, encryption, and page dimensions.

        Args:
            file: Uploaded file object (must have a `filename` attribute).
            content_length (int): Size of the file in bytes.
            document_type (str): Type of document to determine validation rules.

        Returns:
            list | None: List of validation errors if any, otherwise None.
        """
        msg = []
        verify_paper_size = document_type in [DocumentTypes.CNTI.value]

        try:
            pdf_reader = PyPDF2.PdfFileReader(file)
            if verify_paper_size:
                # Check that all pages in the pdf are letter size and able to be processed.
                if any(x.mediaBox.getWidth() != 612 or x.mediaBox.getHeight() != 792 for x in pdf_reader.pages):
                    msg.append(
                        {
                            "error": "Document must be set to fit onto 8.5” x 11” letter-size paper.",
                            "path": file.filename,
                        }
                    )
            if content_length > 30000000:
                msg.append({"error": "File exceeds maximum size.", "path": file.filename})

            if pdf_reader.isEncrypted:
                msg.append({"error": "File must be unencrypted.", "path": file.filename})

        except Exception as e:
            msg.append({"error": "Invalid file.", "path": file.filename})
            current_app.logger.info(e)

        if msg:
            return msg

        return None
