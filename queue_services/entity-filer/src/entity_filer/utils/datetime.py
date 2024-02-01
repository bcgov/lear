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
# from datetime import datetime, timezone
import time as _time
from datetime import date
from datetime import datetime as _datetime  # pylint: disable=unused-import # noqa: F401, I001, I005
from datetime import timezone

# noqa: I003,I005


class datetime(_datetime):  # pylint: disable=invalid-name; # noqa: N801; ha datetime is invalid??
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
