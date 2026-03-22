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
from typing import Optional

import requests
from flask import current_app, jsonify

from legal_api.exceptions import BusinessException
from legal_api.models import Business, Document, Filing
from legal_api.services import AccountService
from legal_api.utils.base import BaseEnum

BUSINESS_DOCS_PATH: str = "{url}/application-reports/history/{product}/{business_id}?includeDocuments=true"
GET_REPORT_PATH: str = "{url}/application-reports/{product}/{drsId}"
GET_REPORT_CERTIFIED_PATH: str = "{url}/application-reports/{product}/{drsId}?certifiedCopy=true"
POST_REPORT_PATH: str = "{url}/application-reports/{product}/{bus_id}/{filing_id}/{report_type}"
POST_REPORT_PARAMS: str = "?consumerFilingDate={filing_date}&consumerFilename={filename}"
GET_DOCUMENT_PATH: str = "{url}/searches/{document_class}?documentServiceId={drs_id}"
FILING_DOCS_PATH: str = "{url}/application-reports/events/{product}/{business_id}/{filing_id}?includeDocuments=true"
DRS_REPORT_PARAMS: str = "?reportType={report_type}&drsId={drs_id}"
DRS_DOCUMENT_PARAMS: str = "?documentClass={document_class}&drsId={drs_id}"
# Used for audit trail and db queries.
BUSINESS_API_ACCOUNT_ID: str = "business-api"
FILING_DOCUMENTS = {
    "certifiedRules": {
        "documentType": "COOP_RULES",
        "documentClass": "COOP"
    },
    "certifiedMemorandum": {
        "documentType": "COOP_MEMORANDUM",
        "documentClass": "COOP"
    },
    "affidavit": {
        "documentType": "CORP_AFFIDAVIT",  # "COSD",
        "documentClass": "CORP"
    },
    "uploadedCourtOrder": {
        "documentType": "CRT",
        "documentClass": "CORP"
    }
}
STATIC_DOCUMENTS = {
    "Unlimited Liability Corporation Information": {
        "documentType": "DIRECTOR_AFFIDAVIT",
        "documentClass": "CORP"
    }
}
APP_JSON = "application/json"
APP_PDF = "application/pdf"
DOC_PATH = "/documents"
BEARER = "Bearer "


class ReportTypes(BaseEnum):
    """Render an Enum of the document service report types."""

    CERT = "CERT"
    FILING = "FILING"
    NOA = "NOA"
    RECEIPT = "RECEIPT"


