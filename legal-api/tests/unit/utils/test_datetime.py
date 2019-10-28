# Copyright © 2019 Province of British Columbia
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

"""Tests to ensure the datetime wrappers are working as expected."""
from datetime import datetime, timezone

from freezegun import freeze_time

from legal_api.utils.datetime import utcnow_tz


def test_utcnow_tz():
    """Assert that the utcnow call includes the utc timezone."""
    now = datetime(2020, 9, 17, 0, 0, 0, 0)

    with freeze_time(now):
        d = utcnow_tz()
        assert d == now.replace(tzinfo=timezone.utc)
