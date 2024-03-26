# Copyright © 2023 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""The Test Suites to ensure that the worker is operating correctly."""
import base64
from datetime import datetime
from http import HTTPStatus
from unittest.mock import patch

import pytest
from legal_api.models import LegalEntity
from legal_api.services import NameXService
from legal_api.services.bootstrap import AccountService
from legal_api.utils.legislation_datetime import LegislationDatetime
from simple_cloudevent import SimpleCloudEvent, to_queue_message

from entity_emailer import worker
from entity_emailer.email_processors import (
    ar_reminder_notification,
    correction_notification,
    filing_notification,
    name_request,
    nr_notification,
    special_resolution_notification,
)
from entity_emailer.services import queue
from tests import MockResponse
from tests.unit import (
    nested_session,
    prep_cp_special_resolution_correction_filing,
    prep_cp_special_resolution_filing,
    prep_incorp_filing,
    prep_maintenance_filing,
)


def test_no_message(client):
    """Return a 4xx when an no JSON present."""

    rv = client.post("/")

    assert rv.status_code == HTTPStatus.OK


CLOUD_EVENT = SimpleCloudEvent(
    id="fake-id",
    source="fake-for-tests",
    subject="fake-subject",
    type="email",
    data={"email": {"filingId": "BC1234567", "type": "bn", "option": "COMPLETED"}},
)
#
# This needs to mimic the envelope created by GCP PubSb when call a resource
#
CLOUD_EVENT_ENVELOPE = {
    "subscription": "projects/PUBSUB_PROJECT_ID/subscriptions/SUBSCRIPTION_ID",
    "message": {
        "data": base64.b64encode(to_queue_message(CLOUD_EVENT)).decode("UTF-8"),
        "messageId": "10",
        "attributes": {},
    },
    "id": 1,
}


@pytest.mark.parametrize(
    "test_name,queue_envelope,expected",
    [("invalid", {}, HTTPStatus.OK), ("valid", CLOUD_EVENT_ENVELOPE, HTTPStatus.OK)],
)
def test_simple_cloud_event(client, session, test_name, queue_envelope, expected):
    with nested_session(session):
        rv = client.post("/", json=CLOUD_EVENT_ENVELOPE)
        assert rv.status_code == expected


@pytest.mark.parametrize(
    "option",
    [
        ("PAID"),
        ("COMPLETED"),
    ],
)
def test_process_incorp_email(app, session, client, option):
    """Assert that an INCORP email msg is processed correctly."""
    # Setup
    filing = prep_incorp_filing(session, "BC1234567", "1", option, "BC")
    token = "1"
    email_msg = {"email": {"filingId": filing.id, "type": "incorporationApplication", "option": option}}
    message = helper_create_cloud_event_envelope(data=email_msg)

    with patch.object(AccountService, "get_bearer_token", return_value=token):
        with patch.object(filing_notification, "_get_pdfs", return_value=[]) as mock_get_pdfs:
            with patch.object(worker, "send_email", return_value="success") as mock_send_email:
                with patch.object(queue, "publish", return_value={}):
                    # TEST
                    rv = client.post("/", json=message)

                    # Check
                    assert rv.status_code == HTTPStatus.OK

                    assert mock_get_pdfs.call_args[0][0] == option
                    assert mock_get_pdfs.call_args[0][1] == token
                    if option == "PAID":
                        assert mock_get_pdfs.call_args[0][2]["identifier"].startswith("T")
                    else:
                        assert mock_get_pdfs.call_args[0][2]["identifier"] == "BC1234567"

                    assert mock_get_pdfs.call_args[0][2]["legalType"] == "BC"
                    assert mock_get_pdfs.call_args[0][3] == filing

                    if option == "PAID":
                        assert "comp_party@email.com" in mock_send_email.call_args[0][0]["recipients"]
                        assert (
                            mock_send_email.call_args[0][0]["content"]["subject"]
                            == "Confirmation of Filing from the Business Registry"
                        )
                    else:
                        assert (
                            mock_send_email.call_args[0][0]["content"]["subject"]
                            == "Incorporation Documents from the Business Registry"
                        )
                    assert "test@test.com" in mock_send_email.call_args[0][0]["recipients"]
                    assert mock_send_email.call_args[0][0]["content"]["body"]
                    assert mock_send_email.call_args[0][0]["content"]["attachments"] == []
                    assert mock_send_email.call_args[0][1] == token


