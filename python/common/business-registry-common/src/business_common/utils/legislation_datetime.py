# Copyright © 2020 Province of British Columbia
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
"""Legislation Date time utilities."""
import datedelta
import pytz
from dateutil.tz import gettz
from flask import current_app

from .datetime import date, datetime, timedelta, timezone


class LegislationDatetime():
    """Date utility using legislation timezone for reporting and future effective dates."""

    @staticmethod
    def now() -> datetime:
        """Construct a datetime using the legislation timezone."""
        return datetime.now().astimezone(pytz.timezone(current_app.config.get('LEGISLATIVE_TIMEZONE')))

    @staticmethod
    def datenow() -> date:
        """Construct a date using the legislation timezone."""
        return LegislationDatetime.now().date()

    @staticmethod
    def tomorrow_midnight() -> datetime:
        """Construct a datetime tomorrow 12:00 AM using the legislation timezone."""
        _date = datetime.now().astimezone(pytz.timezone(current_app.config.get('LEGISLATIVE_TIMEZONE')))
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
        return date_time.astimezone(pytz.timezone(current_app.config.get('LEGISLATIVE_TIMEZONE')))

    @staticmethod
    def as_legislation_timezone_from_date(_date: date) -> datetime:
        """Return a datetime adjusted to the legislation timezone from a date object."""
        return datetime(
            _date.year, _date.month, _date.day, tzinfo=gettz(current_app.config.get('LEGISLATIVE_TIMEZONE'))
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
        return date_time.astimezone(pytz.timezone('GMT'))

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

        return next_day.strftime('%B %d, %Y')

    @staticmethod
    def format_as_report_string(date_time: datetime) -> str:
        """Return a datetime string in this format (eg: `August 5, 2021 at 11:00 am Pacific time`)."""
        # ensure is set to correct timezone
        date_time = LegislationDatetime.as_legislation_timezone(date_time)
        hour = date_time.strftime('%I').lstrip('0')
        # %p provides locale value: AM, PM (en_US); am, pm (de_DE); So forcing it to be lower in any case
        am_pm = date_time.strftime('%p').lower()
        date_time_str = date_time.strftime(f'%B %-d, %Y at {hour}:%M {am_pm} Pacific time')
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

        hour = date_time.strftime('%I').lstrip('0')
        # %p provides locale value: AM, PM (en_US); am, pm (de_DE); So forcing it to be lower in any case
        am_pm = date_time.strftime('%p').lower()
        date_time_str = date_time.strftime(f'%B %-d, %Y at {hour}:%M {am_pm} Pacific time')
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
        return date_time.strftime('%Y-%m-%d')

    @staticmethod
    def is_future(date_string: str) -> bool:
        """Return the boolean for whether the date string is in the future."""
        effective_date = datetime.fromisoformat(date_string)
        return effective_date > datetime.utcnow().replace(tzinfo=timezone.utc)
