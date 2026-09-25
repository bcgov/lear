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
"""Tests for the changeOfDirectors fee code determination across both filing shapes."""
import copy

import pytest

from legal_api.resources.v2.business.business_filings.business_filings import ListFilingResource
from registry_schemas.example_data import CHANGE_OF_DIRECTORS, CHANGE_OF_DIRECTORS_RELATIONSHIPS

PAID_CODE = 'BCCDR'
FREE_CODE = 'BCFDR'  # Filing.FILINGS['changeOfDirectors']['free']['codes']['BC']


def _filing_json(cod: dict) -> dict:
    return {'filing': {'changeOfDirectors': cod}}


def _directors_with_actions(actions_per_director: list) -> dict:
    cod = copy.deepcopy(CHANGE_OF_DIRECTORS)
    cod['directors'] = cod['directors'][:1] * len(actions_per_director)
    cod['directors'] = [copy.deepcopy(d) for d in cod['directors']]
    for director, actions in zip(cod['directors'], actions_per_director):
        director['actions'] = actions
    return cod


def _relationships_with_actions(actions_per_relationship: list) -> dict:
    cod = copy.deepcopy(CHANGE_OF_DIRECTORS_RELATIONSHIPS)
    # use the edited (identifier-bearing, no cessation) item as the base for every entry
    base = cod['relationships'][2]
    cod['relationships'] = [copy.deepcopy(base) for _ in actions_per_relationship]
    for relationship, actions in zip(cod['relationships'], actions_per_relationship):
        if actions is None:
            relationship.pop('actions', None)
        else:
            relationship['actions'] = actions
    return cod


@pytest.mark.parametrize(
    'test_name, actions_per_director, expected_code',
    [
        ('free - edits only', [['nameChanged'], ['addressChanged', 'nameChanged']], FREE_CODE),
        ('free - empty actions', [[]], FREE_CODE),
        ('paid - appointed', [['appointed'], ['nameChanged']], PAID_CODE),
        ('paid - ceased', [['ceased']], PAID_CODE),
    ]
)
def test_cod_fee_code_directors_shape(test_name, actions_per_director, expected_code):
    """Assert the legacy directors shape fee determination is unchanged."""
    filing_json = _filing_json(_directors_with_actions(actions_per_director))

    assert ListFilingResource.get_filing_types_for_cod(filing_json, 'BC', PAID_CODE) == expected_code


@pytest.mark.parametrize(
    'test_name, actions_per_relationship, expected_code',
    [
        ('free - edits only', [['NAME_CHANGED'], ['ADDRESS_CHANGED', 'NAME_CHANGED']], FREE_CODE),
        ('free - CHANGED', [['CHANGED']], FREE_CODE),
        ('free - no actions derives edit', [None], FREE_CODE),
        ('paid - ADDED', [['ADDED'], ['NAME_CHANGED']], PAID_CODE),
        ('paid - REMOVED', [['REMOVED']], PAID_CODE),
    ]
)
def test_cod_fee_code_relationships_shape(test_name, actions_per_relationship, expected_code):
    """Assert the relationships shape maps to the same fee determination."""
    filing_json = _filing_json(_relationships_with_actions(actions_per_relationship))

    assert ListFilingResource.get_filing_types_for_cod(filing_json, 'BC', PAID_CODE) == expected_code


def test_cod_fee_code_relationships_derived_changes():
    """Assert derived appointments/cessations (no actions) are not free."""
    cod = copy.deepcopy(CHANGE_OF_DIRECTORS_RELATIONSHIPS)
    for relationship in cod['relationships']:
        relationship.pop('actions', None)
    # item 0 has no identifier (derives appointed), item 1 has a cessationDate (derives ceased)

    assert ListFilingResource.get_filing_types_for_cod(_filing_json(cod), 'BC', PAID_CODE) == PAID_CODE
