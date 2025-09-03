import pytest
from unittest.mock import patch
from legal_api.services.event_publisher import (
    publish_to_queue, _get_source_and_time
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


@pytest.mark.parametrize("platform,is_wrapped,patch_name", [
    ('GCP', True, 'legal_api.services.gcp_queue.publish'),
])
def test_publish_to_queue_with_none_identifier(app, platform, is_wrapped, patch_name):
    """Test publishing with no identifier provided."""
    test_data = {'test': 'data'}
    test_subject = app.config.get('BUSINESS_FILER_TOPIC')
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
    patch_name = 'legal_api.services.gcp_queue.publish'
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
