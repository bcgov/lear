# Copyright © 2022 Province of British Columbia
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
"""The Unit Tests for the Correction email processor."""
import base64
from unittest.mock import patch

import pytest
import requests_mock
from legal_api.models import LegalEntity

from entity_emailer.email_processors import correction_notification
from tests.unit import (
    prep_cp_special_resolution_correction_filing,
    prep_cp_special_resolution_filing,
    prep_firm_correction_filing,
    prep_incorp_filing,
    prep_incorporation_correction_filing,
)

COMPLETED_SUBJECT_SUFIX = " - Correction Documents from the Business Registry"
CP_IDENTIFIER = "CP1234567"
SPECIAL_RESOLUTION_FILING_TYPE = "specialResolution"


@pytest.mark.parametrize(
    "status,legal_type",
    [
        ("PAID", LegalEntity.EntityTypes.SOLE_PROP.value),
        ("COMPLETED", LegalEntity.EntityTypes.SOLE_PROP.value),
        ("PAID", LegalEntity.EntityTypes.PARTNERSHIP.value),
        ("COMPLETED", LegalEntity.EntityTypes.PARTNERSHIP.value),
    ],
)
def test_firm_correction_notification(app, session, status, legal_type):
    """Assert that email attributes are correct."""
    # setup filing + business for email
    legal_name = "test business"
    filing = prep_firm_correction_filing(session, "FM1234567", "1", legal_type, legal_name, "staff")
    token = "token"
    # test processor
    with patch.object(correction_notification, "_get_pdfs", return_value=[]) as mock_get_pdfs:
        email = correction_notification.process({"filingId": filing.id, "type": "correction", "option": status}, token)
        if status == "PAID":
            assert email["content"]["subject"] == legal_name + " - Confirmation of Filing from the Business Registry"
        else:
            assert email["content"]["subject"] == legal_name + COMPLETED_SUBJECT_SUFIX

        if status == "COMPLETED":
            assert "no_one@never.get" in email["recipients"]
            if legal_type == LegalEntity.EntityTypes.PARTNERSHIP.value:
                assert "party@email.com" in email["recipients"]

        assert email["content"]["body"]
        assert email["content"]["attachments"] == []
        assert mock_get_pdfs.call_args[0][0] == status
        assert mock_get_pdfs.call_args[0][1] == token
        if status == "COMPLETED":
            assert mock_get_pdfs.call_args[0][2]["identifier"] == "FM1234567"
        assert mock_get_pdfs.call_args[0][3] == filing


@pytest.mark.parametrize(
    "status,legal_type",
    [
        ("PAID", LegalEntity.EntityTypes.COMP.value),
        ("COMPLETED", LegalEntity.EntityTypes.COMP.value),
        ("PAID", LegalEntity.EntityTypes.BCOMP.value),
        ("COMPLETED", LegalEntity.EntityTypes.BCOMP.value),
        ("PAID", LegalEntity.EntityTypes.BC_CCC.value),
        ("COMPLETED", LegalEntity.EntityTypes.BC_CCC.value),
        ("PAID", LegalEntity.EntityTypes.BC_ULC_COMPANY.value),
        ("COMPLETED", LegalEntity.EntityTypes.BC_ULC_COMPANY.value),
    ],
)
def test_bc_correction_notification(app, session, status, legal_type):
    """Assert that email attributes are correct."""
    # setup filing + business for email
    legal_name = "test business"
    original_filing = prep_incorp_filing(session, "BC1234567", "1", status, legal_type=legal_type)
    token = "token"
    business = LegalEntity.find_by_identifier("BC1234567")
    filing = prep_incorporation_correction_filing(session, business, original_filing.id, "1", status)
    # test processor
    with patch.object(correction_notification, "_get_pdfs", return_value=[]) as mock_get_pdfs:
        email = correction_notification.process({"filingId": filing.id, "type": "correction", "option": status}, token)
        if status == "PAID":
            assert email["content"]["subject"] == legal_name + " - Confirmation of Filing from the Business Registry"
        else:
            assert email["content"]["subject"] == legal_name + COMPLETED_SUBJECT_SUFIX

        assert "comp_party@email.com" in email["recipients"]
        assert "test@test.com" in email["recipients"]

        assert email["content"]["body"]
        assert email["content"]["attachments"] == []

        assert mock_get_pdfs.call_args[0][0] == status
        assert mock_get_pdfs.call_args[0][1] == token

        if status == "COMPLETED":
            assert mock_get_pdfs.call_args[0][2]["identifier"] == "BC1234567"
        assert mock_get_pdfs.call_args[0][3] == filing


