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
"""The Test Suites to ensure that the worker is operating correctly."""
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from business_model.models import Business, Filing
from flask import Flask
from simple_cloudevent import from_queue_message

from email_reminder import flags
from email_reminder.services.flags import Flags
from email_reminder.worker import (
    AccountService,
    find_and_send_ar_reminder,
    gcp_queue,
    get_ar_fee,
    get_businesses,
    run,
    send_email,
    send_outstanding_bcomps_ar_reminder,
)

from . import factory_business


def assert_publish_mock(app: Flask, mock: MagicMock, business_id: str, ar_fee: str, ar_year: str):
    """Assert the publish mock was called with the expected values."""
    assert mock.call_args[0][0] == app.config["BUSINESS_EMAILER_TOPIC"]
    assert mock.call_args[0][1]
    email_msg = from_queue_message(mock.call_args[0][1])
    assert email_msg.source == "emailReminderJob"
    assert email_msg.subject == "filing"
    assert email_msg.type == "bc.registry.reminder.annualReport"
    assert email_msg.data.get("email", {}).get("businessId") == business_id
    assert email_msg.data.get("email", {}).get("arFee") == ar_fee
    assert email_msg.data.get("email", {}).get("arYear") == ar_year


def test_send_email(app: Flask):
    """Assert the send_email method works as expected."""
    business_id = "1234"
    ar_fee = "43.50"
    ar_year = "2025"
    with patch.object(gcp_queue, "publish", return_value=None) as email_publish_mock:
        send_email(business_id, ar_fee, ar_year)
        email_publish_mock.assert_called()
        assert_publish_mock(app, email_publish_mock, business_id, ar_fee, ar_year)


def test_send_email_reraises_queue_error(app: Flask):
    """Assert send_email logs and reraises queue publish errors."""
    error = Exception("queue publish failed")
    with patch.object(gcp_queue, "publish", side_effect=error), \
         patch.object(app.logger, "error") as logger_error, \
         pytest.raises(Exception, match="queue publish failed"):
        send_email("1234", "43.50", "2025")

    logger_error.assert_called_once()


def test_get_ar_fee(app: Flask):
    """Assert get_ar_fee calls the pay API and returns the filing fee."""
    legal_type = Business.LegalTypes.BCOMP.value
    filing_type_code = Filing.FILINGS["annualReport"]["codes"][legal_type]
    expected_fee = "43.50"
    expected_url = f"{app.config['PAYMENT_SVC_FEES_URL']}/{legal_type}/{filing_type_code}"
    mock_response = MagicMock()
    mock_response.json.return_value = {"filingFees": expected_fee}

    with patch("email_reminder.worker.requests.get", return_value=mock_response) as requests_get:
        ar_fee = get_ar_fee(legal_type, "token")

    assert ar_fee == expected_fee
    requests_get.assert_called_once_with(
        url=expected_url,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer token",
            "App-Name": "email-reminder-job",
        },
        timeout=30,
    )

GET_BUSINESS_CASES = [
    pytest.param(
        {
            "founding_date": datetime.now(UTC),
            "reminder_year": None,
            "rest_expiry_date": None,
            "in_liquidation": False,
            "state": Business.State.ACTIVE,
            "expected": False,
        },
        id="active_new_business",
    ),
    pytest.param(
        {
            "founding_date": datetime.now(UTC) - timedelta(days=365),
            "reminder_year": None,
            "rest_expiry_date": None,
            "in_liquidation": False,
            "state": Business.State.ACTIVE,
            "expected": True,
        },
        id="active_year_old_business",
    ),
    pytest.param(
        {
            "founding_date": datetime.now(UTC) - timedelta(days=365),
            "reminder_year": datetime.now(UTC).year,
            "rest_expiry_date": None,
            "in_liquidation": False,
            "state": Business.State.ACTIVE,
            "expected": False,
        },
        id="active_year_old_business_with_reminder_year",
    ),
    pytest.param(
        {
            "founding_date": datetime.now(UTC) - timedelta(days=730),
            "reminder_year": (datetime.now(UTC) - timedelta(days=730)).year,
            "rest_expiry_date": None,
            "in_liquidation": False,
            "state": Business.State.ACTIVE,
            "expected": True,
        },
        id="active_2year_old_business_with_old_reminder_year",
    ),
    pytest.param(
        {
            "founding_date": datetime.now(UTC) - timedelta(days=730),
            "reminder_year": (datetime.now(UTC) - timedelta(days=364)).year,
            "rest_expiry_date": None,
            "in_liquidation": False,
            "state": Business.State.ACTIVE,
            "expected": True,
        },
        id="active_2year_old_business_with_reminder_year",
    ),
    pytest.param(
        {
            "founding_date": datetime.now(UTC) - timedelta(days=730),
            "reminder_year": datetime.now(UTC).year,
            "rest_expiry_date": None,
            "in_liquidation": False,
            "state": Business.State.ACTIVE,
            "expected": False,
        },
        id="active_2year_old_business_with_current_reminder_year",
    ),
    pytest.param(
        {
            "founding_date": datetime.now(UTC) - timedelta(days=365),
            "reminder_year": None,
            "rest_expiry_date": datetime.now(UTC) + timedelta(days=10),
            "in_liquidation": False,
            "state": Business.State.ACTIVE,
            "expected": False,
        },
        id="active_year_old_business_with_restoration",
    ),
    pytest.param(
        {
            "founding_date": datetime.now(UTC) - timedelta(days=365),
            "reminder_year": None,
            "rest_expiry_date": None,
            "in_liquidation": True,
            "state": Business.State.ACTIVE,
            "expected": False,
        },
        id="active_year_old_business_in_liquidation",
    ),
    pytest.param(
        {
            "founding_date": datetime.now(UTC) - timedelta(days=365),
            "reminder_year": None,
            "rest_expiry_date": None,
            "in_liquidation": False,
            "state": Business.State.HISTORICAL,
            "expected": False,
        },
        id="historical_year_old_business",
    ),
]


