# Copyright © 2024 Province of British Columbia
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
"""Tests for business_emailer.email_processors.name_request."""
import base64
from unittest.mock import patch

import pytest
import requests_mock

from business_emailer.email_processors import name_request
from business_emailer.services.namex import NameXService
from tests import MockResponse


NR_NUMBER = "NR 1234567"
PAYMENT_TOKEN = "pay-token-abc"
NR_ID = 99
PAYMENT_ID = 42
BEARER = "bearer-token"
EMAIL_INFO = {"identifier": NR_NUMBER, "request": {"paymentToken": PAYMENT_TOKEN}}


@pytest.fixture
def namex_config(app):
    """Set NAMEX_* config values for the duration of a test."""
    keys = {
        "NAMEX_SVC_URL": "https://namex-svc-url/",
        "NAMEX_AUTH_SVC_URL": "https://namex-auth-url/token",
        "NAMEX_SERVICE_CLIENT_USERNAME": "user",
        "NAMEX_SERVICE_CLIENT_SECRET": "secret",
    }
    originals = {k: app.config.get(k) for k in keys}
    app.config.update(keys)
    yield app.config
    for k, v in originals.items():
        app.config[k] = v


def _nr_json(email="test@test.com"):
    return {"id": NR_ID, "applicants": {"emailAddress": email}}


# --- process ---

def test_process_happy_path(app, session, namex_config):
    """Assert full processor output when NR, pdfs, and recipient are all present."""
    nr_response = MockResponse(_nr_json(), 200)
    pdfs = [{"fileName": "Receipt.pdf", "fileBytes": "x", "fileUrl": "", "attachOrder": "1"}]

    with patch.object(NameXService, "query_nr_number", return_value=nr_response), \
            patch.object(name_request, "_get_pdfs", return_value=pdfs) as mock_pdfs:
        email = name_request.process(EMAIL_INFO)

        assert email["recipients"] == "test@test.com"
        assert email["content"]["subject"] == f"{NR_NUMBER} - Receipt from Corporate Registry"
        assert email["content"]["attachments"] == pdfs
        assert email["content"]["body"]
        assert mock_pdfs.call_args[0] == (NR_ID, PAYMENT_TOKEN)


def test_process_returns_empty_when_nr_lookup_fails(app, session, namex_config):
    """Assert {} is returned when NameX responds with a non-200."""
    with patch.object(NameXService, "query_nr_number", return_value=MockResponse({}, 500)):
        assert name_request.process(EMAIL_INFO) == {}


def test_process_returns_empty_when_no_pdfs(app, session, namex_config):
    """Assert {} is returned when _get_pdfs yields nothing."""
    with patch.object(NameXService, "query_nr_number", return_value=MockResponse(_nr_json(), 200)), \
            patch.object(name_request, "_get_pdfs", return_value=[]):
        assert name_request.process(EMAIL_INFO) == {}


def test_process_returns_empty_when_no_recipients(app, session, namex_config):
    """Assert {} is returned when the NR has no applicant email."""
    pdfs = [{"fileName": "Receipt.pdf", "fileBytes": "x", "fileUrl": "", "attachOrder": "1"}]
    with patch.object(NameXService, "query_nr_number",
                      return_value=MockResponse(_nr_json(email=""), 200)), \
            patch.object(name_request, "_get_pdfs", return_value=pdfs):
        assert name_request.process(EMAIL_INFO) == {}


# --- _get_pdfs ---

@pytest.mark.parametrize("token,nr_id,payment_token", [
    (None, NR_ID, PAYMENT_TOKEN),
    (BEARER, None, PAYMENT_TOKEN),
    (BEARER, NR_ID, ""),
])
def test_get_pdfs_returns_empty_on_missing_inputs(app, namex_config, token, nr_id, payment_token):
    """Assert any missing input (token, nr_id, payment_token) short-circuits to []."""
    with app.app_context(), patch.object(name_request, "get_nr_bearer_token", return_value=token):
        assert name_request._get_pdfs(nr_id, payment_token) == []


def test_get_pdfs_returns_empty_when_payments_lookup_fails(app, namex_config):
    """Assert [] when the NameX payments endpoint returns non-200."""
    with app.app_context(), \
            patch.object(name_request, "get_nr_bearer_token", return_value=BEARER), \
            requests_mock.Mocker() as m:
        m.get(f'{namex_config["NAMEX_SVC_URL"]}payments/{NR_ID}', status_code=500)
        assert name_request._get_pdfs(NR_ID, PAYMENT_TOKEN) == []


def test_get_pdfs_returns_empty_when_no_matching_payment(app, namex_config):
    """Assert [] when no payment record matches the payment token."""
    with app.app_context(), \
            patch.object(name_request, "get_nr_bearer_token", return_value=BEARER), \
            requests_mock.Mocker() as m:
        m.get(f'{namex_config["NAMEX_SVC_URL"]}payments/{NR_ID}',
              json=[{"id": 1, "token": "other-token"}], status_code=200)
        assert name_request._get_pdfs(NR_ID, PAYMENT_TOKEN) == []


def test_get_pdfs_returns_empty_when_receipt_fails(app, namex_config):
    """Assert [] when the receipt POST returns non-200."""
    with app.app_context(), \
            patch.object(name_request, "get_nr_bearer_token", return_value=BEARER), \
            requests_mock.Mocker() as m:
        m.get(f'{namex_config["NAMEX_SVC_URL"]}payments/{NR_ID}',
              json=[{"id": PAYMENT_ID, "token": PAYMENT_TOKEN}], status_code=200)
        m.post(f'{namex_config["NAMEX_SVC_URL"]}payments/{PAYMENT_ID}/receipt', status_code=500)
        assert name_request._get_pdfs(NR_ID, PAYMENT_TOKEN) == []


def test_get_pdfs_happy_path_encodes_receipt(app, namex_config):
    """Assert the receipt PDF is base64-encoded into the returned attachment."""
    pdf_bytes = b"%PDF-fake-content"
    with app.app_context(), \
            patch.object(name_request, "get_nr_bearer_token", return_value=BEARER), \
            requests_mock.Mocker() as m:
        m.get(f'{namex_config["NAMEX_SVC_URL"]}payments/{NR_ID}',
              json=[{"id": 1, "token": "other"}, {"id": PAYMENT_ID, "token": PAYMENT_TOKEN}],
              status_code=200)
        m.post(f'{namex_config["NAMEX_SVC_URL"]}payments/{PAYMENT_ID}/receipt',
               content=pdf_bytes, status_code=200)

        pdfs = name_request._get_pdfs(NR_ID, PAYMENT_TOKEN)

    assert len(pdfs) == 1
    assert pdfs[0]["fileName"] == "Receipt.pdf"
    assert pdfs[0]["attachOrder"] == "1"
    assert base64.b64decode(pdfs[0]["fileBytes"]) == pdf_bytes


# --- get_nr_bearer_token ---

def test_get_nr_bearer_token_returns_access_token(app, namex_config):
    """Assert the access_token field is extracted from the auth response."""
    with app.app_context(), requests_mock.Mocker() as m:
        m.post(namex_config["NAMEX_AUTH_SVC_URL"], json={"access_token": "abc"}, status_code=200)
        assert name_request.get_nr_bearer_token() == "abc"


def test_get_nr_bearer_token_returns_none_on_bad_json(app, namex_config):
    """Assert None is returned when the auth response body is not valid JSON."""
    with app.app_context(), requests_mock.Mocker() as m:
        m.post(namex_config["NAMEX_AUTH_SVC_URL"], text="not json", status_code=200)
        assert name_request.get_nr_bearer_token() is None
