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

"""Tests to assure the Alias Model.

Test-Suite to ensure that the Alias Model is working as expected.
"""

from business_model import Alias
from tests.models import factory_legal_entity


def test_valid_alias_save(session):
    """Assert that a valid alias can be saved."""
    identifier = 'CP1234567'
    legal_entity =factory_legal_entity(identifier)
    alias = Alias(
        alias='ABC Ltd.',
        type='TRANSLATION',
        legal_entity_id=legal_entity.id
    )
    alias.save()
    assert alias.id


def test_alias_json(session):
    """Assert the json format of alias."""
    identifier = 'CP1234567'
    legal_entity =factory_legal_entity(identifier)
    alias = Alias(
        alias='ABC Ltd.',
        type='TRANSLATION',
        legal_entity_id=legal_entity.id
    )
    alias.save()
    alias_json = {
        'id': str(alias.id),
        'name': alias.alias,
        'type': alias.type
    }
    assert alias_json == alias.json


def test_find_alias_by_id(session):
    """Assert that the method returns correct value."""
    identifier = 'CP1234567'
    legal_entity =factory_legal_entity(identifier)
    alias = Alias(
        alias='ABC Ltd.',
        type='TRANSLATION',
        legal_entity_id=legal_entity.id
    )
    alias.save()

    res = Alias.find_by_id(alias.id)

    assert res
    assert res.json == alias.json


def test_find_alias_by_business_and_type(session):
    """Assert that the method returns correct value."""
    identifier = 'CP1234567'
    legal_entity =factory_legal_entity(identifier)
    alias1 = Alias(
        alias='ABC Ltd.',
        type='TRANSLATION',
        legal_entity_id=legal_entity.id
    )
    alias2 = Alias(
        alias='DEF Ltd.',
        type='DBA',
        legal_entity_id=legal_entity.id
    )
    alias1.save()
    alias2.save()

    res = Alias.find_by_type(legal_entity.id, 'TRANSLATION')

    assert res
    assert len(res) == 1
    assert res[0].alias == 'ABC Ltd.'
