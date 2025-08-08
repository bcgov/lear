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

"""Tests to assure the Registrar Meta Utility.

Test-Suite to ensure that the Registrar Meta Utility is working as expected.
"""
import pytest
import datetime

from registry_schemas.example_data import ANNUAL_REPORT

from legal_api.models import Filing
from legal_api.reports.registrar_meta import RegistrarInfo
from tests.unit.models import factory_business


@pytest.mark.parametrize(
    'date, name, title',
    [
        (datetime.datetime(1970, 1, 1), "RON TOWNSHEND", "Registrar of Companies"),
        (datetime.datetime(2012, 5, 31), "RON TOWNSHEND", "Registrar of Companies"),
        (datetime.datetime(2012, 6, 1), "ANGELO COCCO", "A/Registrar of Companies"),
        (datetime.datetime(2012, 7, 12), "ANGELO COCCO", "A/Registrar of Companies"),
        (datetime.datetime(2012, 7, 13), "CAROL PREST", "Registrar of Companies"),
        (datetime.datetime(2022, 5, 31), "CAROL PREST", "Registrar of Companies"),
        (datetime.datetime(2022, 6, 1), "T.K. SPARKS", "Registrar of Companies"),
        (datetime.datetime(2025, 4, 17), "T.K. SPARKS", "Registrar of Companies"),
        (datetime.datetime(2025, 4, 18), "S. O'CALLAGHAN", "Registrar of Companies"),
        (datetime.datetime(2025, 8, 12), "S. O'CALLAGHAN", "Registrar of Companies")
    ]
)
def test_get_registrar_by_date(session, date, name, title):
    """Assert that the registrar effective on that date is returned."""
    b = factory_business('CP1234567')
    filing = Filing()
    filing.business_id = b.id
    filing.filing_date = date
    filing.effective_date = date
    filing.filing_data = ANNUAL_REPORT
    filing.save()

    registrar_info = RegistrarInfo.get_registrar_info(filing.effective_date)
    assert registrar_info['startDate']
    # assert registrar_info['endDate'] # last registrar has endDate=None
    assert registrar_info['signature']
    assert registrar_info['name'] == name
    assert registrar_info['title'] == title
