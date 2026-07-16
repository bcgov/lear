# Copyright © 2026 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""This manages all of the BC Registries document record service DRS integration for client submitted documents."""
import json

import requests
from flask import current_app

from legal_api.models import Document
from legal_api.services import AccountService

POST_DOCUMENT_PATH: str = "{url}/documents/{document_class}/{document_type}"
GET_DOCUMENT_PATH: str = "{url}/searches/{document_class}?documentServiceId={drs_id}"
DELETE_DOCUMENT_PATH: str = "{url}/documents/{drs_id}"
PATCH_DOCUMENT_PATH: str = "{url}/documents/{drs_id}"
PUT_DOCUMENT_PATH: str = "{url}/documents/{drs_id}"
BUSINESS_API_ACCOUNT_ID: str = "business-api"
APP_JSON = "application/json"
APP_PDF = "application/pdf"
BEARER = "Bearer "
SERVICE_TIMEOUT = 30.0
DOC_PATH = "/documents"
# Example with all optional document properties relevant to the Business API
DOCUMENT_PROPERTIES = {
  "documentClass": "",
  "documentType": "",
  "consumerDocumentId": "",
  "consumerFilename": "",
  "consumerIdentifier": "",
  "consumerReferenceId": "",
  "consumerFilingDate": "",
  "description": "",
}


def create_document(doc_info: dict, doc_data):
    """
    Create a new document record for the doc_data document. Expected doc_info properties:
        documentClass: required
        documentType: required
        consumerFilename: optional
        consumerIdentifier: optional
        consumerReferenceId: optional
        consumerFilingDate: optional

    DRS API reference https://okagqp-test-bcregrestricted.apigee.io/docs/docserviceproxy/1/overview
        POST /doc/api/v1/documents/{documentClass}/{documentType}

    doc_info: contains the document record information associated with the document.
    doc_data: the document binary data to add to or replace in the DRS for an existing document record.
    return: The DRS response as json, including the DRS unique identifier for the document record.
    """
    doc_class = doc_info.get("documentClass")
    doc_type = doc_info.get("documentType")
    if not doc_class or not doc_type:
        current_app.logger.info("DRS create_document aborted: no document class or no document type.")
        return None
    headers = _get_request_headers(APP_PDF)
    url = build_create_doc_url(doc_class, doc_type, doc_info)
    current_app.logger.info(f"DRS create_document url={url}")
    response = requests.post(url=url, headers=headers, timeout=SERVICE_TIMEOUT, data=doc_data)
    current_app.logger.info(f"DRS post call {url} status={response.status_code}")
    if not response.ok:
        current_app.logger.error(f"DRS post call {url} response={response.content}")
    return response


def get_document(drs_id: str, doc_class: str, doc_binary: bool = True):
    """
    Get a previously saved document from the document service by unique DRS identifier and document class.

    DRS API reference https://okagqp-test-bcregrestricted.apigee.io/docs/docserviceproxy/1/overview
        GET doc/api/v1/searches/{documentClass}?documentServiceId={docServiceId}

    drs_id: The unique DRS identifier for the requested document.
    document_class: The DRS document class for the business to filter on.
    doc_binary: True if the response is the pdf binary data. False if the response is JSON with a storage download link.
    return: Response containing the document binary data or json depending on the doc_binary value.
    """
    accept = APP_JSON if not doc_binary else APP_PDF
    headers = _get_request_headers(APP_JSON, accept)
    url = GET_DOCUMENT_PATH.format(
        url=str(current_app.config.get("DOCUMENT_SVC_URL")).replace(DOC_PATH, ""),
        document_class=doc_class,
        drs_id=drs_id
    )
    current_app.logger.info(f"DRS get_document url={url}")
    response = requests.get(url=url, headers=headers, timeout=SERVICE_TIMEOUT)
    if not response.ok:
        current_app.logger.error(f"DRS call {url} failed status={response.status_code}: {response.content}")
    return response


def delete_document(bus_document: Document):
    """
    Permanently delete a document record from the document service by unique DRS identifier. Record deletion
    is only allowed with existing DRS identifiers that exist in the documents table.

    DRS API reference https://okagqp-test-bcregrestricted.apigee.io/docs/docserviceproxy/1/overview
        DELETE /doc/api/v1/documents/{docServiceId}

    bus_document: Existing documents table record containing the DRS identifier as the file_key value.
    return: The DRS response, or None if no documents record file key exists.
    """
    drs_id = get_drs_id(bus_document)
    if not drs_id:
        current_app.logger.info("DRS delete_document aborted: no document file_key.")
        return None
    headers = _get_request_headers(APP_JSON)
    url = DELETE_DOCUMENT_PATH.format(
        url=str(current_app.config.get("DOCUMENT_SVC_URL")).replace(DOC_PATH, ""),
        drs_id=drs_id
    )
    current_app.logger.info(f"DRS delete_document url={url}")
    response = requests.delete(url=url, headers=headers, timeout=SERVICE_TIMEOUT)
    current_app.logger.info(f"DRS delete call {url} status={response.status_code}")
    if not response.ok:
        current_app.logger.error(f"DRS delete call {url} response={response.content}")
    return response