@pytest.mark.parametrize(
    ["status", "filing_type"],
    [
        ("PAID", "annualReport"),
        ("PAID", "changeOfAddress"),
        ("PAID", "changeOfDirectors"),
        ("COMPLETED", "changeOfAddress"),
        ("COMPLETED", "changeOfDirectors"),
    ],
)
def test_maintenance_notification(app, session, client, status, filing_type):
    """Assert that the legal name is changed."""
    # Setup
    filing = prep_maintenance_filing(session, "BC1234567", "1", status, filing_type)
    token = "token"
    email_msg = {"email": {"filingId": filing.id, "type": f"{filing_type}", "option": status}}
    message = helper_create_cloud_event_envelope(data=email_msg)

    with patch.object(AccountService, "get_bearer_token", return_value=token):
        with patch.object(filing_notification, "_get_pdfs", return_value=[]) as mock_get_pdfs:
            with patch.object(
                filing_notification, "get_recipients", return_value="test@test.com"
            ) as mock_get_recipients:
                with patch.object(worker, "send_email", return_value="success") as mock_send_email:
                    with patch.object(queue, "publish", return_value={}):
                        # TEST
                        rv = client.post("/", json=message)

                        # Check
                        assert rv.status_code == HTTPStatus.OK

                        assert mock_get_pdfs.call_args[0][0] == status
                        assert mock_get_pdfs.call_args[0][1] == token

                        assert mock_get_pdfs.call_args[0][2]["identifier"] == "BC1234567"
                        assert mock_get_pdfs.call_args[0][2]["legalType"] == LegalEntity.EntityTypes.BCOMP.value
                        assert mock_get_pdfs.call_args[0][2]["legalName"] == "test business"

                        assert mock_get_pdfs.call_args[0][3] == filing
                        assert mock_get_recipients.call_args[0][0] == status
                        assert mock_get_recipients.call_args[0][1] == filing.filing_json
                        assert mock_get_recipients.call_args[0][2] == token

                        assert mock_send_email.call_args[0][0]["content"]["subject"]
                        assert "test@test.com" in mock_send_email.call_args[0][0]["recipients"]
                        assert mock_send_email.call_args[0][0]["content"]["body"]
                        assert mock_send_email.call_args[0][0]["content"]["attachments"] == []
                        assert mock_send_email.call_args[0][1] == token


@pytest.mark.parametrize(
    ["status", "filing_type", "identifier"],
    [
        ("COMPLETED", "annualReport", "BC1234567"),
        ("PAID", "changeOfAddress", "CP1234567"),
        ("PAID", "changeOfDirectors", "CP1234567"),
        ("COMPLETED", "changeOfAddress", "CP1234567"),
        ("COMPLETED", "changeOfDirectors", "CP1234567"),
    ],
)
def test_skips_notification(app, session, client, status, filing_type, identifier):
    """Assert that the legal name is changed."""
    # Setup
    filing = prep_maintenance_filing(session, identifier, "1", status, filing_type)
    token = "token"
    email_msg = {"email": {"filingId": filing.id, "type": f"{filing_type}", "option": status}}
    message = helper_create_cloud_event_envelope(data=email_msg)

    with patch.object(AccountService, "get_bearer_token", return_value=token):
        with patch.object(filing_notification, "_get_pdfs", return_value=[]):
            with patch.object(worker, "send_email", return_value="success") as mock_send_email:
                with patch.object(queue, "publish", return_value={}):
                    # TEST
                    rv = client.post("/", json=message)

                    # Check
                    assert rv.status_code == HTTPStatus.OK
                    assert not mock_send_email.call_args


