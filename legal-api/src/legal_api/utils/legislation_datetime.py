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
import datetime

import datedelta
import pytz
from dateutil.tz import gettz
from flask import current_app


class LegislationDatetime():
    """Date utility using legislation timezone for reporting and future effective dates."""

    @staticmethod
    def now() -> datetime:
        """Construct a datetime using the legislation timezone."""
        return datetime.datetime.now().astimezone(pytz.timezone(current_app.config.get('LEGISLATIVE_TIMEZONE')))

    @staticmethod
    def tomorrow_midnight() -> datetime:
        """Construct a datetime tomorrow midnight using the legislation timezone."""
        date = datetime.datetime.now().astimezone(pytz.timezone(current_app.config.get('LEGISLATIVE_TIMEZONE')))
        date += datedelta.datedelta(days=1)
        date = date.replace(hour=0, minute=0, second=0, microsecond=0)

        return date

    @staticmethod
    def as_legislation_timezone(date_time: datetime) -> datetime:
        """Return a datetime adjusted to the legislation timezone."""
        return date_time.astimezone(pytz.timezone(current_app.config.get('LEGISLATIVE_TIMEZONE')))

    @staticmethod
    def as_legislation_timezone_from_date(_date: datetime.date) -> datetime.date:
        """Return a datetime adjusted to the legislation timezone from a date object."""
        return datetime.datetime(
            _date.year, _date.month, _date.day, tzinfo=gettz(current_app.config.get('LEGISLATIVE_TIMEZONE'))
        )

    @staticmethod
    def as_utc_timezone(date_time: datetime) -> datetime:
        """Return a datetime adjusted to the GMT timezone (aka UTC)."""
        return date_time.astimezone(pytz.timezone('GMT'))

    @staticmethod
    def format_as_report_string(date_time: datetime) -> str:
        """Return a datetime string in this format (eg: `August 5, 2021 at 11:00 am Pacific time`)."""
        hour = date_time.strftime('%I').lstrip('0')
        # %p provides locale value: AM, PM (en_US); am, pm (de_DE); So forcing it to be lower in any case
        am_pm = date_time.strftime('%p').lower()
        date_time_str = date_time.strftime(f'%B %-d, %Y at {hour}:%M {am_pm} Pacific time')
        return date_time_str

    @staticmethod
    def format_as_legislation_date(date_string: str) -> str:
        """Return the date in legislation timezone as a string."""
        date_time = datetime.datetime.fromisoformat(date_string)
        return date_time.astimezone(pytz.timezone(current_app.config.get('LEGISLATIVE_TIMEZONE'))).strftime('%Y-%m-%d')

    @staticmethod
    def is_future(date_string: str) -> bool:
        """Return the boolean for whether the date string is in the future."""
        effective_date = datetime.datetime.fromisoformat(date_string)
        return effective_date > datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