def update_document_record(bus_document: Document, update_info: dict):
    """
    Update document record properties by unique DRS identifier. Record changes
    are only allowed with existing DRS identifiers that exist in the documents table.
    Updates from the filer:
        consumerReferenceId: the filings record ID.
        consumerFilingDate: the filings record filing date.
        consumerIdentifier: the businesses record identifier.

    DRS API reference https://okagqp-test-bcregrestricted.apigee.io/docs/docserviceproxy/1/overview
        PATCH /doc/api/v1/documents/{docServiceId}

    bus_document: Existing documents table record containing the DRS identifier as the file_key value.
    return: The DRS response, or None if no documents record file key exists.
    """
    drs_id = get_drs_id(bus_document)
    if not drs_id:
        current_app.logger.info("DRS update_document_record aborted: no document file_key.")
        return None
    headers = _get_request_headers(APP_JSON)
    url = PATCH_DOCUMENT_PATH.format(
        url=str(current_app.config.get("DOCUMENT_SVC_URL")).replace(DOC_PATH, ""),
        drs_id=drs_id
    )
    if update_info.get("consumerReferenceId"):
        update_info["consumerReferenceId"] = str(update_info["consumerReferenceId"])
    current_app.logger.info(f"DRS update_document_record url={url}")
    response = requests.patch(url=url, headers=headers, timeout=SERVICE_TIMEOUT, json=update_info)
    current_app.logger.info(f"DRS patch call {url} status={response.status_code}")
    if not response.ok:
        current_app.logger.error(f"DRS patch call {url} response={response.content}")
    return response


def add_replace_document(bus_document: Document, doc_data):
    """
    Add or replace a document associated with an existing document record identified by the unique DRS identifier.

    DRS API reference https://okagqp-test-bcregrestricted.apigee.io/docs/docserviceproxy/1/overview
        PUT /doc/api/v1/documents/{docServiceId}

    bus_document: Existing documents table record containing the DRS identifier as the file_key value.
    doc_data: the document binary data to add to or replace in the DRS for an existing document record.
    return: The DRS response, or None if no documents record file key exists.
    """
    drs_id = get_drs_id(bus_document)
    if not drs_id:
        current_app.logger.info("DRS add_replace_document aborted: no document file_key.")
        return None
    headers = _get_request_headers(APP_PDF)
    url = PUT_DOCUMENT_PATH.format(
        url=str(current_app.config.get("DOCUMENT_SVC_URL")).replace(DOC_PATH, ""),
        drs_id=drs_id
    )
    current_app.logger.info(f"DRS add_replace_document url={url}")
    response = requests.put(url=url, headers=headers, timeout=SERVICE_TIMEOUT, data=doc_data)
    current_app.logger.info(f"DRS put call {url} status={response.status_code}")
    if not response.ok:
        current_app.logger.error(f"DRS put call {url} response={response.content}")
    return response


def build_create_doc_url(doc_class: str, doc_type: str, doc_info: dict) -> str:
    """
    Build the url for the DRS API create document record request.

    doc_class: New record document class.
    doc_type: New record document type.
    doc_info: All other document record extra information.
    return: The create record request request url.
    """
    url = POST_DOCUMENT_PATH.format(
        url=str(current_app.config.get("DOCUMENT_SVC_URL")).replace(DOC_PATH, ""),
        document_class=doc_class,
        document_type=doc_type
    )
    request_params: str = ""
    if doc_info.get("consumerFilename"):
        request_params += f"&consumerFilename={doc_info['consumerFilename']}"
    if doc_info.get("consumerIdentifier"):
        request_params += f"&consumerIdentifier={doc_info['consumerIdentifier']}"
    if doc_info.get("consumerReferenceId"):
        request_params += f"&consumerReferenceId={doc_info['consumerReferenceId']}"
    if doc_info.get("consumerFilingDate"):
        request_params += f"&consumerFilingDate={doc_info['consumerFilingDate']}"
    if request_params != "":
        url += "?" + request_params[1:]
    return url


def get_drs_id(bus_document: Document):
    """
    Extract the DRS identifier GUID from the business document file key.

    bus_document: Existing documents table record containing the DRS identifier as the file_key value.
    return: The DRS identifier if available.
    """
    filekey: str = bus_document.file_key if bus_document else None
    if not filekey or filekey.startswith("DS"):
        return filekey
    tokens = filekey.split("-")
    if tokens and len(tokens) > 1:
        filekey = tokens[1]
    return filekey


def _get_request_headers(content_type, accept_mime_type = None) -> dict:
    """
    Get request headers for the DRS api call.

    content_type: The request header Content-Type value to use.
    accept_mime_type: The request header Accept value to use.
    return: The request headers.
    """
    headers = {
        "Account-Id": BUSINESS_API_ACCOUNT_ID,
        "Content-Type": content_type
    }
    if current_app.config.get("ACCOUNT_SVC_CLIENT_SECRET"):
        token = AccountService.get_bearer_token()
        headers["Authorization"] = BEARER + token
    if apikey := current_app.config.get("DOCUMENT_API_KEY"):
        headers["x-apikey"] = apikey
    if accept_mime_type:
        headers["Accept"] = accept_mime_type
    return headers


def get_content(response):
    """Get the content of the response useful for test methods."""
    c = response.content
    try:
        c = c.decode()
        c = json.loads(c)
    except Exception:
        pass
    return c
