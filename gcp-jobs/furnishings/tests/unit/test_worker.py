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
from datetime import datetime
from unittest.mock import MagicMock, patch

from business_model.models import Configuration
from furnishings.worker import check_run_schedule


def test_check_run_schedule():
    """Assert that schedule check validates the day of run based on cron string in config."""
    with patch.object(Configuration, "find_by_name") as mock_find_by_name:
        mock_stage_1_config = MagicMock()
        mock_stage_2_config = MagicMock()
        mock_stage_3_config = MagicMock()
        mock_stage_1_config.val = "0 0 * * 1-2"
        mock_stage_2_config.val = "0 0 * * 2"
        mock_stage_3_config.val = "0 0 * * 3"
        mock_find_by_name.side_effect = [mock_stage_1_config, mock_stage_2_config, mock_stage_3_config]

        with patch("furnishings.worker.datetime", wraps=datetime) as mock_datetime:
            mock_datetime.today.return_value = datetime(2024, 6, 4, 1, 2, 3, 4)
            cron_valid_1, cron_valid_2, cron_valid_3 = check_run_schedule()

            assert cron_valid_1 is True
            assert cron_valid_2 is True
            assert cron_valid_3 is False
