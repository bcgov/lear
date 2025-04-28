import pytest


@pytest.fixture(scope='function', autouse=True)
def set_publish_mocks(request, mocker):
    # mock out the email sender and event publishing
    mocker.patch('business_filer.services.publish_event.PublishEvent.publish_email_message', return_value=None)
    mocker.patch('business_filer.services.publish_event.PublishEvent.publish_event', return_value=None)
    mocker.patch('business_filer.services.publish_event.PublishEvent.publish_mras_email', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)
