# Copyright © 2026 Province of British Columbia
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
"""Tests for Filing._process_amalgamating_businesses entry classification."""
from unittest.mock import MagicMock

from colin_api.models import Business
from colin_api.models.corp_involved import CorpInvolved
from colin_api.models.filing import Filing


def _process(mocker, amalgamating_businesses):
    """Run _process_amalgamating_businesses over the entries; return (corp_involved rows, state updates)."""
    created = []
    mocker.patch.object(CorpInvolved, 'create_corp_involved', side_effect=lambda _cursor, obj: created.append(obj))
    update_corp_state = mocker.patch.object(Business, 'update_corp_state')

    filing = Filing()
    filing.event_id = 1234567
    filing.body = {'amalgamatingBusinesses': amalgamating_businesses}
    Filing._process_amalgamating_businesses(MagicMock(), filing)  # pylint: disable=protected-access

    return created, update_corp_state


def test_identifier_entry_bc_corp(mocker):
    """Assert a BC identifier entry is HAM'd under its bare corp num."""
    created, update_corp_state = _process(mocker, [
        {'role': 'amalgamating', 'identifier': 'BC0870226'}
    ])

    assert len(created) == 1
    assert created[0].corp_num == '0870226'
    assert created[0].home_juri_num is None
    assert created[0].adopted_corp_ind is None
    update_corp_state.assert_called_once()
    assert update_corp_state.call_args.args[2] == '0870226'
    assert update_corp_state.call_args.args[3] == Business.CorpStateTypes.AMALGAMATED.value


def test_identifier_entry_expro(mocker):
    """Assert an identifier-only extraprovincial (A) entry is HAM'd under its full identifier."""
    created, update_corp_state = _process(mocker, [
        {'role': 'amalgamating', 'identifier': 'A0077777'}
    ])

    assert len(created) == 1
    assert created[0].corp_num == 'A0077777'
    assert created[0].home_juri_num is None
    assert created[0].foreign_nme is None
    update_corp_state.assert_called_once()
    assert update_corp_state.call_args.args[2] == 'A0077777'
    assert update_corp_state.call_args.args[3] == Business.CorpStateTypes.AMALGAMATED.value


def test_holding_entry_marks_adopted(mocker):
    """Assert a holding/primary identifier entry sets the adopted corp indicator."""
    created, _ = _process(mocker, [
        {'role': 'holding', 'identifier': 'BC0870226'}
    ])

    assert created[0].adopted_corp_ind == 'Y'


def test_foreign_entry(mocker):
    """Assert a true foreign entry records home jurisdiction data and no corp state change."""
    created, update_corp_state = _process(mocker, [
        {
            'role': 'amalgamating',
            'identifier': 'AB-1234567',
            'legalName': 'FOREIGN CO.',
            'foreignJurisdiction': {'country': 'CA', 'region': 'AB'}
        }
    ])

    assert len(created) == 1
    assert created[0].corp_num is None
    assert created[0].home_juri_num == 'AB-1234567'
    assert created[0].foreign_nme == 'FOREIGN CO.'
    assert created[0].can_jur_typ_cd == 'AB'
    update_corp_state.assert_not_called()


def test_foreign_federal_and_international_entries(mocker):
    """Assert federal and non-Canadian foreign entries map their jurisdiction codes."""
    created, _ = _process(mocker, [
        {
            'role': 'amalgamating',
            'identifier': '7654321',
            'legalName': 'FEDERAL CO.',
            'foreignJurisdiction': {'country': 'CA', 'region': 'FEDERAL'}
        },
        {
            'role': 'amalgamating',
            'identifier': 'US-1',
            'legalName': 'US CO.',
            'foreignJurisdiction': {'country': 'US', 'region': 'DE'}
        }
    ])

    assert created[0].can_jur_typ_cd == 'FD'
    assert created[1].can_jur_typ_cd == 'OT'
    assert created[1].othr_juri_desc == 'US, DE'
