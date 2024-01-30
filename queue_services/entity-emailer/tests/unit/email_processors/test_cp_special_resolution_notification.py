# Copyright © 2021 Province of British Columbia
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
"""The Unit Tests for the Special Resolution email processor."""
import base64
from unittest.mock import patch

import pytest
import requests_mock
from legal_api.models import LegalEntity

from entity_emailer.email_processors import special_resolution_notification
from tests.unit import prep_cp_special_resolution_filing

LEGAL_TYPE = LegalEntity.EntityTypes.COOP.value
LEGAL_NAME = "test business"
IDENTIFIER = "CP1234567"
TOKEN = "token"
RECIPIENT_EMAIL = "recipient@email.com"
USER_EMAIL_FROM_AUTH = "user@email.com"


@pytest.mark.parametrize("status", [("PAID"), ("COMPLETED")])
def test_cp_special_resolution_notification(session, app, config, status):
    """Assert that the special resolution email processor works as expected."""
    # setup filing + business for email
    filing = prep_cp_special_resolution_filing(IDENTIFIER, "1", LEGAL_TYPE, LEGAL_NAME, submitter_role=None)
    get_pdf_function = "get_paid_pdfs" if status == "PAID" else "get_completed_pdfs"
    # test processor
    with patch.object(special_resolution_notification, get_pdf_function, return_value=[]) as mock_get_pdfs:
        with patch.object(special_resolution_notification, "get_recipient_from_auth", return_value=RECIPIENT_EMAIL):
            with patch.object(
                special_resolution_notification, "get_user_email_from_auth", return_value=USER_EMAIL_FROM_AUTH
            ):
                email = special_resolution_notification.process(
                    {"filingId": filing.id, "type": "specialResolution", "option": status}, TOKEN
                )
                if status == "PAID":
                    assert (
                        email["content"]["subject"]
                        == LEGAL_NAME + " - Confirmation of Special Resolution from the Business Registry"
                    )
                else:
                    assert (
                        email["content"]["subject"]
                        == LEGAL_NAME + " - Special Resolution Documents from the Business Registry"
                    )

                assert RECIPIENT_EMAIL in email["recipients"]
                assert USER_EMAIL_FROM_AUTH in email["recipients"]
                assert email["content"]["body"]
                assert email["content"]["attachments"] == []
                assert mock_get_pdfs.call_args[0][0] == TOKEN
                assert mock_get_pdfs.call_args[0][1]["identifier"] == IDENTIFIER
                assert mock_get_pdfs.call_args[0][2] == filing


def test_complete_special_resolution_attachments(session, config):
    """Test completed special resolution notification."""
    # setup filing + business for email
    status = "COMPLETED"
    filing = prep_cp_special_resolution_filing(IDENTIFIER, "1", LEGAL_TYPE, LEGAL_NAME, submitter_role=None)
    with requests_mock.Mocker() as m:
        with patch.object(special_resolution_notification, "get_recipient_from_auth", return_value=RECIPIENT_EMAIL):
            with patch.object(
                special_resolution_notification, "get_user_email_from_auth", return_value=USER_EMAIL_FROM_AUTH
            ):
                m.get(
                    (
                        f'{config.get("LEGAL_API_URL")}'
                        f"/businesses/{IDENTIFIER}"
                        f"/filings/{filing.id}"
                        f"?type=specialResolution"
                    ),
                    content=b"pdf_content_1",
                    status_code=200,
                )
                m.get(
                    f'{config.get("LEGAL_API_URL")}/businesses/{IDENTIFIER}/filings/{filing.id}'
                    "?type=certificateOfNameChange",
                    content=b"pdf_content_2",
                    status_code=200,
                )
                m.get(
                    f'{config.get("LEGAL_API_URL")}/businesses/{IDENTIFIER}/filings/{filing.id}?type=certifiedRules',
                    content=b"pdf_content_3",
                    status_code=200,
                )

                output = special_resolution_notification.process(
                    {"filingId": filing.id, "type": "specialResolution", "option": status}, TOKEN
                )
                assert "content" in output
                assert "attachments" in output["content"]
                assert len(output["content"]["attachments"]) == 3
                assert output["content"]["attachments"][0]["fileName"] == "Special Resolution.pdf"
                assert (
                    base64.b64decode(output["content"]["attachments"][0]["fileBytes"]).decode("utf-8")
                    == "pdf_content_1"
                )
                assert output["content"]["attachments"][1]["fileName"] == "Certificate of Name Change.pdf"
                assert (
                    base64.b64decode(output["content"]["attachments"][1]["fileBytes"]).decode("utf-8")
                    == "pdf_content_2"
                )
                assert output["content"]["attachments"][2]["fileName"] == "Certified Rules.pdf"
                assert (
                    base64.b64decode(output["content"]["attachments"][2]["fileBytes"]).decode("utf-8")
                    == "pdf_content_3"
                )


def test_paid_special_resolution_attachments(session, config):
    """Test paid special resolution notification."""
    # setup filing + business for email
    status = "PAID"
    filing = prep_cp_special_resolution_filing(IDENTIFIER, "1", LEGAL_TYPE, LEGAL_NAME, submitter_role=None)
    with requests_mock.Mocker() as m:
        with patch.object(special_resolution_notification, "get_recipient_from_auth", return_value=RECIPIENT_EMAIL):
            with patch.object(
                special_resolution_notification, "get_user_email_from_auth", return_value=USER_EMAIL_FROM_AUTH
            ):
                m.get(
                    (
                        f'{config.get("LEGAL_API_URL")}'
                        f"/businesses/{IDENTIFIER}"
                        f"/filings/{filing.id}"
                        f"?type=specialResolutionApplication"
                    ),
                    content=b"pdf_content_1",
                    status_code=200,
                )
                m.post(f'{config.get("PAY_API_URL")}/1/receipts', content=b"pdf_content_2", status_code=201)
                output = special_resolution_notification.process(
                    {"filingId": filing.id, "type": "specialResolution", "option": status}, TOKEN
                )
                assert "content" in output
                assert "attachments" in output["content"]
                assert len(output["content"]["attachments"]) == 2
                assert output["content"]["attachments"][0]["fileName"] == "Special Resolution Application.pdf"
                assert (
                    base64.b64decode(output["content"]["attachments"][0]["fileBytes"]).decode("utf-8")
                    == "pdf_content_1"
                )
                assert output["content"]["attachments"][1]["fileName"] == "Receipt.pdf"
                assert (
                    base64.b64decode(output["content"]["attachments"][1]["fileBytes"]).decode("utf-8")
                    == "pdf_content_2"
                )
