# Copyright © 2025 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
# an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
"""Works with the document service api."""

import json
from http import HTTPStatus
import requests

from flask import current_app, jsonify
from legal_api.models import Document, Business
from legal_api.exceptions import BusinessException


class DocumentService:
    """Service to create document records in document service api."""

    def __init__(self):
        self.url = current_app.config.get('DOCUMENT_SVC_URL')
        self.product_code = current_app.config.get('DOCUMENT_PRODUCT_CODE')
        self.api_key = current_app.config.get('DOCUMENT_API_KEY')

    def get_content(self, response):
        """Get the content of the response useful for test methods."""
        c = response.content
        try:
            c = c.decode()
            c = json.loads(c)
        except Exception:
            pass
        return c

    def create_document_record(self, business_id: int, filing_id: int, report_type: str, file_key: str, file_name: str): #pylint: disable=too-many-arguments
        """Create a document record in the document table."""
        new_document = Document(
            business_id=business_id,
            filing_id=filing_id,
            type=report_type,
            file_key=file_key,
            file_name=file_name,
        )
        new_document.save()

    def has_document(self, business_identifier: str, filing_identifier: int, report_type: str):
        """
        Check if a document exists in the document service.
        business_identifier: The business identifier.
        filing_identifier: The filing identifier.
        report_type: The report type.
        account_id: The account id.
        return: True if the document exists, False otherwise.
        """
        business_id = Business.find_by_identifier(business_identifier).id
        document = Document.find_one_by(business_id, filing_identifier, report_type)
        return document if document else False

    def create_document(self, business_identifier: str, filing_identifier: int, report_type: str, account_id: str, binary_or_url): #pylint: disable=too-many-arguments
        """
        Create a document in the document service.
        business_identifier: The business identifier.
        filing_identifier: The filing identifier.
        report_type: The report type.
        account_id: The account id.
        binary_or_url: The binary (pdf) or url of the document.
        """
        if self.has_document(business_identifier, filing_identifier, report_type):
            raise BusinessException('Document already exists', HTTPStatus.CONFLICT)
        headers = {
            'Content-Type': 'application/json',
            'X-Api-Key': self.api_key,
            'Account-Id': account_id
        }
        post_url = f'{self.url}/application-reports/{self.product_code}/{business_identifier}/{filing_identifier}/{report_type}'
        response = requests.post(url=post_url, headers=headers, data=binary_or_url)
        content = self.get_content(response)
        if response.status_code != HTTPStatus.CREATED:
            return jsonify(message=str(content)), response.status_code
        self.create_document_record(Business.find_by_identifier(business_identifier).id, filing_identifier, report_type, content['identifier'], f'{business_identifier}_{filing_identifier}_{report_type}.pdf')
        return content, response.status_code

    def get_document(self, business_identifier: str, filing_identifier: int, report_type: str, account_id: str, file_key: str=None): #pylint: disable=too-many-arguments
        """
        Get a document from the document service.
        business_identifier: The business identifier.
        filing_identifier: The filing identifier.
        report_type: The report type.
        account_id: The account id.
        return: The document url (or binary).
        """

        headers = {
            'X-Api-Key': self.api_key,
            'Account-Id': account_id,
            'Content-Type': 'application/pdf'
        }
        get_url = ''
        if file_key is not None:
            get_url = f'{self.url}/application-reports/{self.product_code}/{file_key}'
        else:
            document = self.has_document(business_identifier, filing_identifier, report_type)
            if document is False:
                raise BusinessException('Document not found', HTTPStatus.NOT_FOUND)
            get_url = f'{self.url}/application-reports/{self.product_code}/{document.file_key}'

        if get_url != '':
            response = requests.get(url=get_url, headers=headers)
            content = self.get_content(response)
            if response.status_code != HTTPStatus.OK:
                return jsonify(message=str(content)), response.status_code
            return content, response.status_code
        return jsonify(message='Document not found'), HTTPStatus.NOT_FOUND