class DocumentService:
    """Service to create document records in document service api."""

    def __init__(self):
        """Initialize the document service."""
        self.url = current_app.config.get("DOCUMENT_SVC_URL")
        self.product_code = current_app.config.get("DOCUMENT_PRODUCT_CODE")
        self.api_key = current_app.config.get("DOCUMENT_API_KEY")

    def get_content(self, response):
        """Get the content of the response useful for test methods."""
        c = response.content
        try:
            c = c.decode()
            c = json.loads(c)
        except Exception:
            pass
        return c

    # pylint: disable=too-many-arguments
    def create_document_record(
      self,
      business_id: int,
      filing_id: int,
      report_type: str,
      file_key: str,
      file_name: str):
        """Create a document record in the document table."""
        new_document = Document(
            business_id=business_id,
            filing_id=filing_id,
            type=report_type,
            file_key=file_key,
            file_name=file_name,
        )
        new_document.save()

    def has_document(
      self,
      business_identifier: str,
      filing_identifier: int,
      report_type: str):
        """
        Check if a document exists in the document service.

        business_identifier: The business identifier.
        filing_identifier: The filing identifier.
        report_type: The report type.
        account_id: The account id.
        return: True if the document exists, False otherwise.
        """
        business_id = Business.find_by_identifier(business_identifier).id
        document = Document.find_one_by(
          business_id,
          filing_identifier,
          report_type)
        return document if document else False

    # pylint: disable=too-many-arguments
    def create_document(
      self,
      business_identifier: str,
      filing_identifier: int,
      report_type: str,
      account_id: str,
      binary_or_url):
        """
        Create a document in the document service.

        business_identifier: The business identifier.
        filing_identifier: The filing identifier.
        report_type: The report type.
        account_id: The account id.
        binary_or_url: The binary (pdf) or url of the document.
        """
        if self.has_document(business_identifier, filing_identifier, report_type):
            raise BusinessException("Document already exists", HTTPStatus.CONFLICT)
        headers = self._get_request_headers(account_id)
        filename: str = f"{business_identifier}_{filing_identifier}_{report_type}.pdf"
        url: str = self.url.replace(DOC_PATH, "")
        post_url = (f"{url}/application-reports/"
                    f"{self.product_code}/{business_identifier}/"
                    f"{filing_identifier}/{report_type}?consumerFiliename={filename}")
        # Include filing date if available.
        response = requests.post(url=post_url, headers=headers, data=binary_or_url)
        content = self.get_content(response)
        if response.status_code != HTTPStatus.CREATED:
            return jsonify(message=str(content)), response.status_code
        self.create_document_record(
          Business.find_by_identifier(business_identifier).id,
          filing_identifier, report_type, content["identifier"],
          filename
        )
        return content, response.status_code

    # pylint: disable=too-many-arguments
    def get_document(
      self,
      business_identifier: str,
      filing_identifier: int,
      report_type: str,
      account_id: str,
      file_key: Optional[str] = None):
        """
        Get a document from the document service.

        business_identifier: The business identifier.
        filing_identifier: The filing identifier.
        report_type: The report type.
        account_id: The account id.
        return: The document url (or binary).
        """
        headers = self._get_request_headers(account_id)
        url: str = self.url.replace(DOC_PATH, "")
        get_url = ""
        if file_key is not None:
            get_url = f"{url}/application-reports/{self.product_code}/{file_key}"
        else:
            document = self.has_document(business_identifier, filing_identifier, report_type)
            if document is False:
                raise BusinessException("Document not found", HTTPStatus.NOT_FOUND)
            get_url = f"{url}/application-reports/{self.product_code}/{document.file_key}"

        if get_url != "":
            response = requests.get(url=get_url, headers=headers)
            content = self.get_content(response)
            if response.status_code != HTTPStatus.OK:
                return jsonify(message=str(content)), response.status_code
            return content, response.status_code
        return jsonify(message="Document not found"), HTTPStatus.NOT_FOUND

    def get_documents_by_business_id(self, business_identifier: str) -> list:
        """
        Get all available document information from the DRS by business identifier.

        business_identifier: The business identifier.
        return: The list of available filing reports and documents for the business, or [] if there is a problem.
        """
        try:
            if not business_identifier:
                return []
            headers = self._get_request_headers(BUSINESS_API_ACCOUNT_ID)
            url: str = self.url.replace(DOC_PATH, "")
            get_url = BUSINESS_DOCS_PATH.format(url=url, product=self.product_code, business_id=business_identifier)
            response = requests.get(url=get_url, headers=headers)
            content = self.get_content(response)
            if response.status_code not in (HTTPStatus.OK, HTTPStatus.NOT_FOUND):
                current_app.logger.error(f"DRS call {get_url} failed status={response.status_code}: {content}")
            return content if response.status_code == HTTPStatus.OK else []
        except Exception:
            return []

    def get_documents_by_filing_id(self, business_identifier: str, filing_identifier: str) -> list:
        """
        Get all available document information from the DRS by filing identifier.

        business_identifier: The business identifier.
        filing_identifier: The filing identifier.
        return: The list of available filing reports and documents for the filing, or [] if there is a problem or none.
        """
        try:
            if not business_identifier or not filing_identifier:
                return []
            headers = self._get_request_headers(BUSINESS_API_ACCOUNT_ID)
            url: str = self.url.replace(DOC_PATH, "")
            get_url = FILING_DOCS_PATH.format(
                url=url,
                product=self.product_code,
                business_id=business_identifier,
                filing_id=filing_identifier
            )
            response = requests.get(url=get_url, headers=headers)
            content = self.get_content(response)
            if response.status_code not in (HTTPStatus.OK, HTTPStatus.NOT_FOUND):
                current_app.logger.error(f"DRS call {get_url} failed status={response.status_code}: {content}")
            return content if response.status_code == HTTPStatus.OK else []
        except Exception:
            return []

    def update_document_list(self, drs_docs: list, document_list: list) -> list:
        """
        Update document_list urls with DRS information if a filing document maps to a DRS output or document.

        drs_docs: The DRS reports/documents for the filing identifier.
        document_list: The business list of reports/documents for the filing.
        return: The updated list of filing reports and documents for the filing.
        """
        if not drs_docs or not document_list or not document_list.get("documents"):
            return document_list
        doc_list = document_list.get("documents")
        for doc in drs_docs:
            if doc.get("reportType") and doc.get("reportType") == "RECEIPT" and doc_list.get("receipt"):
                query_params: str = DRS_REPORT_PARAMS.format(report_type="RECEIPT", drs_id=doc.get("identifier"))
                doc_list["receipt"] = doc_list["receipt"] + query_params
            elif doc.get("reportType") and doc.get("reportType") == "NOA" and doc_list.get("noticeOfArticles"):
                query_params: str = DRS_REPORT_PARAMS.format(report_type="NOA", drs_id=doc.get("identifier"))
                doc_list["noticeOfArticles"] = doc_list["noticeOfArticles"] + query_params
            elif doc.get("reportType") and doc.get("reportType") == "FILING" and doc_list.get("legalFilings"):
                query_params: str = DRS_REPORT_PARAMS.format(report_type="FILING", drs_id=doc.get("identifier"))
                filing = doc_list["legalFilings"][0]
                filing_key = next(iter(filing.keys()))
                filing[filing_key] = filing[filing_key] + query_params
            elif doc.get("reportType") and doc.get("reportType") == "CERT":
                query_params: str = DRS_REPORT_PARAMS.format(report_type="CERT", drs_id=doc.get("identifier"))
                for key in doc_list:
                    if str(key).find("certificate") > -1:
                        doc_list[key] = doc_list[key] + query_params
                        break
            elif doc.get("documentClass"):
                doc_list = self._update_static_document(doc, doc_list)
        return document_list

    def update_filing_documents(self, drs_docs: list, filing_docs: list, filing: Filing) -> list:  # noqa: PLR0912
        """
        Get outputs and documents for a ledger filing, adding DRS information if available by mapping on the filing ID.

        drs_docs: The DRS reports/documents for the business identifier.
        filing_docs: The filing list of reports/documents.
        return: The updated list of filing reports and documents for the filing.
        """
        doc_list =  filing_docs.get("documents") if filing_docs else None
        if not filing_docs or not doc_list:
            return []
        if not drs_docs or not filing or filing.paper_only:
            return doc_list
        drs_filing_id: int = filing.id
        # If DRS reports/documents exist add the DRS download info to the document URLs.
        if filing and filing.source == filing.Source.COLIN.value:
            meta_data = filing.meta_data
            if meta_data and meta_data.get("colinFilingInfo") and meta_data["colinFilingInfo"].get("eventId"):
                drs_filing_id = meta_data["colinFilingInfo"].get("eventId")

        for doc in drs_docs:
            if doc.get("eventIdentifier", 0) == drs_filing_id:
                if doc.get("reportType") and doc.get("reportType") == "RECEIPT" and doc_list.get("receipt"):
                    query_params: str = DRS_REPORT_PARAMS.format(report_type="RECEIPT", drs_id=doc.get("identifier"))
                    doc_list["receipt"] = doc_list["receipt"] + query_params
                elif doc.get("reportType") and doc.get("reportType") == "NOA" and doc_list.get("noticeOfArticles"):
                    query_params: str = DRS_REPORT_PARAMS.format(report_type="NOA", drs_id=doc.get("identifier"))
                    doc_list["noticeOfArticles"] = doc_list["noticeOfArticles"] + query_params
                elif doc.get("reportType") and doc.get("reportType") == "FILING" and doc_list.get("legalFilings"):
                    query_params: str = DRS_REPORT_PARAMS.format(report_type="FILING", drs_id=doc.get("identifier"))
                    legal_filing = doc_list["legalFilings"][0]
                    filing_key = next(iter(legal_filing.keys()))
                    legal_filing[filing_key] = legal_filing[filing_key] + query_params
                elif doc.get("reportType") and doc.get("reportType") == "CERT":
                    query_params: str = DRS_REPORT_PARAMS.format(report_type="CERT", drs_id=doc.get("identifier"))
                    for key in doc_list:
                        if str(key).find("certificate") > -1:
                            doc_list[key] = doc_list[key] + query_params
                            break
                elif doc.get("documentClass"):
                    doc_list = self._update_static_document(doc, doc_list)
        return doc_list

    def get_filing_report(self, drs_id: str, report_type: str):
        """
        Get a filing report document from the document service by unique DRS identifier.

        drs_id: The unique DRS identifier for the requested document.
        report_type: The report type: request a certified copy for NOA and FILING report types.
        return: The document binary data.
        """
        headers = self._get_request_headers(BUSINESS_API_ACCOUNT_ID, APP_PDF)
        url: str = self.url.replace(DOC_PATH, "")
        get_url = GET_REPORT_PATH
        if report_type in (ReportTypes.FILING.value, ReportTypes.NOA.value):
            get_url = GET_REPORT_CERTIFIED_PATH
        get_url = get_url.format(url=url, product=self.product_code, drsId=drs_id)
        response = requests.get(url=get_url, headers=headers)
        if response.status_code not in (HTTPStatus.OK, HTTPStatus.NOT_FOUND):
            current_app.logger.error(f"DRS call {get_url} failed status={response.status_code}: {response.content}")
        return response

    def get_filing_report_by_filing_id(self, business_identifier: str, filing_identifier: int, report_type: str):
        """
        Try to get a filing report document from the DRS by filing identifier and report type.

        business_identifier: The business identifier.
        filing_identifier: The filing identifier.
        report_type: The report type.
        return: The report binary data status is OK.
        """
        if not business_identifier or not filing_identifier or not report_type:
            return None, HTTPStatus.NOT_FOUND
        headers = self._get_request_headers(BUSINESS_API_ACCOUNT_ID)
        url: str = self.url.replace(DOC_PATH, "")
        get_url = FILING_DOCS_PATH.format(
            url=url,
            product=self.product_code,
            business_id=business_identifier,
            filing_id=filing_identifier
        )
        response = requests.get(url=get_url, headers=headers)
        if response.status_code != HTTPStatus.OK:
            return response.content, response.status_code
        response_json = json.loads(response.content)
        drs_id = None
        for doc in response_json:
            if doc.get("reportType") == report_type and doc.get("eventIdentifier") == filing_identifier:
                drs_id = doc.get("identifier")
                break
        if drs_id:
            response = self.get_filing_report(drs_id, report_type)
            return response.content, response.status_code
        return None, HTTPStatus.NOT_FOUND

    def get_filing_document(self, drs_id: str, doc_class: str):
        """
        Get a filing document from the document service by unique DRS identifier.

        drs_id: The unique DRS identifier for the requested document.
        document_class: The DRS document class for the business to filter on.
        return: The document binary data.
        """
        headers = self._get_request_headers(BUSINESS_API_ACCOUNT_ID, APP_PDF)
        url: str = self.url.replace(DOC_PATH, "")
        get_url = GET_DOCUMENT_PATH.format(url=url, document_class=doc_class, drs_id=drs_id)
        response = requests.get(url=get_url, headers=headers)
        if response.status_code not in (HTTPStatus.OK, HTTPStatus.NOT_FOUND):
            current_app.logger.error(f"DRS call {get_url} failed status={response.status_code}: {response.content}")
        return response

    def create_filing_report(
        self,
        business_identifier: str,
        filing: Filing,
        report_meta: dict,
        report_response
    ):
        """
        Create a DRS application report record with a report service report.

        business_identifier: Required - associates the report with the business.
        filing: Required - contains the filing ID and filing date.
        report_type: Required - the DRS report type.
        report_response: Required - contains the report binary data
        return: The DRS API response.
        """
        if not business_identifier or not filing or not report_meta or not report_meta.get("reportType"):
            return report_response
        headers = self._get_request_headers(BUSINESS_API_ACCOUNT_ID)
        url: str = self.url.replace(DOC_PATH, "")
        report_type: str = report_meta.get("reportType")
        filename: str = filing.filing_type
        if report_meta.get("fileName"):
            filename = report_meta.get("fileName")
        elif report_meta.get("default") and report_meta["default"].get("fileName"):
            filename: str = report_meta["default"].get("fileName")
        filename += ".pdf"
        filing_date: str = filing.effective_date.isoformat()[:10]
        post_url = POST_REPORT_PATH.format(
            url=url,
            product=self.product_code,
            bus_id=business_identifier,
            filing_id=filing.id,
            report_type=report_type
        )
        post_url += POST_REPORT_PARAMS.format(filing_date=filing_date, filename=filename)
        response = requests.post(url=post_url, headers=headers, data=report_response.content)
        if response.status_code not in (HTTPStatus.OK, HTTPStatus.CREATED):
            current_app.logger.error(f"DRS call {post_url} failed status={response.status_code}: {response.content}")
            return report_response
        if report_type == ReportTypes.CERT.value:
            return report_response
        # Get the certified copy of the NOA and FILING report types.
        response_json = json.loads(response.content)
        if response_json and response_json.get("identifier"):
            response2 = self.get_filing_report(response_json.get("identifier"), report_type)
            if response2.status_code == HTTPStatus.OK:
                return response2
        return report_response

    def _update_static_document(self, doc: dict, doc_list: list) -> list:
        """
        Update static document urls in the document_list if a DRS match is found.

        docs: The DRS document information to match on.
        doc_list: The business list of reports/documents for the filing.
        return: The updated list of static documents for the filing.
        """
        query_params: str = DRS_DOCUMENT_PARAMS.format(
            document_class=doc.get("documentClass"),
            drs_id=doc.get("identifier")
        )
        for key in doc_list:
            if key == "staticDocuments":
                for static_doc in doc_list.get("staticDocuments"):
                    name: str = static_doc.get("name")
                    if (name and name == doc.get("name")) or (
                            name and STATIC_DOCUMENTS.get(name) and
                            doc.get("documentClass") == STATIC_DOCUMENTS[name].get("documentClass") and
                            doc.get("documentType") == STATIC_DOCUMENTS[name].get("documentType")
                        ):
                        static_doc["url"] = static_doc["url"] + query_params
                        break
            elif (
                FILING_DOCUMENTS.get(key) and
                doc.get("documentClass") == FILING_DOCUMENTS[key].get("documentClass") and
                doc.get("documentType") == FILING_DOCUMENTS[key].get("documentType")
            ):
                doc_list[key] = doc_list[key] + query_params
                break
        return doc_list


    def _get_request_headers(self, account_id: str, accept_mime_type = None) -> dict:
        """
        Get request headers for the DRS api call.

        account_id: The account use if not the default.
        return: The request headers.
        """
        token = AccountService.get_bearer_token()
        headers = {
            "x-apikey": self.api_key,
            "Account-Id": account_id if account_id else BUSINESS_API_ACCOUNT_ID,
            "Content-Type": APP_PDF,
            "Authorization": BEARER + token
        }
        if accept_mime_type:
            headers["Accept"] = accept_mime_type
        return headers
