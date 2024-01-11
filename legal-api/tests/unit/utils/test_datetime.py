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


def test_datetime_utcnow():
    """Assert that datetime.utcnow returns a non-naive datetime object."""
    import legal_api.utils.datetime as _datetime

    now = datetime(2020, 9, 17, 0, 0, 0, 0)

    with freeze_time(now):
        d = _datetime.datetime.utcnow()
        assert d == now.replace(tzinfo=timezone.utc)


def test_datetime_isoformat():
    """Assert that the isoformat has the tzinfo set to +00:00."""
    import legal_api.utils.datetime as _datetime

    now = datetime(2020, 9, 17, 0, 0, 0, 0)

    with freeze_time(now):
        d = _datetime.datetime.utcnow()
        iso = d.isoformat()
        tz = iso[iso.find("+") :]
        assert tz == "+00:00"
