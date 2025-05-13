import pytest
from unittest.mock import patch
from legal_api.services.event_publisher import (
    publish_to_queue, _publish_to_nats, _publish_to_nats_with_wrapper,
    _publish_to_gcp, _get_source_and_time
)

@pytest.mark.parametrize("identifier,extra_on_expected_source", [
    ('BC123', '/BC123'),
    ('F83232', '/F83232'),
    (None, '/'),
])
def test_get_source_and_time(app, identifier, extra_on_expected_source):
    """Test getting source and time for message."""
    with app.app_context():
        source, time = _get_source_and_time(identifier=identifier)

        assert source == f"{app.config.get('LEGAL_API_BASE_URL')}{extra_on_expected_source}"
        assert time is not None
        assert isinstance(time, str)

@pytest.mark.parametrize("platform,is_wrapped,expected_function", [
    ('GCP', True, '_publish_to_gcp'),
    ('OCP', True, '_publish_to_nats_with_wrapper'),
    ('OCP', False, '_publish_to_nats'),
])
def test_publish_to_queue_routing(app, platform, is_wrapped, expected_function):
    """Test routing to different publish functions based on configuration."""
    with app.app_context():
        app.config['DEPLOYMENT_PLATFORM'] = platform
        test_data = {'test': 'data'}
        test_subject = 'test.subject'
        test_event_type = 'test.event'

        with patch(f'legal_api.services.event_publisher.{expected_function}') as mock_publish:
            publish_to_queue(
                data=test_data,
                subject=test_subject,
                event_type=test_event_type,
                message_id=None,
                identifier='BC123',
                is_wrapped=is_wrapped
            )

            mock_publish.assert_called_once()

def test_publish_to_nats_with_wrapper(app):
    """Test publishing wrapped message to NATS."""

    with app.app_context(), patch('legal_api.services.queue.publish_json') as mock_queue_publish:
        test_data = {'test': 'data'}
        test_subject = 'test.subject'
        test_event_type = 'test.event'
        test_message_id = 'test-id'

        _publish_to_nats_with_wrapper(
            data=test_data,
            subject=test_subject,
            identifier='123',
            event_type=test_event_type,
            message_id=test_message_id
        )

        mock_queue_publish.assert_called_once()
        args = mock_queue_publish.call_args[1]
        assert args['subject'] == test_subject
        assert args['payload']['type'] == test_event_type
        assert args['payload']['id'] == test_message_id
        assert args['payload']['data'] == test_data

def test_publish_to_nats():
    """Test publishing direct message to NATS."""
    with patch('legal_api.services.queue.publish_json') as mock_queue_publish:
        test_payload = {'test': 'data'}
        test_subject = 'test.subject'

        _publish_to_nats(payload=test_payload, subject=test_subject)

        mock_queue_publish.assert_called_once_with(
            subject=test_subject,
            payload=test_payload
        )

def test_publish_to_gcp(app):
    """Test publishing message to GCP."""
    with app.app_context(), \
        patch('legal_api.services.gcp_queue.publish') as mock_gcp_publish:

        test_data = {'test': 'data'}
        test_subject = app.config.get('NATS_FILER_SUBJECT')
        test_event_type = 'test.event'

        _publish_to_gcp(
            data=test_data,
            subject=test_subject,
            identifier='123',
            event_type=test_event_type
        )

        mock_gcp_publish.assert_called_once()
        args = mock_gcp_publish.call_args
        assert args[0][0] == app.config.get('BUSINESS_FILER_TOPIC')

@pytest.mark.parametrize("platform,is_wrapped,patch_name", [
    ('GCP', True, 'legal_api.services.gcp_queue.publish'),
    ('OCP', True, 'legal_api.services.queue.publish_json'),
    ('OCP', False, 'legal_api.services.queue.publish_json'),
])
def test_publish_to_queue_with_none_identifier(app, platform, is_wrapped, patch_name):
    """Test publishing with no identifier provided."""
    test_data = {'test': 'data'}
    test_subject = app.config.get('NATS_FILER_SUBJECT')
    test_event_type = 'test.event'

    with app.app_context(), patch(patch_name) as mock_gcp_publish:
        app.config['DEPLOYMENT_PLATFORM'] = platform
        publish_to_queue(
            data=test_data,
            subject=test_subject,
            event_type=test_event_type,
            message_id=None,
            identifier=None,
            is_wrapped=is_wrapped
        )

        mock_gcp_publish.assert_called_once()

def test_publish_to_queue_error_handling(app):
    """Test error handling in publish_to_queue."""
    with app.app_context(), \
        patch('legal_api.services.gcp_queue.publish', side_effect=Exception("Test error")), \
        patch('flask.current_app.logger.error') as mock_logger:
        app.config['DEPLOYMENT_PLATFORM'] = 'GCP'
        publish_to_queue(
            data={'test': 'data'},
            subject='test.subject',
            event_type='test.event',
            message_id=None,
            identifier='123'
        )

        mock_logger.assert_called()

@pytest.mark.parametrize("nats_subject,gcp_subject", [
    ('NATS_FILER_SUBJECT', 'BUSINESS_FILER_TOPIC'),
    ('NATS_ENTITY_EVENT_SUBJECT', 'BUSINESS_EVENTS_TOPIC'),
    ('NATS_EMAILER_SUBJECT', 'BUSINESS_EMAILER_TOPIC'),
])
def test_gcp_topic_mapping(app, nats_subject, gcp_subject):
    """Test GCP topic mapping from NATS subjects."""

    with app.app_context(), patch('legal_api.services.gcp_queue.publish') as mock_gcp_publish:
        app.config['DEPLOYMENT_PLATFORM'] = 'GCP'

        _publish_to_gcp(
            data={'test': 'data'},
            subject=app.config.get(nats_subject),
            identifier='123',
            event_type='test.event'
        )

        mock_gcp_publish.assert_called_once()
        assert mock_gcp_publish.call_args[0][0] ==app.config.get(gcp_subject)
