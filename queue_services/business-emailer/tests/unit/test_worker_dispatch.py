# Copyright © 2026 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
"""Dispatch-branch coverage for worker.process_email.

These tests mock every email processor's `process()` so we can verify the
routing logic in `process_email` without building real filings. They are
complementary to the integration-style tests in test_worker.py which exercise
processor internals.
"""
from unittest.mock import patch

import pytest
from simple_cloudevent import SimpleCloudEvent

from business_account.AccountService import AccountService
from business_model.models import Filing

from business_emailer.email_processors import (
    affiliation_notification,
    agm_extension_notification,
    agm_location_change_notification,
    amalgamation_notification,
    amalgamation_out_notification,
    appoint_receiver_notification,
    ar_reminder_notification,
    bn_notification,
    cease_receiver_notification,
    change_of_registration_notification,
    consent_amalgamation_out_notification,
    consent_continuation_out_notification,
    continuation_in_notification,
    continuation_out_notification,
    correction_notification,
    dissolution_notification,
    filing_notification,
    intent_to_liquidate_notification,
    intent_to_liquidate_notification as _intent_to_liquidate,  # noqa: F401 (keep alias import-safe)
    mras_notification,
    name_request,
    notice_of_withdrawal_notification,
    nr_notification,
    registration_notification,
    restoration_notification,
    special_resolution_notification,
)
from business_emailer.resources import business_emailer as worker
from business_emailer.services import flags


STUB_EMAIL = {
    "recipients": "stub@test.com",
    "content": {"subject": "stub", "body": "stub", "attachments": []},
}
TOKEN = "token"
COMPLETED = Filing.Status.COMPLETED.value


@pytest.fixture
def mock_send_email(mocker):
    """Patch worker.send_email and return the mock for assertions."""
    return mocker.patch.object(worker, "send_email", return_value="success")


@pytest.fixture(autouse=True)
def mock_bearer_token(mocker):
    """Every dispatch path calls AccountService.get_bearer_token() first."""
    mocker.patch.object(AccountService, "get_bearer_token", return_value=TOKEN)


def _ce(data, etype=None):
    """Build a SimpleCloudEvent. If etype is None, wraps data under 'email'."""
    if etype:
        return SimpleCloudEvent(type=etype, data=data)
    return SimpleCloudEvent(data=data)


# --------------------------------------------------------------------------- #
# bc.registry.* cloud-event types                                             #
# --------------------------------------------------------------------------- #

def test_affiliation_event_dispatches(app, session, mocker, mock_send_email):
    """bc.registry.affiliation routes to affiliation_notification.process."""
    mock_process = mocker.patch.object(affiliation_notification, "process", return_value=STUB_EMAIL)
    payload = {"some": "affiliation-data"}

    worker.process_email(_ce(payload, etype="bc.registry.affiliation"))

    mock_process.assert_called_once_with(payload, TOKEN)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


def test_bnmove_event_dispatches(app, session, mocker, mock_send_email):
    """bc.registry.bnmove routes to bn_notification.process_bn_move."""
    mock_process = mocker.patch.object(bn_notification, "process_bn_move", return_value=STUB_EMAIL)
    payload = {"some": "bn-move-data"}

    worker.process_email(_ce(payload, etype="bc.registry.bnmove"))

    mock_process.assert_called_once_with(payload, TOKEN)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


@pytest.mark.parametrize("option", [
    nr_notification.Option.BEFORE_EXPIRY.value,
    nr_notification.Option.EXPIRED.value,
    nr_notification.Option.RENEWAL.value,
    nr_notification.Option.UPGRADE.value,
    nr_notification.Option.REFUND.value,
])
def test_names_request_routes_to_nr_notification(app, session, mocker, mock_send_email, option):
    """bc.registry.names.request with a recognized option → nr_notification.process."""
    mock_process = mocker.patch.object(nr_notification, "process", return_value=STUB_EMAIL)
    payload = {"request": {"option": option}}

    worker.process_email(_ce(payload, etype="bc.registry.names.request"))

    mock_process.assert_called_once_with(payload, option)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