@pytest.mark.parametrize("case", GET_BUSINESS_CASES)
def test_get_businesses(app, session, case):
    """Assert the get_businesses method works as expected."""
    business = factory_business(
        identifier="BC1234567",
        founding_date=case["founding_date"],
        last_ar_reminder_year=case["reminder_year"],
        restoration_expiry_date=case["rest_expiry_date"],
        state=case["state"],
        in_liquidation=case["in_liquidation"],
    )
    resp = get_businesses([business.legal_type])
    if case["expected"]:
        assert len(resp.items) == 1
        assert resp.items[0].id == business.id
    else:
        assert len(resp.items) == 0

AR_REMINDER_CASES = [
    pytest.param(
        {
            "ld_flag_value": False,
            "legal_type": Business.LegalTypes.BCOMP.value,
            "last_reminder_year": 2023,
            "expected": True,
        },
        id="BEN_flag_off",
    ),
    pytest.param(
        {
            "ld_flag_value": True,
            "legal_type": Business.LegalTypes.BCOMP.value,
            "last_reminder_year": 2023,
            "expected": True,
        },
        id="BEN_flag_on",
    ),
    pytest.param(
        {
            "ld_flag_value": False,
            "legal_type": Business.LegalTypes.COMP.value,
            "last_reminder_year": 2023,
            "expected": False,
        },
        id="BC_flag_off",
    ),
    pytest.param(
        {
            "ld_flag_value": True,
            "legal_type": Business.LegalTypes.COMP.value,
            "last_reminder_year": 2023,
            "expected": True,
        },
        id="BC_flag_on",
    ),
]


@pytest.mark.parametrize("case", AR_REMINDER_CASES)
def test_find_and_send_ar_reminder(ld, app, session, case):
    """Assert the find_and_send_ar_reminder method works as expected."""
    ld.update(ld.flag("enable-bc-ccc-ulc-email-reminder").variation_for_all(case["ld_flag_value"]))
    flags.init_app(app, ld)

    business = factory_business(
        identifier="BC1234567",
        entity_type=case["legal_type"],
        last_ar_reminder_year=case["last_reminder_year"],
    )
    test_fee = "43.50"
    with patch.object(AccountService, "get_bearer_token", return_value="token"), \
         patch.object(gcp_queue, "publish", return_value=None) as publish_mock, \
         patch("email_reminder.worker.get_ar_fee", return_value=test_fee):
        find_and_send_ar_reminder()
        if not case["expected"]:
            publish_mock.assert_not_called()
        else:
            publish_mock.assert_called()
            ar_year = str((case["last_reminder_year"] or business.founding_date.year) + 1)
            assert_publish_mock(app, publish_mock, business.id, test_fee, ar_year)


def test_find_and_send_ar_reminder_logs_send_error(ld, app, session):
    """Assert find_and_send_ar_reminder logs and continues when queueing a business fails."""
    ld.update(ld.flag("enable-bc-ccc-ulc-email-reminder").variation_for_all(False))
    flags.init_app(app, ld)

    business = factory_business(
        identifier="BC1234567",
        entity_type=Business.LegalTypes.BCOMP.value,
        last_ar_reminder_year=2023,
    )

    with patch.object(AccountService, "get_bearer_token", return_value="token"), \
        patch("email_reminder.worker.get_ar_fee", return_value="43.50"), \
        patch("email_reminder.worker.send_email", side_effect=Exception("publish failed")), \
        patch.object(app.logger, "error") as logger_error:
        find_and_send_ar_reminder()

    logger_error.assert_any_call("Error sending email reminder for %s", business.identifier)


def test_find_and_send_ar_reminder_logs_top_level_error(app):
    """Assert find_and_send_ar_reminder logs top-level setup failures."""
    error = Exception("token failure")
    with patch.object(AccountService, "get_bearer_token", side_effect=error), \
        patch.object(app.logger, "error") as logger_error:
        find_and_send_ar_reminder()

    assert logger_error.call_args[0][0] is error