def test_process_mras_email(app, session, client):
    """Assert that an MRAS email msg is processed correctly."""
    # Setup
    filing = prep_incorp_filing(session, "BC1234567", "1", "mras")
    token = "1"
    email_msg = {"email": {"filingId": filing.id, "type": "incorporationApplication", "option": "mras"}}
    message = helper_create_cloud_event_envelope(data=email_msg)

    with patch.object(AccountService, "get_bearer_token", return_value=token):
        with patch.object(worker, "send_email", return_value="success") as mock_send_email:
            with patch.object(queue, "publish", return_value={}):
                # TEST
                rv = client.post("/", json=message)

                # Check
                assert rv.status_code == HTTPStatus.OK

                assert (
                    mock_send_email.call_args[0][0]["content"]["subject"] == "BC Business Registry Partner Information"
                )
                assert mock_send_email.call_args[0][0]["recipients"] == "test@test.com"
                assert mock_send_email.call_args[0][0]["content"]["body"]
                assert mock_send_email.call_args[0][0]["content"]["attachments"] == []
                assert mock_send_email.call_args[0][1] == token


@pytest.mark.parametrize(
    ["option", "submitter_role"],
    [
        ("PAID", "staff"),
        ("COMPLETED", None),
    ],
)
def test_process_special_resolution_email(app, session, client, option, submitter_role):
    """Assert that an special resolution email msg is processed correctly."""
    # Setup
    filing = prep_cp_special_resolution_filing("CP1234567", "1", "CP", "TEST", submitter_role=submitter_role)
    token = "1"
    get_pdf_function = "get_paid_pdfs" if option == "PAID" else "get_completed_pdfs"
    email_msg = {"email": {"filingId": filing.id, "type": "specialResolution", "option": option}}
    message = helper_create_cloud_event_envelope(data=email_msg)

    with patch.object(AccountService, "get_bearer_token", return_value=token):
        with patch.object(special_resolution_notification, get_pdf_function, return_value=[]) as mock_get_pdfs:
            with patch.object(
                special_resolution_notification, "get_recipient_from_auth", return_value="recipient@email.com"
            ):
                with patch.object(
                    special_resolution_notification, "get_user_email_from_auth", return_value="user@email.com"
                ):
                    with patch.object(worker, "send_email", return_value="success") as mock_send_email:
                        with patch.object(queue, "publish", return_value={}):
                            # TEST
                            rv = client.post("/", json=message)

                            # Check
                            assert rv.status_code == HTTPStatus.OK

                            assert mock_get_pdfs.call_args[0][0] == token
                            assert mock_get_pdfs.call_args[0][1]["identifier"] == "CP1234567"
                            assert mock_get_pdfs.call_args[0][2] == filing

                            if option == "PAID":
                                assert (
                                    mock_send_email.call_args[0][0]["content"]["subject"]
                                    == "TEST - Confirmation of Special Resolution from the Business Registry"
                                )
                            else:
                                assert (
                                    mock_send_email.call_args[0][0]["content"]["subject"]
                                    == "TEST - Special Resolution Documents from the Business Registry"
                                )
                            assert "recipient@email.com" in mock_send_email.call_args[0][0]["recipients"]
                            if submitter_role:
                                assert f"{submitter_role}@email.com" in mock_send_email.call_args[0][0]["recipients"]
                            else:
                                assert "user@email.com" in mock_send_email.call_args[0][0]["recipients"]
                            assert mock_send_email.call_args[0][0]["content"]["body"]
                            assert mock_send_email.call_args[0][0]["content"]["attachments"] == []
                            assert mock_send_email.call_args[0][1] == token


