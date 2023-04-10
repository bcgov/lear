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

import pytest

from legal_api.models.legacy_outputs import LegacyOutputs
from tests.unit.models import (
    factory_business,
    factory_shadow_filing
)
from registry_schemas.example_data import (
    ANNUAL_REPORT,
)

def factory_output(colin_event_id, filing_id: int = None, output_key: int = None, type: str = 'test'):
    """Return a valid legacy outputs object."""
    output = LegacyOutputs(colin_event_id=colin_event_id,
                          filing_id=filing_id,
                          legacy_output_key=output_key,
                          type=type)
    return output

def test_legacy_ouptuts_save(session):
    """Assert that an output is stored correctly"""
    mock_outputs = factory_output(1)
    mock_outputs.save()

    assert mock_outputs.colin_event_id is not None
    assert mock_outputs.filing_id is None
    assert mock_outputs.legacy_output_key is None
    assert mock_outputs.type is not None

def test_get_by_filing_id(session):
    """Assert that searching for an output by filing_id correctly."""
    b = factory_business('CP1234567')
    filing = factory_shadow_filing(business=b, id=2, data_dict=None)
    mock_output_table = factory_output(colin_event_id=1, filing_id=2)
    mock_output_table.save()
    
    session.add(mock_output_table)
    session.commit()

    # finding output succeeds
    output = mock_output_table.get_by_filing_id(2)
    assert output is not None

    # finding output fails
    output = mock_output_table.get_by_filing_id(3)
    assert output is None

def test_get_by_colin_id(session):
    """Assert that searching for an output by colin_id correctly."""
    mock_output_table = factory_output(colin_event_id=1)

    session.add(mock_output_table)
    session.commit()

    # finding output succeeds
    output = mock_output_table.get_by_colin_id(2)
    assert output is not None

    # finding output fails
    output = mock_output_table.get_by_colin_id(3)
    assert output is None

def test_get_by_legacy_output_id(session):
    """Assert that searching for an output by output_key correctly."""
    mock_output_table = factory_output(output_key=1)
    
    session.add(mock_output_table)
    session.commit()

    # finding output succeeds
    output = mock_output_table.get_by_legacy_output_key(2)
    assert output is not None

    # finding output fails
    output = mock_output_table.get_by_legacy_output_key(3)
    assert output is None
