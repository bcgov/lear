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
"""The Unit Tests for the Incorporation filing."""
import copy
import random

from legal_api.models import Alias, Business
from registry_schemas.example_data import ALTERATION_FILING_TEMPLATE

from entity_filer.filing_processors.filing_components import aliases
from entity_filer.worker import process_filing
from tests.unit import create_business, create_filing


def test_new_aliases(app, session):
    """Assert that the business is altered."""
    # setup
    identifier = 'BC1234567'
    business = create_business(identifier)
    component = {'nameTranslations': {
        'new': ['MÉDIAS DE TRANSPORT INC.', 'CLUDIANT MEDIA INC.']
    }}

    # test
    aliases.update_aliases(business, component.get('nameTranslations'))

    # validate
    new_aliases = business.aliases.all()
    assert len(component['nameTranslations']['new']) == len(new_aliases)
    assert set(component['nameTranslations']['new']) == set([n.alias for n in new_aliases])


def test_modified_aliases(app, session):
    """Assert that the business is altered."""
    # setup
    identifier = 'BC1234567'
    old_value = 'A1 LTD.'
    new_value = 'SOCIÉTÉ GÉNÉRALE'
    business = create_business(identifier)
    business.aliases.append(Alias(alias=old_value, type=Alias.AliasType.TRANSLATION.value))
    business.save()
    component = {'nameTranslations': {
        'modified': [{
            'oldValue': old_value,
            'newValue': new_value
        }, {
            'oldValue': 'missing',
            'newValue': 'missing'
        }]
    }}

    # test
    aliases.update_aliases(business, component.get('nameTranslations'))

    # validate
    business_aliases = business.aliases.all()
    assert 1 == len(business_aliases)
    assert new_value == business_aliases[0].alias


def test_cease_aliases(app, session):
    """Assert that the business is altered."""
    # setup
    identifier = 'BC1234567'
    old_value = 'A1 LTD.'
    business = create_business(identifier)
    business.aliases.append(Alias(alias=old_value, type=Alias.AliasType.TRANSLATION.value))
    business.save()
    component = {'nameTranslations': {
        'ceased': ['A1 LTD.', 'B2']
    }}

    # test
    aliases.update_aliases(business, component.get('nameTranslations'))

    # validate
    business_aliases = business.aliases.all()
    assert 0 == len(business_aliases)


def test_all_aliases(app, session):
    """Assert that the business is altered."""
    # setup
    identifier = 'BC1234567'
    old_value = 'A1 LTD.'
    new_value = 'SOCIÉTÉ GÉNÉRALE'
    business = create_business(identifier)
    business.aliases.append(Alias(alias=old_value, type=Alias.AliasType.TRANSLATION.value))
    business.aliases.append(Alias(alias='B1', type=Alias.AliasType.TRANSLATION.value))
    business.save()
    component = {'nameTranslations': {
        'new': ['MÉDIAS DE TRANSPORT INC.', 'CLUDIANT MEDIA INC.'],
        'modified': [{
            'oldValue': old_value,
            'newValue': new_value
        }],
        'ceased': ['B1', 'B2']
    }}

    # test
    aliases.update_aliases(business, component.get('nameTranslations'))

    expected = ['SOCIÉTÉ GÉNÉRALE', 'MÉDIAS DE TRANSPORT INC.', 'CLUDIANT MEDIA INC.']

    # validate
    business_aliases = business.aliases.all()
    assert 3 == len(business_aliases)
    assert set(expected) == set([b.alias for b in business_aliases])