@pytest.mark.parametrize(
    "option",
    [
        ("PAID"),
        ("COMPLETED"),
    ],
)
def test_process_correction_cp_sr_email(app, session, client, option):
    """Assert that a correction email msg is processed correctly."""
    # Setup
    identifier = "CP1234567"
    original_filing = prep_cp_special_resolution_filing(identifier, "1", "CP", "TEST", submitter_role=None)
    token = "1"
    business = LegalEntity.find_by_identifier(identifier)
    filing = prep_cp_special_resolution_correction_filing(
        session, business, original_filing.id, "1", option, "specialResolution"
    )
    email_msg = {"email": {"filingId": filing.id, "type": "correction", "option": option}}
    message = helper_create_cloud_event_envelope(data=email_msg)

    with patch.object(AccountService, "get_bearer_token", return_value=token):
        with patch.object(correction_notification, "_get_pdfs", return_value=[]):
            with patch.object(worker, "send_email", return_value="success") as mock_send_email:
                with patch.object(queue, "publish", return_value={}):
                    # TEST
                    rv = client.post("/", json=message)

                    # Check
                    assert rv.status_code == HTTPStatus.OK

                    if option == "PAID":
                        assert (
                            mock_send_email.call_args[0][0]["content"]["subject"] == "TEST - Confirmation of correction"
                        )
                    else:
                        assert (
                            mock_send_email.call_args[0][0]["content"]["subject"]
                            == "TEST - Correction Documents from the Business Registry"
                        )
                    assert "cp_sr@test.com" in mock_send_email.call_args[0][0]["recipients"]
                    assert mock_send_email.call_args[0][0]["content"]["body"]
                    assert mock_send_email.call_args[0][0]["content"]["attachments"] == []
                    assert mock_send_email.call_args[0][1] == token


def test_process_ar_reminder_email(app, session, client):
    """Assert that the ar reminder notification can be processed."""
    # Setup
    filing = prep_incorp_filing(session, "BC1234567", "1", "COMPLETED")
    business = LegalEntity.find_by_internal_id(filing.legal_entity_id)
    business.legal_type = "BC"
    business.legal_name = "test business"
    token = "token"
    email_msg = {
        "email": {
            "businessId": filing.legal_entity_id,
            "type": "annualReport",
            "option": "reminder",
            "arFee": "100",
            "arYear": "2021",
        }
    }
    message = helper_create_cloud_event_envelope(data=email_msg)

    with patch.object(AccountService, "get_bearer_token", return_value=token):
        with patch.object(ar_reminder_notification, "get_recipient_from_auth", return_value="test@test.com"):
            with patch.object(worker, "send_email", return_value="success") as mock_send_email:
                with patch.object(queue, "publish", return_value={}):
                    # TEST
                    rv = client.post("/", json=message)

                    # Check
                    assert rv.status_code == HTTPStatus.OK

                    call_args = mock_send_email.call_args
                    assert call_args[0][0]["content"]["subject"] == "test business 2021 Annual Report Reminder"
                    assert call_args[0][0]["recipients"] == "test@test.com"
                    assert call_args[0][0]["content"]["body"]
                    assert "Dye & Durham" not in call_args[0][0]["content"]["body"]
                    assert call_args[0][0]["content"]["attachments"] == []
                    assert call_args[0][1] == token


def test_process_bn_email(app, session, client):
    """Assert that a BN email msg is processed correctly."""
    # Setup
    identifier = "BC1234567"
    filing = prep_incorp_filing(session, identifier, "1", "bn")
    business = LegalEntity.find_by_identifier(identifier)
    email_msg = {"email": {"filingId": None, "type": "businessNumber", "option": "bn", "identifier": "BC1234567"}}
    message = helper_create_cloud_event_envelope(data=email_msg)

    # Sanity check
    assert filing.id
    assert business.id
    token = "1"

    with patch.object(AccountService, "get_bearer_token", return_value=token):
        with patch.object(worker, "send_email", return_value="success") as mock_send_email:
            with patch.object(queue, "publish", return_value={}):
                # TEST
                rv = client.post("/", json=message)

                # Check
                assert rv.status_code == HTTPStatus.OK

                assert "comp_party@email.com" in mock_send_email.call_args[0][0]["recipients"]
                assert "test@test.com" in mock_send_email.call_args[0][0]["recipients"]
                assert (
                    mock_send_email.call_args[0][0]["content"]["subject"]
                    == f"{business.legal_name} - Business Number Information"
                )
                assert mock_send_email.call_args[0][0]["content"]["body"]
                assert mock_send_email.call_args[0][0]["content"]["attachments"] == []


default_legal_name = "TEST COMP"
default_names_array = [{"name": default_legal_name, "state": "NE"}]


