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
"""Manages Filer -> DRS integration for updating client document records after a filing completes."""
import json

import requests
from flask import current_app

from business_filer.services import AccountService

PATCH_DOCUMENT_PATH: str = "{url}/documents/client/{document_key}"
SERVICE_TIMEOUT = 30.0


def update_document_record(document_key: str, update_info: dict):
    """Update document record properties via the Business API documents endpoint.

    Business API reference: PATCH /business/api/v2/documents/client/{documentKey}

    document_key: The business documents table file_key value, formatted as
        "{documentClass}-{documentServiceId}".
    update_info: The properties to update - any of filingId, filingDate, businessIdentifier.
    return: The Business API response, or None if no document_key is available to update.
    """
    if not document_key:
        current_app.logger.info("update_document_record aborted: no document file_key.")
        return None
    url = PATCH_DOCUMENT_PATH.format(
        url=str(current_app.config.get("LEGAL_API_URL")).rstrip("/"),
        document_key=document_key
    )
    headers = _get_request_headers()
    current_app.logger.info(f"Business API update_document_record url={url}")
    response = requests.patch(url=url, headers=headers, timeout=SERVICE_TIMEOUT, json=update_info)
    current_app.logger.info(f"Business API patch call {url} status={response.status_code}")
    if not response.ok:
        current_app.logger.error(f"Business API patch call {url} response={response.content}")
    return response


def _get_request_headers() -> dict:
    """Get request headers."""
    headers = {
        **AccountService.CONTENT_TYPE_JSON
    }

    if current_app.config.get("ACCOUNT_SVC_CLIENT_SECRET"):
        token = AccountService.get_bearer_token()
        headers["Authorization"] = AccountService.BEARER + token

    return headers


def get_content(response):
    """Get the content of the response useful for test methods."""
    content = response.content
    try:
        content = content.decode()
        content = json.loads(content)
    except Exception:  # pylint: disable=broad-except; best-effort parsing only
        pass
    return content
