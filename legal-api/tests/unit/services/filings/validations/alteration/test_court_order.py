# Copyright © 2021 Province of British Columbia
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
"""Tests to assure the Court Order is validated properly."""
import pytest

from legal_api.utils.datetime import datetime, timedelta
from legal_api.services.filings.validations.common_validations import validate_court_order


@pytest.mark.parametrize('invalid_court_order', [
    {'orderDate': (datetime.today() + timedelta(days=1)).isoformat()}, #invalid date - tommorow
    {'orderDate': (datetime.today() + timedelta(days=30)).isoformat()}, #invalid date - 30 days later
    {'orderDate': (datetime.today() + timedelta(days=366)).isoformat()} #invalid date - 366 days later
])
def test_validate_invalid_court_orders(session, invalid_court_order):
    """Assert not valid court orders."""
    msg = validate_court_order('/filing/alteration/courtOrder', invalid_court_order)

    assert msg
    assert len(msg) > 0

@pytest.mark.parametrize('valid_court_order', [
    {'orderDate': datetime.today().isoformat()}, #valid date - today
    {'orderDate': (datetime.today() + timedelta(days=-1)).isoformat()}, #valid date - yesterday
    {'orderDate': (datetime.today() + timedelta(days=-30)).isoformat()}, #valid date - 30 days ago
    {'orderDate': (datetime.today() + timedelta(days=-366)).isoformat()}  #valid date - 366 days ago
])
def test_validate_valid_court_orders(session, valid_court_order):
    """Assert valid court orders."""
    msg = validate_court_order('/filing/alteration/courtOrder', valid_court_order)

    assert not msg
