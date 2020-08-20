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
    def as_gmt_timezone(date_time: datetime) -> datetime:
        """Return a datetime adjusted to the offset-aware GMT timezone."""
        return date_time.astimezone(pytz.timezone('GMT'))

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
