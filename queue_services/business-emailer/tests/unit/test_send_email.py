# Copyright © 2026 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
"""Unit tests for worker.send_email.

Covers exception paths, recipient-string dedup/parsing, the log_message
formatting block, and the requests.post call shape.
"""
from unittest.mock import MagicMock

import pytest

from business_emailer.exceptions import EmailException, QueueException
from business_emailer.resources import business_emailer as worker


NOTIFY_URL = "https://notify-api-url/"
TOKEN = "token"


def _valid_email(**overrides):
    """Build a minimally valid email dict; override any top-level/content key."""
    email = {
        "recipients": "test@test.com",
        "content": {"subject": "Subject", "body": "Body", "attachments": []},
    }
    content_overrides = overrides.pop("content", None)
    email.update(overrides)
    if content_overrides is not None:
        email["content"].update(content_overrides)
    return email


@pytest.fixture
def mock_post(mocker):
    """Mock requests.post inside the worker module; default to a 200 response."""
    mock = mocker.patch("business_emailer.resources.business_emailer.requests.post")
    mock.return_value = MagicMock(status_code=200)
    return mock


@pytest.fixture
def mock_logger_debug(app, mocker):
    """Patch the Flask app logger's debug method.

    `current_app.logger` resolves to `app.logger` under the test app context,
    so intercepting here captures every debug call made from send_email.
    """
    return mocker.patch.object(app.logger, "debug")


@pytest.fixture(autouse=True)
def _notify_url(app, monkeypatch):
    """Force a known NOTIFY_API_URL so we can assert the requests.post URL."""
    monkeypatch.setitem(app.config, "NOTIFY_API_URL", NOTIFY_URL)


# --------------------------------------------------------------------------- #
# Exception paths                                                             #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("email", [
    None,
    {},
    {"content": {"body": "x"}},                                   # missing 'recipients'
    {"recipients": "a@b.com"},                                    # missing 'content'
    {"recipients": "a@b.com", "content": {"subject": "s"}},       # missing 'body' in content
])
def test_send_email_missing_required_keys_raises(app, email, mock_post):
    """First guard: any required key missing → QueueException ('empty')."""
    with pytest.raises(QueueException) as exc:
        worker.send_email(email, TOKEN)
    assert "required email object(s) is empty" in str(exc.value)
    mock_post.assert_not_called()


@pytest.mark.parametrize("email", [
    {"recipients": "", "content": {"body": "x"}},                 # empty recipients
    {"recipients": "a@b.com", "content": {"body": ""}},           # empty body
])
def test_send_email_empty_required_values_raises(app, email, mock_post):
    """Second guard: empty recipients/content/body → QueueException ('missing')."""
    with pytest.raises(QueueException) as exc:
        worker.send_email(email, TOKEN)
    assert "required email object(s) is missing" in str(exc.value)
    mock_post.assert_not_called()


def test_send_email_non_200_response_raises_email_exception(app, mock_post):
    """Notify API non-200 → EmailException."""
    mock_post.return_value = MagicMock(status_code=500)

    with pytest.raises(EmailException) as exc:
        worker.send_email(_valid_email(), TOKEN)
    assert "Unsuccessful response when sending email" in str(exc.value)


def test_send_email_requests_raises_wrapped_as_email_exception(app, mock_post):
    """Any exception from requests.post is converted to EmailException."""
    mock_post.side_effect = ConnectionError("network down")

    with pytest.raises(EmailException) as exc:
        worker.send_email(_valid_email(), TOKEN)
    assert "Unsuccessful response when sending email" in str(exc.value)


# --------------------------------------------------------------------------- #
# Recipient string handling (single / multiple / dedup / whitespace / empty)  #
# --------------------------------------------------------------------------- #

def test_send_email_single_recipient_unchanged(app, mock_post):
    email = _valid_email(recipients="only@test.com")

    worker.send_email(email, TOKEN)

    posted = mock_post.call_args.kwargs["json"]
    assert posted["recipients"] == "only@test.com"


def test_send_email_single_recipient_whitespace_stripped(app, mock_post):
    email = _valid_email(recipients="   only@test.com   ")

    worker.send_email(email, TOKEN)

    posted = mock_post.call_args.kwargs["json"]
    assert posted["recipients"] == "only@test.com"


def test_send_email_multiple_recipients_deduped(app, mock_post):
    email = _valid_email(recipients="a@test.com, b@test.com, a@test.com")

    worker.send_email(email, TOKEN)

    posted_recipients = mock_post.call_args.kwargs["json"]["recipients"]
    # set ordering is not deterministic; assert membership instead
    assert sorted(r.strip() for r in posted_recipients.split(",")) == ["a@test.com", "b@test.com"]


def test_send_email_multiple_recipients_whitespace_stripped(app, mock_post):
    email = _valid_email(recipients="  a@test.com  ,   b@test.com  ")

    worker.send_email(email, TOKEN)

    posted_recipients = mock_post.call_args.kwargs["json"]["recipients"]
    assert sorted(r.strip() for r in posted_recipients.split(",")) == ["a@test.com", "b@test.com"]


def test_send_email_multiple_recipients_empty_entries_filtered(app, mock_post):
    email = _valid_email(recipients="a@test.com, , b@test.com, ")

    worker.send_email(email, TOKEN)

    posted_recipients = mock_post.call_args.kwargs["json"]["recipients"]
    parts = [r.strip() for r in posted_recipients.split(",")]
    assert sorted(parts) == ["a@test.com", "b@test.com"]
    assert "" not in parts


