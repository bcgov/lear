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

import datetime

from registry_schemas.example_data import ANNUAL_REPORT

from legal_api.models import Filing
from legal_api.reports.registrar_meta import RegistrarInfo
from tests.unit.models import factory_legal_entity


def test_get_current_registrar(session):
    """Assert that the current registrar is returned."""
    b = factory_legal_entity("CP1234567")
    filing = Filing()
    filing.legal_entity_id = b.id
    filing.filing_date = datetime.datetime.utcnow()
    filing.filing_data = ANNUAL_REPORT
    filing.save()

    registrar_info = RegistrarInfo.get_registrar_info(filing.effective_date)
    assert registrar_info["startDate"]
    # assert registrar_info['endDate'] is None
    assert registrar_info["signature"]
    assert registrar_info["name"]
    assert registrar_info["title"]


def test_get_registrar_for_a_filing(session):
    """Assert that the registrar effective on that date is returned."""
    b = factory_legal_entity("CP1234567")
    filing = Filing()
    filing.legal_entity_id = b.id
    filing.filing_date = datetime.datetime(2012, 6, 6)
    filing.effective_date = datetime.datetime(2012, 6, 6)
    filing.filing_data = ANNUAL_REPORT
    filing.save()

    registrar_info = RegistrarInfo.get_registrar_info(filing.effective_date)
    assert registrar_info["startDate"]
    assert registrar_info["endDate"]
    assert registrar_info["signature"]
    assert registrar_info["name"] == "ANGELO COCCO"
    assert registrar_info["title"] == "A/Registrar of Companies"