@pytest.mark.parametrize(
    "status,legal_type",
    [
        ("PAID", LegalEntity.EntityTypes.COOP.value),
        ("COMPLETED", LegalEntity.EntityTypes.COOP.value),
    ],
)
def test_cp_special_resolution_correction_notification(app, session, status, legal_type):
    """Assert that email attributes are correct."""
    # setup filing + business for email
    legal_name = "cp business"
    original_filing = prep_cp_special_resolution_filing(CP_IDENTIFIER, "1", legal_type, legal_name, submitter_role=None)
    token = "token"
    business = LegalEntity.find_by_identifier(CP_IDENTIFIER)
    filing = prep_cp_special_resolution_correction_filing(
        session, business, original_filing.id, "1", status, SPECIAL_RESOLUTION_FILING_TYPE
    )
    # test processor
    with patch.object(correction_notification, "_get_pdfs", return_value=[]) as mock_get_pdfs:
        email = correction_notification.process({"filingId": filing.id, "type": "correction", "option": status}, token)
        if status == "PAID":
            assert email["content"]["subject"] == legal_name + " - Confirmation of correction"
        else:
            assert email["content"]["subject"] == legal_name + COMPLETED_SUBJECT_SUFIX

        assert "cp_sr@test.com" in email["recipients"]

        assert email["content"]["body"]
        assert email["content"]["attachments"] == []

        assert mock_get_pdfs.call_args[0][0] == status
        assert mock_get_pdfs.call_args[0][1] == token

        if status == "COMPLETED":
            assert mock_get_pdfs.call_args[0][2]["identifier"] == CP_IDENTIFIER
        assert mock_get_pdfs.call_args[0][3] == filing


def test_complete_special_resolution_correction_attachments(session, config):
    """Test completed special resolution correction notification."""
    # setup filing + business for email
    legal_type = LegalEntity.EntityTypes.COOP.value
    legal_name = "test cp sr business"
    token = "token"
    status = "COMPLETED"
    original_filing = prep_cp_special_resolution_filing(CP_IDENTIFIER, "1", legal_type, legal_name, submitter_role=None)
    business = LegalEntity.find_by_identifier(CP_IDENTIFIER)
    filing = prep_cp_special_resolution_correction_filing(
        session, business, original_filing.id, "1", status, SPECIAL_RESOLUTION_FILING_TYPE
    )
    with requests_mock.Mocker() as m:
        m.get(
            (
                f'{config.get("LEGAL_API_URL")}'
                f"/businesses/{CP_IDENTIFIER}"
                f"/filings/{filing.id}"
                f"?type=specialResolution"
            ),
            content=b"pdf_content_1",
            status_code=200,
        )
        m.get(
            f'{config.get("LEGAL_API_URL")}/businesses/{CP_IDENTIFIER}/filings/{filing.id}'
            "?type=certificateOfNameChange",
            content=b"pdf_content_2",
            status_code=200,
        )
        m.get(
            f'{config.get("LEGAL_API_URL")}/businesses/{CP_IDENTIFIER}/filings/{filing.id}?type=certifiedRules',
            content=b"pdf_content_3",
            status_code=200,
        )

        output = correction_notification.process({"filingId": filing.id, "type": "correction", "option": status}, token)
        assert "content" in output
        assert "attachments" in output["content"]
        assert len(output["content"]["attachments"]) == 3
        assert output["content"]["attachments"][0]["fileName"] == "Special Resolution.pdf"
        assert base64.b64decode(output["content"]["attachments"][0]["fileBytes"]).decode("utf-8") == "pdf_content_1"
        assert output["content"]["attachments"][1]["fileName"] == "Certificate of Name Change.pdf"
        assert base64.b64decode(output["content"]["attachments"][1]["fileBytes"]).decode("utf-8") == "pdf_content_2"
        assert output["content"]["attachments"][2]["fileName"] == "Certified Rules.pdf"
        assert base64.b64decode(output["content"]["attachments"][2]["fileBytes"]).decode("utf-8") == "pdf_content_3"