def test_send_email_list_recipients_not_mangled(app, mock_post):
    """Non-string recipients skip the dedup branch entirely."""
    email = _valid_email(recipients=["a@test.com", "b@test.com"])

    worker.send_email(email, TOKEN)

    posted_recipients = mock_post.call_args.kwargs["json"]["recipients"]
    assert posted_recipients == ["a@test.com", "b@test.com"]


# --------------------------------------------------------------------------- #
# requests.post invocation shape                                              #
# --------------------------------------------------------------------------- #

def test_send_email_posts_expected_json_and_headers(app, mock_post):
    email = _valid_email(
        recipients="only@test.com",
        content={"subject": "Hi", "body": "Hello", "attachments": [{"fileName": "f.pdf"}]},
    )

    worker.send_email(email, TOKEN)

    assert mock_post.call_count == 1
    args, kwargs = mock_post.call_args
    assert args == (NOTIFY_URL,)
    assert kwargs["json"] is email  # posted as-is
    assert kwargs["json"]["content"]["subject"] == "Hi"
    assert kwargs["json"]["content"]["body"] == "Hello"
    assert kwargs["json"]["content"]["attachments"] == [{"fileName": "f.pdf"}]
    assert kwargs["headers"] == {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}",
    }


def test_send_email_200_returns_normally(app, mock_post):
    """Happy path: no exception raised."""
    worker.send_email(_valid_email(), TOKEN)  # does not raise


# --------------------------------------------------------------------------- #
# log_message formatting — the block of lines the user called out             #
# --------------------------------------------------------------------------- #

def _get_log_message(mock_debug):
    """Return the first positional arg of the first debug call in the try block."""
    assert mock_debug.call_args_list, "logger.debug was never called"
    return mock_debug.call_args_list[0].args[0]


def test_log_message_short_subject_and_recipients(app, mock_post, mock_logger_debug):
    email = _valid_email(
        recipients="only@test.com",
        content={"subject": "Hello", "body": "Body", "attachments": []},
    )

    worker.send_email(email, TOKEN)

    log_message = _get_log_message(mock_logger_debug)
    assert log_message == "Sending email with subject 'Hello' and 0 attachments to: only@test.com"


def test_log_message_attachment_count(app, mock_post, mock_logger_debug):
    email = _valid_email(
        content={
            "subject": "s", "body": "b",
            "attachments": [{"fileName": "a"}, {"fileName": "b"}, {"fileName": "c"}],
        },
    )

    worker.send_email(email, TOKEN)

    assert "and 3 attachments" in _get_log_message(mock_logger_debug)


def test_log_message_no_attachments_key(app, mock_post, mock_logger_debug):
    """content without 'attachments' key → count falls back to 0."""
    email = _valid_email(content={"subject": "s", "body": "b"})
    email["content"].pop("attachments", None)

    worker.send_email(email, TOKEN)

    assert "and 0 attachments" in _get_log_message(mock_logger_debug)


def test_log_message_missing_subject_falls_back_to_empty(app, mock_post, mock_logger_debug):
    """Missing 'subject' key → subject_display == '-empty-'."""
    email = _valid_email(content={"body": "b", "attachments": []})
    email["content"].pop("subject", None)

    worker.send_email(email, TOKEN)

    assert "subject '-empty-'" in _get_log_message(mock_logger_debug)


def test_log_message_truncates_long_subject(app, mock_post, mock_logger_debug):
    """Subject > 50 chars is truncated to 50 chars + '...'."""
    long_subject = "A" * 60
    email = _valid_email(content={"subject": long_subject, "body": "b", "attachments": []})

    worker.send_email(email, TOKEN)

    log_message = _get_log_message(mock_logger_debug)
    assert f"subject '{'A' * 50}...'" in log_message
    # full subject is NOT present (would be 60 A's)
    assert "A" * 60 not in log_message


def test_log_message_does_not_truncate_subject_at_exactly_50(app, mock_post, mock_logger_debug):
    """Boundary: subject of exactly 50 chars is shown verbatim, no '...'."""
    subject_50 = "A" * 50
    email = _valid_email(content={"subject": subject_50, "body": "b", "attachments": []})

    worker.send_email(email, TOKEN)

    log_message = _get_log_message(mock_logger_debug)
    assert f"subject '{subject_50}'" in log_message
    assert "..." not in log_message


def test_log_message_truncates_long_recipients(app, mock_post, mock_logger_debug):
    """Recipients string > 100 chars is truncated to 100 chars + '...'."""
    # 12 emails of 11 chars + ", " separators = ~130 chars after dedup
    recipients = ", ".join(f"a{i:02d}@test.com" for i in range(12))
    assert len(recipients) > 100
    email = _valid_email(recipients=recipients)

    worker.send_email(email, TOKEN)

    log_message = _get_log_message(mock_logger_debug)
    # The displayed substring ends with '...'; check the truncation marker is present
    # and that the full recipients string is NOT wholly in the log message.
    posted_recipients = mock_post.call_args.kwargs["json"]["recipients"]
    assert posted_recipients[:100] + "..." in log_message
    assert posted_recipients not in log_message


def test_log_message_short_recipients_not_truncated(app, mock_post, mock_logger_debug):
    email = _valid_email(recipients="a@b.com")

    worker.send_email(email, TOKEN)

    log_message = _get_log_message(mock_logger_debug)
    assert "to: a@b.com" in log_message
    assert "..." not in log_message
