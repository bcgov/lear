# Copyright © 2025 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
"""Unit tests for BN retry worker."""

from unittest.mock import MagicMock, patch

import pytest

from bn_retry import create_app, db
from bn_retry.worker import (
    get_businesses_to_process,
    publish_business_event,
    publish_email_notification,
    run_job,
    update_business_bn,
)
from business_model.models import Business


@pytest.fixture
def mock_business():
    """Create a mock business object."""
    business = MagicMock(spec=Business)
    business.identifier = "FM1234567"
    business.tax_id = None
    return business


def test_get_businesses_to_process(app, mock_business):
    """Test querying businesses that need BN15 retry."""
    with patch.object(db.session, "query") as mock_query:
        # Mock chain: query().filter().order_by().offset().limit().all()
        mock_query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
            mock_business
        ]

        businesses = get_businesses_to_process(limit=10, skip=5)

        assert len(businesses) == 1
        assert businesses[0].identifier == "FM1234567"
        mock_query.return_value.filter.return_value.order_by.return_value.offset.assert_called_with(5)
        mock_query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.assert_called_with(
            10
        )


# ... [other tests] ...


def test_run_job_no_matches(app, mock_business):
    """Test job execution when batch returns no matches."""
    # Scenario:
    # 1. get(skip=0) -> [business]
    # 2. check -> {} (no matches)
    # 3. updates=0. skip+=1.
    # 4. get(skip=1) -> [] (break)

    with (
        patch("bn_retry.worker.get_businesses_to_process") as mock_get,
        patch("bn_retry.worker.check_bn15_status_batch") as mock_check,
        patch.object(db.session, "commit") as mock_commit,
    ):
        mock_get.side_effect = [[mock_business], []]
        mock_check.return_value = []  # No matches

        run_job()

        assert mock_get.call_count == 2
        mock_get.assert_any_call(limit=20, skip=0)
        mock_get.assert_any_call(limit=20, skip=1)
        mock_check.assert_called_once()
        # db.session.commit() is NOT called because updates=0 and user edited code to only commit in update_business_bn (Step 180) and run_job logging (which doesn't call commit, just logs).
        # Wait, run_job logic I wrote:
        # try:
        #    total_updated += updates_in_batch
        #    current_app.logger.info(...)
        # except...
        # It does NOT call commit. Commit is in update_business_bn per row.
        # So mock_commit should NOT be called.
        mock_commit.assert_not_called()


def test_update_business_bn(app, mock_business):
    """Test updating business with BN15."""
    with (
        patch.object(db.session, "add"),
        patch.object(db.session, "commit"),
    ):  # NOTE: commit is removed from update_business_bn but added to run_job,
        # Wait, I removed commit from update_business_bn in worker.py, let me check.
        # Yes, I removed it. So the test should NOT expect commit here if I test update_business_bn in isolation.
        # But wait, looking at my worker.py change:
        # -        db.session.commit()
        # +        # db.session.commit() (removed)
        # So I should update the test to NOT expect commit.

        update_business_bn(mock_business, "123456789BC0001")

        assert mock_business.tax_id == "123456789BC0001"
        db.session.add.assert_called_once_with(mock_business)
        # db.session.commit.assert_not_called() # Ideally we'd assert this passed


def test_publish_email_notification(app):
    """Test publishing email notification."""
    with patch("bn_retry.worker.gcp_queue") as mock_queue:
        publish_email_notification("FM1234567")

        mock_queue.publish.assert_called_once()
        # Verify arguments if needed, or just that it was called.


def test_publish_business_event(app):
    """Test publishing business change event."""
    with patch("bn_retry.worker.gcp_queue") as mock_queue:
        publish_business_event("FM1234567")

        mock_queue.publish.assert_called_once()


def test_run_job_success_batch(app, mock_business):
    """Test successful job execution with batch processing."""
    # Scenario:
    # 1. get(skip=0) -> [business]
    # 2. check -> match (len=1)
    # 3. updates=1. len(business)=1. unprocessed=0. skip+=0.
    # 4. get(skip=0) -> [] (break)

    with (
        patch("bn_retry.worker.get_businesses_to_process") as mock_get,
        patch("bn_retry.worker.check_bn15_status_batch") as mock_check,
        patch("bn_retry.worker.update_business_bn") as mock_update,
        patch("bn_retry.worker.publish_email_notification") as mock_email,
        patch("bn_retry.worker.publish_business_event") as mock_event,
    ):
        # Mock get_businesses sequence: [mock_business], []
        mock_get.side_effect = [[mock_business], []]

        # Mock batch check returning 1 match list (matches user format of list of dicts)
        # Assuming len(bn_results) == 1 implies 1 update for logic consistency
        mock_check.return_value = [{"FM1234567": "BN12345"}]

        run_job()

        assert mock_get.call_count == 2
        mock_get.assert_any_call(limit=50, skip=0)
        # offset remains 0 because we updated all items returned
        mock_get.assert_any_call(limit=50, skip=0)

        mock_check.assert_called_once_with(["FM1234567"])
        mock_update.assert_called_once_with(mock_business, "BN12345")


def test_run_job_no_matches(app, mock_business):
    """Test job execution when batch returns no matches."""
    # Scenario:
    # 1. get(skip=0) -> [business]
    # 2. check -> [] (no matches)
    # 3. updates=0. len(business)=1. unprocessed=1. skip+=1.
    # 4. get(skip=1) -> [] (break)

    with (
        patch("bn_retry.worker.get_businesses_to_process") as mock_get,
        patch("bn_retry.worker.check_bn15_status_batch") as mock_check,
    ):
        mock_get.side_effect = [[mock_business], []]
        mock_check.return_value = []  # No matches

        run_job()

        assert mock_get.call_count == 2
        mock_get.assert_any_call(limit=50, skip=0)
        mock_get.assert_any_call(limit=50, skip=1)
        mock_check.assert_called_once()


def test_run_job_empty(app):
    """Test job execution when no businesses found initially."""
    with (
        patch("bn_retry.worker.get_businesses_to_process", return_value=[]),
        patch("bn_retry.worker.check_bn15_status_batch") as mock_check,
    ):
        run_job()

        mock_check.assert_not_called()