@pytest.mark.parametrize("_test_name, legal_type, last_ar_year, expected",[
    ("BEN_publish", Business.LegalTypes.BCOMP.value, 2023, True),
    ("BEN_no_ar_publish", Business.LegalTypes.BCOMP.value, None, True),
    ("BEN_no_publish", Business.LegalTypes.BCOMP.value, datetime.now(UTC).year, False),
    ("BC_no_publish", Business.LegalTypes.COMP.value, 2023, False),
])
def test_send_outstanding_bcomps_ar_reminder(app, session, _test_name, legal_type, last_ar_year, expected):
    """Assert the send_outstanding_bcomps_ar_reminder method works as expected."""
    ar_date = datetime(year=last_ar_year, month=1, day=1, tzinfo=UTC) if last_ar_year else None
    business = factory_business(identifier="BC1234567",
                                entity_type=legal_type,
                                last_ar_date=ar_date)
    test_fee = "43.50"
    with patch.object(AccountService, "get_bearer_token", return_value="token"),\
        patch.object(gcp_queue, "publish", return_value=None) as publish_mock,\
            patch("email_reminder.worker.get_ar_fee", return_value=test_fee):
                send_outstanding_bcomps_ar_reminder()
                if not expected:
                    publish_mock.assert_not_called()
                else:
                    publish_mock.assert_called()
                    ar_year = str((last_ar_year or business.founding_date.year) + 1)
                    assert_publish_mock(app, publish_mock, business.id, test_fee, ar_year)


def test_send_outstanding_bcomps_ar_reminder_logs_top_level_error(app):
    """Assert send_outstanding_bcomps_ar_reminder logs top-level setup failures."""
    error = Exception("token failure")
    with patch.object(AccountService, "get_bearer_token", side_effect=error), \
        patch.object(app.logger, "error") as logger_error:
        send_outstanding_bcomps_ar_reminder()

    assert logger_error.call_args[0][0] is error

@pytest.mark.parametrize("_test_name, config_value, expected",[
    ("run_find_and_send_ar_reminder", None, "find_and_send_ar_reminder"),
    ("run_send_outstanding_bcomps_ar_reminder", "send.outstanding.bcomps", "send_outstanding_bcomps_ar_reminder"),
])
def test_run(app, _test_name, config_value, expected):
    """Assert the run method works as expected."""
    with patch("email_reminder.worker.find_and_send_ar_reminder", return_value=None) as mock_1,\
        patch("email_reminder.worker.send_outstanding_bcomps_ar_reminder", return_value=None) as mock_2:
            app.config["SEND_OUTSTANDING_BCOMPS"] = config_value
            run()
            if expected == "find_and_send_ar_reminder":
                mock_1.assert_called()
            else:
                mock_2.assert_called()


def test_flags_constructor_initializes_app():
    """Assert Flags(app) initializes the app immediately."""
    test_app = Flask("flags-constructor")

    with patch.object(Flags, "init_app", autospec=True) as init_app:
        flag_service = Flags(test_app)

    init_app.assert_called_once_with(flag_service, test_app)


def test_flags_init_app_with_sdk_key_registers_client():
    """Assert Flags.init_app registers an initialized LaunchDarkly client."""
    test_app = Flask("flags-sdk")
    test_app.config["LD_SDK_KEY"] = "sdk-key"
    client = MagicMock()
    client.is_initialized.return_value = True

    with patch("email_reminder.services.flags.ldclient.set_config") as set_config, \
        patch("email_reminder.services.flags.ldclient.get", return_value=client):
        Flags().init_app(test_app)

    set_config.assert_called_once()
    assert test_app.extensions[Flags.COMPONENT_NAME] is client


def test_flags_get_client_returns_none_when_ldclient_get_fails():
    """Assert Flags.get_client returns None when the fallback client lookup fails."""
    test_app = Flask("flags-get-client")

    with test_app.app_context(), \
        patch("email_reminder.services.flags.ldclient.get", side_effect=Exception("ld unavailable")):
        assert Flags.get_client() is None


def test_flags_is_on_returns_false_when_value_fails():
    """Assert Flags.is_on returns False when value lookup raises."""
    test_app = Flask("flags-is-on")

    with test_app.app_context(), patch.object(Flags, "value", side_effect=Exception("flag failure")):
        assert Flags.is_on("enable-bc-ccc-ulc-email-reminder") is False


def test_flags_value_returns_none_when_variation_fails():
    """Assert Flags.value returns None when variation lookup raises."""
    test_app = Flask("flags-value")
    client = MagicMock()
    client.variation.side_effect = Exception("variation failure")

    with test_app.app_context(), patch.object(Flags, "get_client", return_value=client):
        assert Flags.value("enable-bc-ccc-ulc-email-reminder") is None
