# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test suite to ensure the Common Utilities are working correctly."""
from datetime import date

from hypothesis import example, given
from hypothesis.strategies import text

from legal_api.services.filings.utils import get_date, get_str


@given(f=text(), p=text())
@example(f={'filing': {'header': {'date': '2001-08-05'}}},
         p='filing/header/date')
def test_get_date(f, p):
    """Assert the get_date extracts the date from the JSON file."""
    d = get_date(f, p)
    if not d:
        assert True
    else:
        assert isinstance(d, date)


@given(f=text(), p=text())
@example(f={'filing': {'header': {'name': 'annualReport'}}},
         p='filing/header/name')
def test_get_str(f, p):
    """Assert the get_date extracts the date from the JSON file."""
    d = get_str(f, p)
    if not d:
        assert True
    else:
        assert isinstance(d, str)