def test_names_request_falls_back_to_name_request(app, session, mocker, mock_send_email):
    """bc.registry.names.request without a matching option → name_request.process."""
    mock_nr = mocker.patch.object(nr_notification, "process", return_value=STUB_EMAIL)
    mock_name_request = mocker.patch.object(name_request, "process", return_value=STUB_EMAIL)
    payload = {"request": {"option": "something-unknown"}}

    worker.process_email(_ce(payload, etype="bc.registry.names.request"))

    mock_nr.assert_not_called()
    mock_name_request.assert_called_once_with(payload)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


def test_names_request_missing_option_falls_back(app, session, mocker, mock_send_email):
    """Missing option → name_request.process (covers the `if option and option in [...]` falsy branch)."""
    mock_name_request = mocker.patch.object(name_request, "process", return_value=STUB_EMAIL)
    payload = {"request": {}}

    worker.process_email(_ce(payload, etype="bc.registry.names.request"))

    mock_name_request.assert_called_once_with(payload)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


# --------------------------------------------------------------------------- #
# Inner email-dict dispatch (email_msg['email']['type'])                      #
# --------------------------------------------------------------------------- #

def test_business_number_dispatches(app, session, mocker, mock_send_email):
    mock_process = mocker.patch.object(bn_notification, "process", return_value=STUB_EMAIL)
    email = {"type": "businessNumber", "option": "whatever"}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_called_once_with(email)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


@pytest.mark.parametrize("etype", [
    "amalgamationApplication",
    "continuationIn",
    "incorporationApplication",
])
def test_mras_dispatch(app, session, mocker, mock_send_email, etype):
    """Any of the three filing types + option='mras' routes to mras_notification."""
    mock_process = mocker.patch.object(mras_notification, "process", return_value=STUB_EMAIL)
    email = {"type": etype, "option": "mras"}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_called_once_with(email)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


def test_ar_reminder_dispatch_with_flag_on(app, session, mocker, mock_send_email):
    mocker.patch.object(flags, "is_on", return_value=True)
    mock_process = mocker.patch.object(ar_reminder_notification, "process", return_value=STUB_EMAIL)
    email = {"type": "annualReport", "option": "reminder"}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_called_once_with(email, TOKEN, True)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


def test_ar_reminder_dispatch_with_flag_off(app, session, mocker, mock_send_email):
    mocker.patch.object(flags, "is_on", return_value=False)
    mock_process = mocker.patch.object(ar_reminder_notification, "process", return_value=STUB_EMAIL)
    email = {"type": "annualReport", "option": "reminder"}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_called_once_with(email, TOKEN, False)


def test_agm_location_change_completed_dispatches(app, session, mocker, mock_send_email):
    mock_process = mocker.patch.object(agm_location_change_notification, "process", return_value=STUB_EMAIL)
    email = {"type": "agmLocationChange", "option": COMPLETED}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_called_once_with(email, TOKEN)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


def test_agm_location_change_non_completed_is_skipped(app, session, mocker, mock_send_email):
    """Option != COMPLETED falls through to the `else` log-and-skip branch."""
    mock_process = mocker.patch.object(agm_location_change_notification, "process", return_value=STUB_EMAIL)
    email = {"type": "agmLocationChange", "option": "PAID"}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_not_called()
    mock_send_email.assert_not_called()


def test_agm_extension_completed_dispatches(app, session, mocker, mock_send_email):
    mock_process = mocker.patch.object(agm_extension_notification, "process", return_value=STUB_EMAIL)
    email = {"type": "agmExtension", "option": COMPLETED}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_called_once_with(email, TOKEN)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


def test_dissolution_dispatches(app, session, mocker, mock_send_email):
    mock_process = mocker.patch.object(dissolution_notification, "process", return_value=STUB_EMAIL)
    email = {"type": "dissolution", "option": COMPLETED}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_called_once_with(email, TOKEN)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


