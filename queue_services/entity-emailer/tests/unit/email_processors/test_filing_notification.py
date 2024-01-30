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
"""The Unit Tests for the Incorporation email processor."""
from unittest.mock import patch

import pytest
from legal_api.models import LegalEntity

from entity_emailer.email_processors import filing_notification
from tests.unit import prep_incorp_filing, prep_maintenance_filing


@pytest.mark.parametrize(
    "status",
    [
        ("PAID"),
        ("COMPLETED"),
    ],
)
def test_incorp_notification(app, session, status):
    """Assert that the legal name is changed."""
    # setup filing + business for email
    filing = prep_incorp_filing(session, "BC1234567", "1", status, "BC")
    token = "token"
    # test processor
    with patch.object(filing_notification, "_get_pdfs", return_value=[]) as mock_get_pdfs:
        email = filing_notification.process(
            {"filingId": filing.id, "type": "incorporationApplication", "option": status}, token
        )
        if status == "PAID":
            assert "comp_party@email.com" in email["recipients"]
            assert email["content"]["subject"] == "Confirmation of Filing from the Business Registry"
        else:
            assert email["content"]["subject"] == "Incorporation Documents from the Business Registry"

        assert "test@test.com" in email["recipients"]
        assert email["content"]["body"]
        assert email["content"]["attachments"] == []
        assert mock_get_pdfs.call_args[0][0] == status
        assert mock_get_pdfs.call_args[0][1] == token
        if status == "PAID":
            assert mock_get_pdfs.call_args[0][2]["identifier"].startswith("T")
        else:
            assert mock_get_pdfs.call_args[0][2]["identifier"] == "BC1234567"

        assert mock_get_pdfs.call_args[0][2]["legalType"] == "BC"
        assert mock_get_pdfs.call_args[0][3] == filing


@pytest.mark.parametrize(
    "legal_type",
    [
        ("BEN"),
        ("BC"),
        ("ULC"),
        ("CC"),
    ],
)
def test_numbered_incorp_notification(app, session, legal_type):
    """Assert that the legal name is changed."""
    # setup filing + business for email
    filing = prep_incorp_filing(session, "BC1234567", "1", "PAID", legal_type=legal_type)
    token = "token"
    # test processor
    with patch.object(filing_notification, "_get_pdfs", return_value=[]):
        email = filing_notification.process(
            {"filingId": filing.id, "type": "incorporationApplication", "option": "PAID"}, token
        )

        assert email["content"]["body"]
        assert LegalEntity.BUSINESSES[legal_type]["numberedDescription"] in email["content"]["body"]


@pytest.mark.parametrize(
    ["status", "filing_type", "submitter_role"],
    [
        ("PAID", "annualReport", None),
        ("PAID", "changeOfAddress", None),
        ("PAID", "changeOfDirectors", None),
        ("PAID", "alteration", None),
        ("COMPLETED", "changeOfAddress", None),
        ("COMPLETED", "changeOfDirectors", None),
        ("COMPLETED", "alteration", None),
        ("COMPLETED", "alteration", "staff"),
    ],
)
def test_maintenance_notification(app, session, mocker, status, filing_type, submitter_role):
    """Assert that the legal name is changed."""
    # setup filing + business for email
    filing = prep_maintenance_filing(session, "BC1234567", "1", status, filing_type, submitter_role=submitter_role)
    token = "token"
    # test processor
    mocker.patch(
        "entity_emailer.email_processors.filing_notification.get_user_email_from_auth", return_value="user@email.com"
    )
    with patch.object(filing_notification, "_get_pdfs", return_value=[]) as mock_get_pdfs:
        with patch.object(filing_notification, "get_recipients", return_value="test@test.com") as mock_get_recipients:
            email = filing_notification.process({"filingId": filing.id, "type": filing_type, "option": status}, token)

            if filing_type == "alteration":
                if submitter_role:
                    assert f"{submitter_role}@email.com" in email["recipients"]
                else:
                    assert "user@email.com" in email["recipients"]

            assert "test@test.com" in email["recipients"]
            assert email["content"]["body"]
            assert email["content"]["attachments"] == []
            assert mock_get_pdfs.call_args[0][0] == status
            assert mock_get_pdfs.call_args[0][1] == token
            assert mock_get_pdfs.call_args[0][2]["identifier"] == "BC1234567"
            assert mock_get_pdfs.call_args[0][2]["legalType"] == LegalEntity.EntityTypes.BCOMP.value
            assert mock_get_pdfs.call_args[0][2]["legalName"] == "test business"
            assert mock_get_pdfs.call_args[0][3] == filing
            assert mock_get_recipients.call_args[0][0] == status
            assert mock_get_recipients.call_args[0][1] == filing.filing_json
            assert mock_get_recipients.call_args[0][2] == token
