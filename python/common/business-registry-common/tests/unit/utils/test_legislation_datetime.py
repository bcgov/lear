# Copyright © 2025 Province of British Columbia
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
"""Tests for LegislationDatetime utilities."""
from datetime import date

import pytest
from flask import Flask

from business_common.utils.legislation_datetime import LegislationDatetime


@pytest.fixture
def app():
    """Minimal Flask app with LEGISLATIVE_TIMEZONE configured."""
    _app = Flask(__name__)
    _app.config["LEGISLATIVE_TIMEZONE"] = "America/Vancouver"
    return _app


def test_static_helpers():
    """Assert context-free helpers work correctly."""
    assert LegislationDatetime.format_as_next_legislation_day("2021-08-04") == "August 05, 2021"
    assert LegislationDatetime.is_future("2099-01-01T00:00:00+00:00") is True
    assert LegislationDatetime.is_future("2000-01-01T00:00:00+00:00") is False


def test_now_methods(app):
    """Assert now(), datenow(), and tomorrow helpers return expected values."""
    with app.app_context():
        assert LegislationDatetime.now().tzinfo is not None
        assert isinstance(LegislationDatetime.datenow(), date)
        midnight = LegislationDatetime.tomorrow_midnight()
        assert midnight.hour == 0 and midnight.minute == 0 and midnight.second == 0
        assert LegislationDatetime.tomorrow_one_minute_after_midnight().minute == 1


def test_timezone_conversions(app):
    """Assert legislation ↔ UTC conversion methods return correct timezones."""
    with app.app_context():
        leg_dt = LegislationDatetime.as_legislation_timezone_from_date_str("2021-08-05")
        assert leg_dt is not None
        utc_dt = LegislationDatetime.as_utc_timezone_from_legislation_date_str("2021-08-05")
        assert utc_dt.tzname() in ("GMT", "UTC")
        assert LegislationDatetime.as_utc_timezone(leg_dt).tzname() in ("GMT", "UTC")


def test_format_methods(app):
    """Assert all format_as_* methods return expected strings."""
    with app.app_context():
        dt = LegislationDatetime.as_legislation_timezone_from_date_str("2021-08-05")
        assert "Pacific time" in LegislationDatetime.format_as_report_string(dt)
        assert "12:01" in LegislationDatetime.format_as_report_expiry_string(dt)
        assert "11:59" in LegislationDatetime.format_as_report_expiry_string_1159(dt)
        assert LegislationDatetime.format_as_legislation_date(dt) == "2021-08-05"
