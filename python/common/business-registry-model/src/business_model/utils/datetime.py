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
"""Date time utilities."""
import time as _time
from datetime import (  # pylint: disable=unused-import
    date,
    timedelta,
    timezone,
)
from datetime import datetime as _datetime

from .base import BaseEnum


class DayOfWeek(BaseEnum):
    """Enum for the days of the week."""

    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6
    

class datetime(_datetime):  # pylint: disable=invalid-name; ha datetime is invalid??
    """Alternative to the built-in datetime that has a timezone on the UTC call."""

    @classmethod
    def utcnow(cls):
        """Construct a UTC non-naive datetime, meaning it includes timezone from time.time()."""
        time_stamp = _time.time()
        return super().utcfromtimestamp(time_stamp).replace(tzinfo=timezone.utc)

    @classmethod
    def from_date(cls, date_obj):
        """Get a datetime object from a date object."""
        return datetime(date_obj.year, date_obj.month, date_obj.day)

    @classmethod
    def add_business_days(cls, from_date: _datetime, num_days: int):
        """Add business days to an initial date. Only accounts for weekends, not holidays."""
        sunday = 6
        current_date = from_date
        business_days_to_add = abs(num_days)
        inc = 1 if num_days > 0 else -1
        while business_days_to_add > 0:
            current_date += timedelta(days=inc)
            weekday = current_date.weekday()
            if weekday >= sunday:
                continue
            business_days_to_add -= 1
        return current_date
