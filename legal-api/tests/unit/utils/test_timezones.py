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
"""Test Suite for the utilities to manage timezones."""
from datetime import datetime, timezone

import pytest
from hypothesis import example, given
from hypothesis.strategies import datetimes

from legal_api.utils.timezone import local_from_utc


@pytest.mark.parametrize('test_name, utc_dt, timezone_name, expected_dt', [
    ('simple-date',
     datetime(2019, 8, 5, 17, 43, 30, 802644, tzinfo=timezone.utc),
     'America/Vancouver',
     datetime(2019, 8, 5, 10, 43, 30, 802644)
     ),
    ('local_day_before',
     datetime(2019, 7, 1, 0, 43, 30, 802644, tzinfo=timezone.utc),
     'America/Vancouver',
     datetime(2019, 6, 30, 17, 43, 30, 802644)
     ),
    ('leap_yr_day_of',
     datetime(2020, 2, 29, 17, 43, 30, 802644, tzinfo=timezone.utc),
     'America/Vancouver',
     datetime(2020, 2, 29, 9, 43, 30, 802644)
     ),
    ('leap_yr_day_before',
     datetime(2020, 3, 1, 0, 43, 30, 802644, tzinfo=timezone.utc),
     'America/Vancouver',
     datetime(2020, 2, 29, 16, 43, 30, 802644)
     ),
])
def test_local_from_utc(test_name, utc_dt, timezone_name, expected_dt):
    """Assert that UTC is converted to the locale specified."""
    d2 = local_from_utc(utc_dt, timezone_name)

    assert d2.replace(tzinfo=None) == expected_dt


@given(dt=datetimes())
@example(dt=datetime(2020, 3, 1, 0, 43, 30, 802644, tzinfo=timezone.utc))
def test_local_from_utc_hypothesis(dt):
    """Assert that datetime is converted or return None.

    The only error thrown for inputs can be pytz.exceptions.NonExistentTimeError
    """
    local_from_utc(dt, 'America/Vancouver')


def test_bad_unknown_local_from_utc():
    """Assert that UTC is converted to the locale specified."""
    d2 = local_from_utc(datetime(2019, 7, 1, 0, 43, 30, 802644, tzinfo=timezone.utc), 'Mars/UnknownTZ')

    assert not d2
