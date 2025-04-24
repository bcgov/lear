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
"""Legislation Date time utilities."""
from datetime import UTC, date, timedelta

import datedelta
import pytz
from dateutil.tz import gettz
from flask import current_app

from .datetime import datetime


class LegislationDatetime:
    """Date utility using legislation timezone for reporting and future effective dates."""

    @staticmethod
    def now() -> datetime:
        """Construct a datetime using the legislation timezone."""
        return datetime.now().astimezone(pytz.timezone(current_app.config.get("LEGISLATIVE_TIMEZONE")))

    @staticmethod
    def datenow() -> date:
        """Construct a date using the legislation timezone."""
        return LegislationDatetime.now().date()

    @staticmethod
    def tomorrow_midnight() -> datetime:
        """Construct a datetime tomorrow 12:00 AM using the legislation timezone."""
        _date = datetime.now().astimezone(pytz.timezone(current_app.config.get("LEGISLATIVE_TIMEZONE")))
        _date += datedelta.datedelta(days=1)
        _date = _date.replace(hour=0, minute=0, second=0, microsecond=0)

        return _date

    @staticmethod
    def tomorrow_one_minute_after_midnight() -> datetime:
        """Construct a datetime tomorrow 12:01 AM using the legislation timezone."""
        return LegislationDatetime.tomorrow_midnight() + timedelta(minutes=1)

    @staticmethod
    def as_legislation_timezone(date_time: datetime) -> datetime:
        """Return a datetime adjusted to the legislation timezone."""
        return date_time.astimezone(pytz.timezone(current_app.config.get("LEGISLATIVE_TIMEZONE")))

    @staticmethod
    def as_legislation_timezone_from_date(_date: date) -> datetime:
        """Return a datetime adjusted to the legislation timezone from a date object."""
        return datetime(
            _date.year, _date.month, _date.day, tzinfo=gettz(current_app.config.get("LEGISLATIVE_TIMEZONE"))
        )

    @staticmethod
    def as_legislation_timezone_from_date_str(date_string: str) -> datetime:
        """Return a date time object using provided date_string in legislation timezone.

        Note:
        This function expect a date_sting without time (example: 1990-12-31).
        It is assumed that the date_string provided is already in legislation timezone.
        """
        _date = date.fromisoformat(date_string)
        return LegislationDatetime.as_legislation_timezone_from_date(_date)

    @staticmethod
    def as_utc_timezone(date_time: datetime) -> datetime:
        """Return a datetime adjusted to the GMT timezone (aka UTC)."""
        return date_time.astimezone(pytz.timezone("GMT"))

    @staticmethod
    def as_utc_timezone_from_legislation_date_str(date_string: str) -> datetime:
        """Return a datetime adjusted to the GMT timezone (aka UTC) from a date (1900-12-31) string."""
        _date_time = LegislationDatetime.as_legislation_timezone_from_date_str(date_string)
        return LegislationDatetime.as_utc_timezone(_date_time)

    @staticmethod
    def format_as_next_legislation_day(date_string: str) -> str:
        """Return the next day in this format (eg: `August 5, 2021`)."""
        input_date = datetime.fromisoformat(date_string)
        next_day = input_date + timedelta(days=1)

        return next_day.strftime("%B %d, %Y")

    @staticmethod
    def format_as_report_string(date_time: datetime) -> str:
        """Return a datetime string in this format (eg: `August 5, 2021 at 11:00 am Pacific time`)."""
        # ensure is set to correct timezone
        date_time = LegislationDatetime.as_legislation_timezone(date_time)
        hour = date_time.strftime("%I").lstrip("0")
        # %p provides locale value: AM, PM (en_US); am, pm (de_DE); So forcing it to be lower in any case
        am_pm = date_time.strftime("%p").lower()
        date_time_str = date_time.strftime(f"%B %-d, %Y at {hour}:%M {am_pm} Pacific time")
        return date_time_str

    @staticmethod
    def format_as_report_string_with_custom_time(date_time: datetime,
                                                 custom_hour: int,
                                                 custom_minute: int,
                                                 custom_second: int,
                                                 custom_microsecond: int) -> str:
        """Return a datetime string in this format (eg: `August 5, 2021 at 11:00 am Pacific time`).

        It also accepts new H:M:S.ms values.
        """
        # ensure is set to correct timezone
        date_time = LegislationDatetime.as_legislation_timezone(date_time)
        date_time = date_time.replace(hour=custom_hour,
                                      minute=custom_minute,
                                      second=custom_second,
                                      microsecond=custom_microsecond)

        hour = date_time.strftime("%I").lstrip("0")
        # %p provides locale value: AM, PM (en_US); am, pm (de_DE); So forcing it to be lower in any case
        am_pm = date_time.strftime("%p").lower()
        date_time_str = date_time.strftime(f"%B %-d, %Y at {hour}:%M {am_pm} Pacific time")
        return date_time_str

    @staticmethod
    def format_as_report_expiry_string(date_time: datetime) -> str:
        """Return a datetime string in this format (eg: `August 5, 2021 at 12:01 am Pacific time`).

        It will have an extra minute to satisfy the business requirement of one minute after
        midnight for expiry times.
        """
        # ensure is set to correct timezone
        date_time_str = LegislationDatetime.format_as_report_string_with_custom_time(date_time, 0, 1, 0, 0)
        return date_time_str

    @staticmethod
    def format_as_report_expiry_string_1159(date_time: datetime) -> str:
        """Return a datetime string in this format (eg: `August 5, 2021 at 11:59 pm Pacific time`)."""
        # ensure is set to correct timezone
        date_time_str = LegislationDatetime.format_as_report_string_with_custom_time(date_time, 23, 59, 0, 0)
        return date_time_str

    @staticmethod
    def format_as_legislation_date(date_time: datetime) -> str:
        """Return the date in legislation timezone as a string."""
        date_time = LegislationDatetime.as_legislation_timezone(date_time)
        return date_time.strftime("%Y-%m-%d")

    @staticmethod
    def is_future(date_string: str) -> bool:
        """Return the boolean for whether the date string is in the future."""
        effective_date = datetime.fromisoformat(date_string)
        return effective_date > datetime.now(UTC).replace(tzinfo=UTC)
