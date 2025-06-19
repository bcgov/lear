from legal_api.models import Document, Business
from legal_api.exceptions import BusinessException
import requests
from flask import current_app, jsonify
from http import HTTPStatus

class DocumentService:

    def __init__(self):
        self.url = current_app.config.get('DOCUMENT_SVC_URL')
        self.product_code = current_app.config.get('DOCUMENT_PRODUCT_CODE')
        self.api_key = current_app.config.get('DOCUMENT_API_KEY')

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

    def create_document(self, business_identifier: str, filing_identifier: int, report_type: str, account_id: int, binary_or_url):
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
        if response.status_code != HTTPStatus.CREATED:
            return jsonify(message=str(response.content)), response.status_code
        new_document = Document(
            business_id=Business.find_by_identifier(business_identifier).id,
            filing_id=filing_identifier,
            type=report_type,
            file_key=response.content['identifier'],
            file_name=f'{business_identifier}_{filing_identifier}_{report_type}.pdf',
        )
        new_document.save()
        return response.content, response.status_code

    def get_document(self, business_identifier: str, filing_identifier: int, report_type: str, account_id: int):
        """
        Get a document from the document service.
        business_identifier: The business identifier.
        filing_identifier: The filing identifier.
        report_type: The report type.
        account_id: The account id.
        return: The document url (or binary).
        """
        document = self.has_document(business_identifier, filing_identifier, report_type)
        if document is False:
            raise BusinessException('Document not found', HTTPStatus.NOT_FOUND)
        
        headers = {
            'X-Api-Key': self.api_key,
            'Account-Id': account_id,
            'Content-Type': 'application/pdf'
        }
        get_url = f'{self.url}/application-reports/{self.product_code}/{document.file_key}'
        response = requests.get(url=get_url, headers=headers)
        if response.status_code != HTTPStatus.OK:
            return jsonify(message=str(response.content)), response.status_code
        return response.content, response.status_code

    def get_document(self, business_identifier: str, filing_identifier: int, report_type: str, account_id: int, file_key: str):
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
        get_url = f'{self.url}/application-reports/{self.product_code}/{file_key}'
        response = requests.get(url=get_url, headers=headers)
        if response.status_code != HTTPStatus.OK:
            return jsonify(message=str(response.content)), response.status_code
        
        self.create_document(business_identifier, filing_identifier, report_type, account_id, response.content)

        return response.content, response.status_code