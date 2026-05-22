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
from datetime import date, datetime, timezone

import pytest

from business_common.utils import datetime as _datetime


def test_datetime_utcnow(freeze_datetime_utcnow):
    """Assert that datetime.utcnow returns a non-naive datetime object."""
    now = datetime(2020, 9, 17, 0, 0, 0, 0)

    with freeze_datetime_utcnow(now):
        print(1)
        print(_datetime)
        print(_datetime.__dict__)
        print(_datetime.utcnow)
        d = _datetime.utcnow()
        assert d == now.replace(tzinfo=timezone.utc)


def test_datetime_isoformat(freeze_datetime_utcnow):
    """Assert that the isoformat has the tzinfo set to +00:00."""
    now = datetime(2020, 9, 17, 0, 0, 0, 0)

    with freeze_datetime_utcnow(now):
        d = _datetime.utcnow()
        iso = d.isoformat()
        tz = iso[iso.find('+'):]
        assert tz == '+00:00'


@pytest.mark.parametrize(
    'test_name, from_date_str, num_days, expected_date_str', [
        (
            'ADD_WITHIN_WEEKDAYS',
            '2024-06-19',
            2,
            '2024-06-21'
        ),
        (
            'ADD_OVER_WEEKEND',
            '2024-06-19',
            5,
            '2024-06-26'
        ),
        (
            'SUB_WITHIN_WEEKDAYS',
            '2024-06-19',
            -2,
            '2024-06-17'
        ),
        (
            'SUB_OVER_WEEKEND',
            '2024-06-19',
            -5,
            '2024-06-12'
        ),
    ]
)
def test_datetime_add_business_days(test_name, from_date_str, num_days, expected_date_str):
    """Assert that business days are added to a date correctly."""
    from_date = date.fromisoformat(from_date_str)
    new_date = _datetime.add_business_days(from_date, num_days)
    assert new_date == date.fromisoformat(expected_date_str)
