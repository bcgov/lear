from unittest.mock import patch

from expired_limited_restoration.worker import run_job


@patch("expired_limited_restoration.worker.create_put_back_off_filing")
@patch("expired_limited_restoration.worker.get_businesses_to_process")
@patch("expired_limited_restoration.worker.current_app")
def test_run_job_success(mock_current_app, mock_get_businesses, mock_create_filing, app):
    business_ids = ["BUS123", "BUS456", "BUS789"]
    mock_get_businesses.return_value = business_ids
    mock_create_filing.return_value = {"filing": {"header": {"filingId": 12345}}}

    run_job()

    mock_get_businesses.assert_called_once()
    assert mock_create_filing.call_count == len(business_ids)
    mock_current_app.logger.debug.assert_any_call(
        "Successfully created put back off filing 12345 for BUS123"
    )
    mock_current_app.logger.debug.assert_any_call(
        "Successfully created put back off filing 12345 for BUS456"
    )


@patch("expired_limited_restoration.worker.create_put_back_off_filing")
@patch("expired_limited_restoration.worker.get_businesses_to_process")
@patch("expired_limited_restoration.worker.current_app")
def test_run_job_no_businesses(mock_current_app, mock_get_businesses, mock_create_filing, app):
    mock_get_businesses.return_value = []

    run_job()

    mock_get_businesses.assert_called_once()
    mock_create_filing.assert_not_called()
    mock_current_app.logger.debug.assert_called_with("No businesses to process")


@patch("expired_limited_restoration.worker.create_put_back_off_filing")
@patch("expired_limited_restoration.worker.get_businesses_to_process")
@patch("expired_limited_restoration.worker.current_app")
def test_run_job_filing_creation_failure(mock_current_app, mock_get_businesses, mock_create_filing, app):
    businesses = ["BUS123", "BUS456", "BUS789"]
    mock_get_businesses.return_value =businesses
    mock_create_filing.side_effect = Exception("Mocked filing creation failure")

    run_job()

    mock_get_businesses.assert_called_once()
    assert mock_create_filing.call_count == len(businesses)
    mock_current_app.logger.error.assert_any_call(
        "Error processing business BUS123: Mocked filing creation failure"
    )
    mock_current_app.logger.error.assert_any_call(
        "Error processing business BUS456: Mocked filing creation failure"
    )


@patch("expired_limited_restoration.worker.create_put_back_off_filing")
@patch("expired_limited_restoration.worker.get_businesses_to_process")
@patch("expired_limited_restoration.worker.current_app")
def test_run_job_general_failure(mock_current_app, mock_get_businesses, mock_create_filing, app):
    mock_get_businesses.side_effect = Exception("Mocked general failure")

    run_job()

    mock_get_businesses.assert_called_once()
    mock_create_filing.assert_not_called()
    mock_current_app.logger.error.assert_any_call("Job failed: Mocked general failure")
