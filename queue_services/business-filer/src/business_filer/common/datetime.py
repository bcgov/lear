# Copyright © 2025 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""Date time utilities."""
import time as _time
from datetime import (  # pylint: disable=unused-import
    UTC,
    date,  # noqa: F401
    timedelta,
    timezone,  # noqa: F401
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
    

class datetime(_datetime):  # noqa: N801 ; ha datetime is invalid??
    """Alternative to the built-in datetime that has a timezone on the UTC call."""

    @classmethod
    def utcnow(cls):
        """Construct a UTC non-naive datetime, meaning it includes timezone from time.time()."""
        time_stamp = _time.time()
        return super().fromtimestamp(time_stamp, UTC)

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