def test_registration_dispatches(app, session, mocker, mock_send_email):
    mock_process = mocker.patch.object(registration_notification, "process", return_value=STUB_EMAIL)
    email = {"type": "registration", "option": "PAID"}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_called_once_with(email, TOKEN)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


def test_restoration_dispatches(app, session, mocker, mock_send_email):
    mock_process = mocker.patch.object(restoration_notification, "process", return_value=STUB_EMAIL)
    email = {"type": "restoration", "option": COMPLETED}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_called_once_with(email, TOKEN)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


def test_change_of_registration_dispatches(app, session, mocker, mock_send_email):
    mock_process = mocker.patch.object(change_of_registration_notification, "process", return_value=STUB_EMAIL)
    email = {"type": "changeOfRegistration", "option": COMPLETED}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_called_once_with(email, TOKEN)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


def test_correction_dispatches(app, session, mocker, mock_send_email):
    mock_process = mocker.patch.object(correction_notification, "process", return_value=STUB_EMAIL)
    email = {"type": "correction", "option": "PAID"}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_called_once_with(email, TOKEN)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


def test_consent_amalgamation_out_dispatches(app, session, mocker, mock_send_email):
    mock_process = mocker.patch.object(consent_amalgamation_out_notification, "process", return_value=STUB_EMAIL)
    email = {"type": "consentAmalgamationOut", "option": COMPLETED}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_called_once_with(email, TOKEN)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


def test_amalgamation_out_dispatches(app, session, mocker, mock_send_email):
    mock_process = mocker.patch.object(amalgamation_out_notification, "process", return_value=STUB_EMAIL)
    email = {"type": "amalgamationOut", "option": COMPLETED}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_called_once_with(email, TOKEN)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


def test_consent_continuation_out_completed_dispatches(app, session, mocker, mock_send_email):
    mock_process = mocker.patch.object(consent_continuation_out_notification, "process", return_value=STUB_EMAIL)
    email = {"type": "consentContinuationOut", "option": COMPLETED}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_called_once_with(email, TOKEN)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


def test_consent_continuation_out_non_completed_skipped(app, session, mocker, mock_send_email):
    mock_process = mocker.patch.object(consent_continuation_out_notification, "process", return_value=STUB_EMAIL)
    email = {"type": "consentContinuationOut", "option": "PAID"}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_not_called()
    mock_send_email.assert_not_called()


def test_continuation_out_completed_dispatches(app, session, mocker, mock_send_email):
    mock_process = mocker.patch.object(continuation_out_notification, "process", return_value=STUB_EMAIL)
    email = {"type": "continuationOut", "option": COMPLETED}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_called_once_with(email, TOKEN)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


def test_special_resolution_dispatches(app, session, mocker, mock_send_email):
    mock_process = mocker.patch.object(special_resolution_notification, "process", return_value=STUB_EMAIL)
    email = {"type": "specialResolution", "option": "PAID"}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_called_once_with(email, TOKEN)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


def test_amalgamation_application_non_mras_dispatches(app, session, mocker, mock_send_email):
    """amalgamationApplication with a non-'mras' option hits the dedicated branch."""
    mock_process = mocker.patch.object(amalgamation_notification, "process", return_value=STUB_EMAIL)
    email = {"type": "amalgamationApplication", "option": COMPLETED}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_called_once_with(email, TOKEN)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


def test_continuation_in_non_mras_dispatches(app, session, mocker, mock_send_email):
    mock_process = mocker.patch.object(continuation_in_notification, "process", return_value=STUB_EMAIL)
    email = {"type": "continuationIn", "option": COMPLETED}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_called_once_with(email, TOKEN)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


def test_intent_to_liquidate_dispatches(app, session, mocker, mock_send_email):
    mock_process = mocker.patch.object(intent_to_liquidate_notification, "process", return_value=STUB_EMAIL)
    email = {"type": "intentToLiquidate", "option": COMPLETED}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_called_once_with(email, TOKEN)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


def test_notice_of_withdrawal_completed_dispatches(app, session, mocker, mock_send_email):
    mock_process = mocker.patch.object(notice_of_withdrawal_notification, "process", return_value=STUB_EMAIL)
    email = {"type": "noticeOfWithdrawal", "option": COMPLETED}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_called_once_with(email, TOKEN)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