def test_paid_special_resolution_correction_attachments(session, config):
    """Test paid special resolution correction notification."""
    # setup filing + business for email
    legal_type = LegalEntity.EntityTypes.COOP.value
    legal_name = "test cp sr business"
    token = "token"
    status = "PAID"
    original_filing = prep_cp_special_resolution_filing(CP_IDENTIFIER, "1", legal_type, legal_name, submitter_role=None)
    business = LegalEntity.find_by_identifier(CP_IDENTIFIER)
    filing = prep_cp_special_resolution_correction_filing(
        session, business, original_filing.id, "1", status, SPECIAL_RESOLUTION_FILING_TYPE
    )
    with requests_mock.Mocker() as m:
        m.get(
            f'{config.get("LEGAL_API_URL")}/businesses/{CP_IDENTIFIER}/filings/{filing.id}' f"?type=correction",
            content=b"pdf_content_1",
            status_code=200,
        )
        m.post(f'{config.get("PAY_API_URL")}/1/receipts', content=b"pdf_content_2", status_code=201)
        output = correction_notification.process({"filingId": filing.id, "type": "correction", "option": status}, token)
        assert "content" in output
        assert "attachments" in output["content"]
        assert len(output["content"]["attachments"]) == 2
        assert output["content"]["attachments"][0]["fileName"] == "Register Correction Application.pdf"
        assert base64.b64decode(output["content"]["attachments"][0]["fileBytes"]).decode("utf-8") == "pdf_content_1"
        assert output["content"]["attachments"][1]["fileName"] == "Receipt.pdf"
        assert base64.b64decode(output["content"]["attachments"][1]["fileBytes"]).decode("utf-8") == "pdf_content_2"


@pytest.mark.parametrize(
    "legal_type, filing_type",
    [
        (LegalEntity.EntityTypes.COOP.value, SPECIAL_RESOLUTION_FILING_TYPE),
        (LegalEntity.EntityTypes.CCC_CONTINUE_IN.value, SPECIAL_RESOLUTION_FILING_TYPE),
        (LegalEntity.EntityTypes.COOP.value, "registration"),
    ],
)
def test_paid_special_resolution_correction_on_correction(session, config, legal_type, filing_type):
    """Assert that email attributes are correct."""
    # setup filing + business for email
    legal_name = "cp business"
    original_filing = prep_cp_special_resolution_filing(CP_IDENTIFIER, "1", legal_type, legal_name, submitter_role=None)
    token = "token"
    business = LegalEntity.find_by_identifier(CP_IDENTIFIER)
    filing_correction = prep_cp_special_resolution_correction_filing(
        session, business, original_filing.id, "1", "COMPLETED", filing_type
    )
    filing = prep_cp_special_resolution_correction_filing(
        session, business, filing_correction.id, "1", "PAID", "correction"
    )
    # test processor
    with patch.object(correction_notification, "_get_pdfs", return_value=[]):
        email = correction_notification.process({"filingId": filing.id, "type": "correction", "option": "PAID"}, token)
    if legal_type == LegalEntity.EntityTypes.COOP.value and filing_type == "specialResolution":
        assert email["content"]["subject"] == legal_name + " - Confirmation of correction"
        assert "cp_sr@test.com" in email["recipients"]
        assert email["content"]["body"]
        assert email["content"]["attachments"] == []
