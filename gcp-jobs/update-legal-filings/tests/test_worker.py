from unittest.mock import MagicMock, patch

from update_legal_filings.worker import publish_queue_events, update_business_nos


@patch("update_legal_filings.worker.gcp_queue.publish")
@patch("update_legal_filings.worker.to_queue_message")
@patch("update_legal_filings.worker._get_ce")
def test_publish_queue_events_success(mock_get_ce, mock_to_queue_message, mock_gcp_publish, app):
    mock_get_ce.return_value = MagicMock()
    mock_to_queue_message.return_value = "queue_message"
    mock_gcp_publish.return_value = None

    tax_ids = {"123": "value1", "456": "value2"}
    publish_queue_events(tax_ids)

    assert mock_get_ce.call_count == len(tax_ids) * 2
    assert mock_to_queue_message.call_count == len(tax_ids) * 2
    assert mock_gcp_publish.call_count == len(tax_ids) * 2


@patch("update_legal_filings.worker.gcp_queue.publish")
@patch("update_legal_filings.worker.to_queue_message")
@patch("update_legal_filings.worker._get_ce")
def test_publish_queue_events_calls_correct_topics(mock_get_ce, mock_to_queue_message, mock_gcp_publish, app):
    mock_get_ce.return_value = MagicMock()
    mock_to_queue_message.return_value = "queue_message"
    mock_gcp_publish.return_value = None

    tax_ids = {"123": "value1"}
    publish_queue_events(tax_ids)

    # Verify that gcp_queue.publish was called with the correct topics
    emailer_topic = app.config["BUSINESS_EMAILER_TOPIC"]
    events_topic = app.config["BUSINESS_EVENTS_TOPIC"]
    mock_gcp_publish.assert_any_call(emailer_topic, "queue_message")
    mock_gcp_publish.assert_any_call(events_topic, "queue_message")


@patch("update_legal_filings.worker.requests.post")
@patch("update_legal_filings.worker.requests.get")
@patch("update_legal_filings.worker.AccountService.get_bearer_token")
@patch("update_legal_filings.worker.publish_queue_events")
@patch("update_legal_filings.worker.current_app.logger.error")
def test_update_business_nos_success(mock_logger_error, mock_publish_queue_events, mock_get_bearer_token, mock_requests_get, mock_requests_post, app):
    mock_get_bearer_token.return_value = "test_token"
    mock_requests_get.side_effect = [
        MagicMock(status_code=200, json=MagicMock(return_value={"identifiers": ["123", "456"]})),
        MagicMock(status_code=200, json=MagicMock(return_value={"123": "tax_id_123", "456": "tax_id_456"}))
    ]
    mock_requests_post.return_value = MagicMock(status_code=201)
    mock_publish_queue_events.return_value = None

    update_business_nos()

    assert mock_requests_get.call_count == 2
    assert mock_requests_post.call_count == 1
    mock_publish_queue_events.assert_called_once()
    mock_logger_error.assert_not_called()