@pytest.mark.parametrize(
    ["option", "nr_number", "subject", "expiration_date", "refund_value", "expected_legal_name", "names"],
    [
        (
            "before-expiry",
            "NR 1234567",
            "Expiring Soon",
            "2021-07-20T00:00:00+00:00",
            None,
            "TEST2 Company Name",
            [{"name": "TEST Company Name", "state": "NE"}, {"name": "TEST2 Company Name", "state": "APPROVED"}],
        ),
        (
            "before-expiry",
            "NR 1234567",
            "Expiring Soon",
            "2021-07-20T00:00:00+00:00",
            None,
            "TEST3 Company Name",
            [{"name": "TEST3 Company Name", "state": "CONDITION"}, {"name": "TEST4 Company Name", "state": "NE"}],
        ),
        (
            "expired",
            "NR 1234567",
            "Expired",
            None,
            None,
            "TEST4 Company Name",
            [{"name": "TEST5 Company Name", "state": "NE"}, {"name": "TEST4 Company Name", "state": "APPROVED"}],
        ),
        (
            "renewal",
            "NR 1234567",
            "Confirmation of Renewal",
            "2021-07-20T00:00:00+00:00",
            None,
            None,
            default_names_array,
        ),
        ("upgrade", "NR 1234567", "Confirmation of Upgrade", None, None, None, default_names_array),
        ("refund", "NR 1234567", "Refund request confirmation", None, "123.45", None, default_names_array),
    ],
)
def test_nr_notification(
    app, session, client, option, nr_number, subject, expiration_date, refund_value, expected_legal_name, names
):
    """Assert that the nr notification can be processed."""
    # Setup
    nr_json = {
        "expirationDate": expiration_date,
        "names": names,
        "legalType": "BC",
        "applicants": {"emailAddress": "test@test.com"},
    }
    nr_response = MockResponse(nr_json, 200)
    token = "token"
    email_msg = {
        "id": "123456789",
        "type": "bc.registry.names.request",
        "source": f"/requests/{nr_number}",
        "identifier": nr_number,
        "data": {"request": {"nrNum": nr_number, "option": option, "refundValue": refund_value}},
    }
    message = helper_create_cloud_event_envelope(data=email_msg)

    with patch.object(AccountService, "get_bearer_token", return_value=token):
        with patch.object(NameXService, "query_nr_number", return_value=nr_response) as mock_query_nr_number:
            with patch.object(worker, "send_email", return_value="success") as mock_send_email:
                with patch.object(queue, "publish", return_value={}):
                    # TEST
                    rv = client.post("/", json=message)

                    # Check
                    assert rv.status_code == HTTPStatus.OK

                    call_args = mock_send_email.call_args
                    assert call_args[0][0]["content"]["subject"] == f"{nr_number} - {subject}"
                    assert call_args[0][0]["recipients"] == "test@test.com"
                    assert call_args[0][0]["content"]["body"]
                    if option == nr_notification.Option.REFUND.value:
                        assert f"${refund_value} CAD" in call_args[0][0]["content"]["body"]
                    assert call_args[0][0]["content"]["attachments"] == []
                    assert mock_query_nr_number.call_args[0][0] == nr_number
                    assert call_args[0][1] == token

                    if option == nr_notification.Option.BEFORE_EXPIRY.value:
                        assert nr_number in call_args[0][0]["content"]["body"]
                        assert expected_legal_name in call_args[0][0]["content"]["body"]
                        exp_date = datetime.fromisoformat(expiration_date)
                        exp_date_tz = LegislationDatetime.as_legislation_timezone(exp_date)
                        assert_expiration_date = LegislationDatetime.format_as_report_string(exp_date_tz)
                        assert assert_expiration_date in call_args[0][0]["content"]["body"]

                    if option == nr_notification.Option.EXPIRED.value:
                        assert nr_number in call_args[0][0]["content"]["body"]
                        assert expected_legal_name in call_args[0][0]["content"]["body"]


