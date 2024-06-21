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

"""Tests for the Furnishings Job.
Test suite to ensure that the Furnishings Job is working as expected.
"""
import pytest
import asyncio

from datetime import datetime
from unittest.mock import MagicMock, patch
from legal_api.models import Configuration, Furnishing

from furnish import check_run_schedule, stage_1_process

from . import factory_batch, factory_batch_processing, factory_business


def test_check_run_schedule():
    """Assert that schedule check validates the day of run based on cron string in config."""
    with patch.object(Configuration, 'find_by_name') as mock_find_by_name:
        mock_stage_1_config = MagicMock()
        mock_stage_2_config = MagicMock()
        mock_stage_3_config = MagicMock()
        mock_stage_1_config.val = '0 0 * * 1-2'
        mock_stage_2_config.val = '0 0 * * 2'
        mock_stage_3_config.val = '0 0 * * 3'
        mock_find_by_name.side_effect = [mock_stage_1_config, mock_stage_2_config, mock_stage_3_config]

        with patch('furnish.datetime', wraps=datetime) as mock_datetime:
            mock_datetime.today.return_value = datetime(2024, 6, 4, 1, 2, 3, 4)
            cron_valid_1, cron_valid_2, cron_valid_3 = check_run_schedule()

            assert cron_valid_1 is True
            assert cron_valid_2 is True
            assert cron_valid_3 is False


@pytest.mark.asyncio
async def test_stage_1_process_first_notification_email(app, session):
    """Assert that email furnishing entry is created correctly."""
    business = factory_business(identifier='BC1234567')
    batch = factory_batch()
    batch_processing = factory_batch_processing(
        batch_id=batch.id,
        business_id=business.id,
        identifier=business.identifier,
    )

    qsm = MagicMock()
    with patch('furnish.get_email_address_from_auth', return_value='test@no-reply.com'):
        with patch('furnish.send_email', return_value=None):
            await stage_1_process(app, qsm)

    furnishings = Furnishing.find_by(business_id=business.id)
    assert len(furnishings) == 1
    furnishing = furnishings[0]
    assert furnishing.furnishing_type == Furnishing.FurnishingType.EMAIL
    assert furnishing.email == 'test@no-reply.com'
    assert furnishing.furnishing_name == Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR
    assert furnishing.status == Furnishing.FurnishingStatus.QUEUED