def test_appoint_receiver_completed_dispatches(app, session, mocker, mock_send_email):
    mock_process = mocker.patch.object(appoint_receiver_notification, "process", return_value=STUB_EMAIL)
    email = {"type": "appointReceiver", "option": COMPLETED}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_called_once_with(email, TOKEN)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


def test_cease_receiver_completed_dispatches(app, session, mocker, mock_send_email):
    mock_process = mocker.patch.object(cease_receiver_notification, "process", return_value=STUB_EMAIL)
    email = {"type": "ceaseReceiver", "option": COMPLETED}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_called_once_with(email, TOKEN)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


# --------------------------------------------------------------------------- #
# FILING_TYPE_CONVERTER branch                                                #
# --------------------------------------------------------------------------- #

def test_filing_type_converter_dispatches(app, session, mocker, mock_send_email):
    """An etype in FILING_TYPE_CONVERTER (e.g. 'alteration') that isn't handled
    earlier routes to filing_notification.process."""
    mock_process = mocker.patch.object(filing_notification, "process", return_value=STUB_EMAIL)
    email = {"type": "alteration", "option": "PAID"}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_called_once_with(email, TOKEN)
    mock_send_email.assert_called_once_with(STUB_EMAIL, TOKEN)


def test_filing_type_converter_annual_report_completed_is_skipped(app, session, mocker, mock_send_email):
    """annualReport + COMPLETED short-circuits before filing_notification is called."""
    mock_process = mocker.patch.object(filing_notification, "process", return_value=STUB_EMAIL)
    email = {"type": "annualReport", "option": COMPLETED}

    worker.process_email(_ce({"email": email}))

    mock_process.assert_not_called()
    mock_send_email.assert_not_called()


def test_filing_type_converter_coops_none_return_is_skipped(app, session, mocker, mock_send_email):
    """When filing_notification.process returns None (coops filing), send_email is skipped."""
    mocker.patch.object(filing_notification, "process", return_value=None)
    email = {"type": "alteration", "option": "PAID"}

    worker.process_email(_ce({"email": email}))

    mock_send_email.assert_not_called()


# --------------------------------------------------------------------------- #
# Unrecognized types / dissolution furnishing skip                            #
# --------------------------------------------------------------------------- #

def test_unknown_email_type_is_skipped(app, session, mock_send_email):
    """An etype that matches none of the elif branches silently no-ops."""
    email = {"type": "totallyUnknownFilingType", "option": "PAID"}

    worker.process_email(_ce({"email": email}))

    mock_send_email.assert_not_called()


def test_dissolution_event_with_invalid_furnishing_name_is_skipped(app, session, mocker, mock_send_email):
    """bc.registry.dissolution with a furnishingName not in PROCESSABLE_FURNISHING_NAMES is skipped."""
    from business_emailer.email_processors import involuntary_dissolution_stage_1_notification as ivd
    mock_process = mocker.patch.object(ivd, "process", return_value=STUB_EMAIL)
    mock_post_process = mocker.patch.object(ivd, "post_process")
    payload = {"furnishing": {"furnishingName": "TOTALLY_NOT_A_REAL_FURNISHING"}}

    worker.process_email(_ce(payload, etype="bc.registry.dissolution"))

    mock_process.assert_not_called()
    mock_post_process.assert_not_called()
    mock_send_email.assert_not_called()


def test_dissolution_event_missing_furnishing_name_is_skipped(app, session, mocker, mock_send_email):
    """No furnishingName at all → skipped (covers the `if furnishing_name and ...` falsy branch)."""
    from business_emailer.email_processors import involuntary_dissolution_stage_1_notification as ivd
    mock_process = mocker.patch.object(ivd, "process", return_value=STUB_EMAIL)
    payload = {"furnishing": {}}

    worker.process_email(_ce(payload, etype="bc.registry.dissolution"))

    mock_process.assert_not_called()
    mock_send_email.assert_not_called()