def test_nr_receipt_notification(app, session, client):
    """Assert that the nr payment notification can be processed."""
    # Setup
    nr_number = "NR 1234567"
    email_address = "test@test.com"
    nr_id = 12345
    nr_json = {"applicants": {"emailAddress": email_address}, "id": nr_id}
    nr_response = MockResponse(nr_json, 200)
    token = "token"
    payment_token = "1234"
    pdfs = ["test"]
    email_msg = {
        "id": "123456789",
        "type": "bc.registry.names.request",
        "source": f"/requests/{nr_number}",
        "identifier": nr_number,
        "data": {
            "request": {
                "header": {"nrNum": nr_number},
                "paymentToken": payment_token,
                "statusCode": "DRAFT",  # not used
            }
        },
    }
    message = helper_create_cloud_event_envelope(data=email_msg)

    with patch.object(AccountService, "get_bearer_token", return_value=token):
        with patch.object(NameXService, "query_nr_number", return_value=nr_response) as mock_query_nr_number:
            with patch.object(name_request, "get_nr_bearer_token", return_value=token):
                with patch.object(name_request, "_get_pdfs", return_value=pdfs) as mock_pdf:
                    with patch.object(worker, "send_email", return_value="success") as mock_send_email:
                        with patch.object(queue, "publish", return_value={}):
                            # TEST
                            rv = client.post("/", json=message)

                            # Check
                            assert rv.status_code == HTTPStatus.OK

                            assert mock_pdf.call_args[0][0] == nr_id
                            assert mock_pdf.call_args[0][1] == payment_token
                            assert mock_query_nr_number.call_args[0][0] == nr_number
                            call_args = mock_send_email.call_args
                            assert (
                                call_args[0][0]["content"]["subject"]
                                == f"{nr_number} - Receipt from Corporate Registry"
                            )
                            assert call_args[0][0]["recipients"] == email_address
                            assert call_args[0][0]["content"]["body"]
                            assert call_args[0][0]["content"]["attachments"] == pdfs
                            assert call_args[0][1] == token


@pytest.mark.parametrize(
    "email_msg",
    [
        ({}),
        (
            {
                "recipients": "",
                "requestBy": "test@test.ca",
                "content": {"subject": "test", "body": "test", "attachments": []},
            }
        ),
        ({"recipients": "", "requestBy": "test@test.ca", "content": {}}),
        (
            {
                "recipients": "",
                "requestBy": "test@test.ca",
                "content": {"subject": "test", "body": {}, "attachments": []},
            }
        ),
        ({"requestBy": "test@test.ca", "content": {"subject": "test", "body": "test", "attachments": []}}),
        ({"recipients": "test@test.ca", "requestBy": "test@test.ca"}),
        (
            {
                "recipients": "test@test.ca",
                "requestBy": "test@test.ca",
                "content": {"subject": "test", "attachments": []},
            }
        ),
    ],
)
def test_send_email_with_incomplete_payload(app, session, client, email_msg):
    """Assert that the email not have body can not be processed."""
    # Setup
    message = helper_create_cloud_event_envelope(data=email_msg)

    # TEST
    rv = client.post("/", json=message)

    # Check
    assert rv.status_code == HTTPStatus.OK


def helper_create_cloud_event_envelope(
    cloud_event_id: str = None,
    source: str = "fake-for-tests",
    subject: str = "fake-subject",
    type: str = "email",
    data: dict = {},
    pubsub_project_id: str = "PUBSUB_PROJECT_ID",
    subscription_id: str = "SUBSCRIPTION_ID",
    message_id: int = 1,
    envelope_id: int = 1,
    attributes: dict = {},
    ce: SimpleCloudEvent = None,
):
    if not data:
        data = {
            "email": {
                "type": "bn",
            }
        }
    if not ce:
        ce = SimpleCloudEvent(id=cloud_event_id, source=source, subject=subject, type=type, data=data)
    #
    # This needs to mimic the envelope created by GCP PubSb when call a resource
    #
    envelope = {
        "subscription": f"projects/{pubsub_project_id}/subscriptions/{subscription_id}",
        "message": {
            "data": base64.b64encode(to_queue_message(ce)).decode("UTF-8"),
            "messageId": str(message_id),
            "attributes": attributes,
        },
        "id": envelope_id,
    }
    return envelope
