# Copyright © 2020 Province of British Columbia
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
"""The Unit Tests for the Restoration email processor."""

import base64
from unittest.mock import patch

import pytest
import requests_mock

from entity_emailer.email_processors import restoration_notification
from tests.unit import prep_restoration_filing

LEGAL_NAME = "test business"
BUS_ID = "BC1234567"
TOKEN = "token"
EXPECTED_EMAIL = "joe@email.com"


def test_complete_full_restoration_notification_includes_notice_of_articles_and_incorporation_cert(session, config):
    """Test completed full restoration notification."""
    # setup filing + business for email
    status = "COMPLETED"
    filing = prep_restoration_filing(BUS_ID, "1", "BC", LEGAL_NAME)
    with requests_mock.Mocker() as m:
        m.get(
            f'{config.get("LEGAL_API_URL")}/businesses/{BUS_ID}/filings/{filing.id}?type=noticeOfArticles',
            content=b"pdf_content_1",
            status_code=200,
        )
        m.get(
            f'{config.get("LEGAL_API_URL")}/businesses/{BUS_ID}/filings/{filing.id}?type=certificateOfRestoration',
            content=b"pdf_content_2",
        )
        output = restoration_notification.process(
            {"filingId": filing.id, "type": "restoration", "option": status}, TOKEN
        )
        assert "content" in output
        assert "attachments" in output["content"]
        assert len(output["content"]["attachments"]) == 2
        assert output["content"]["attachments"][0]["fileName"] == "Notice of Articles.pdf"
        assert base64.b64decode(output["content"]["attachments"][0]["fileBytes"]).decode("utf-8") == "pdf_content_1"
        assert output["content"]["attachments"][1]["fileName"] == "Certificate of Restoration.pdf"
        assert base64.b64decode(output["content"]["attachments"][1]["fileBytes"]).decode("utf-8") == "pdf_content_2"


def test_paid_restoration_notification_includes_receipt_and_restoration_application_attachments(session, config):
    """Test PAID full restoration notification."""
    # setup filing + business for email
    status = "PAID"
    filing = prep_restoration_filing(BUS_ID, "1", "BC", LEGAL_NAME)
    with requests_mock.Mocker() as m:
        m.post(
            f'{config.get("PAY_API_URL")}/{filing.payment_token}/receipts', content=b"pdf_content_1", status_code=201
        )
        m.get(
            f'{config.get("LEGAL_API_URL")}/businesses/{BUS_ID}/filings/{filing.id}',
            content=b"pdf_content_2",
            status_code=200,
        )
        output = restoration_notification.process(
            {"filingId": filing.id, "type": "restoration", "option": status}, TOKEN
        )
        assert "content" in output
        assert "attachments" in output["content"]
        assert len(output["content"]["attachments"]) == 2
        assert output["content"]["attachments"][0]["fileName"] == "Restoration Application.pdf"
        assert base64.b64decode(output["content"]["attachments"][0]["fileBytes"]).decode("utf-8") == "pdf_content_2"
        assert output["content"]["attachments"][1]["fileName"] == "Receipt.pdf"
        assert base64.b64decode(output["content"]["attachments"][1]["fileBytes"]).decode("utf-8") == "pdf_content_1"


def test_completed_full_restoration_notification(session, config):
    """Test completed full restoration notification."""
    # setup filing + business for email
    status = "COMPLETED"
    filing = prep_restoration_filing(BUS_ID, "1", "BC", LEGAL_NAME)
    # test processor
    with patch.object(restoration_notification, "_get_completed_pdfs", return_value=[]):
        email_dict = restoration_notification.process(
            {"filingId": filing.id, "type": "restoration", "option": status}, TOKEN
        )
        email = email_dict["content"]["body"]
        assert email_dict["content"]["subject"] == "test business - Restoration Documents from the Business Registry"
        assert EXPECTED_EMAIL in email_dict["recipients"]
        assert "You have successfully restored your business with the BC Business Registry" in email


def test_completed_extended_restoration_notification(session, config):
    """Test completed extended restoration notification includes specific wording."""
    # setup filing + business for email
    status = "COMPLETED"
    filing = prep_restoration_filing(BUS_ID, "1", "BC", LEGAL_NAME, "limitedRestorationExtension")
    with patch.object(restoration_notification, "_get_completed_pdfs", return_value=[]):
        email_dict = restoration_notification.process(
            {"filingId": filing.id, "type": "restoration", "option": status}, TOKEN
        )
        email = email_dict["content"]["body"]
        assert "You have successfully extended the period of restoration with the BC Business" in email


@pytest.mark.parametrize(
    "restoration_type, attachment_name",
    [
        ("fullRestoration", "Full Restoration Application"),
        ("limitedRestoration", "Limited Restoration Application"),
        ("limitedRestorationExtension", "Limited Restoration Extension Application"),
        ("limitedRestorationToFull", "Conversion to Full Restoration Application"),
    ],
)
def test_paid_full_restoration_notification(session, restoration_type, attachment_name):
    """Test PAID restoration notification."""
    # setup filing + business for email
    status = "PAID"
    filing = prep_restoration_filing("BC1234567", "1", "BC", LEGAL_NAME, restoration_type)
    # test processor
    with patch.object(restoration_notification, "_get_paid_pdfs", return_value=[]):
        email_dict = restoration_notification.process(
            {"filingId": filing.id, "type": "restoration", "option": status}, TOKEN
        )
        email = email_dict["content"]["body"]
        assert EXPECTED_EMAIL in email_dict["recipients"]
        assert email_dict["content"]["subject"] == "test business - Confirmation of Filing from the Business Registry"
        assert EXPECTED_EMAIL in email_dict["recipients"]
        assert "You have successfully filed your restoration with the BC Business Registry" in email
        assert email_dict["content"]["attachments"] == []
        assert attachment_name in email
