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
"""The Unit Tests for the aliases processor."""
from business_model.models import Alias

from business_filer.filing_processors.filing_components import aliases
from tests.unit import create_business


def test_new_aliases(app, session):
    """Assert that the new aliases are created."""
    # setup
    identifier = 'BC1234567'
    business = create_business(identifier)
    component = {'nameTranslations': [{'name': 'MÉDIAS DE TRANSPORT INC.'}, {'name': 'CLUDIANT MEDIA INC.'}]}

    # test
    aliases.update_aliases(business, component.get('nameTranslations'))

    # validate
    new_aliases = business.aliases.all()
    assert len(component['nameTranslations']) == len(new_aliases)


def test_modified_aliases(app, session):
    """Assert that aliases are altered."""
    # setup
    identifier = 'BC1234567'
    old_value_1 = 'A1 LTD.'
    new_value_1 = 'SOCIÉTÉ GÉNÉRALE'
    old_value_2 = 'B1 LTD.'
    new_value_2 = 'B2 LTD.'
    business = create_business(identifier)
    business.aliases.append(Alias(alias=old_value_1, type=Alias.AliasType.TRANSLATION.value))
    business.aliases.append(Alias(alias=old_value_2, type=Alias.AliasType.TRANSLATION.value))
    business.save()
    business_aliases = business.aliases.all()
    assert len(business_aliases) == 2
    component = {'nameTranslations': [
        {
            'id': str(business_aliases[0].id),
            'name': new_value_1
        },
        {
            'id': str(business_aliases[1].id),
            'name': new_value_2
        }
    ]}

    # test
    aliases.update_aliases(business, component.get('nameTranslations'))

    # validate
    business_aliases = business.aliases.all()
    assert len(business_aliases) == 2
    for alias in component['nameTranslations']:
        business_alias = next((x for x in business_aliases if str(x.id) == alias['id']), None)
        assert business_alias.alias == alias['name'].upper()


def test_cease_aliases(app, session):
    """Assert that aliases are removed."""
    # setup
    identifier = 'BC1234567'
    alias_1 = 'A1 LTD.'
    alias_2 = 'A2 LTD.'
    alias_3 = 'A3 LTD.'
    business = create_business(identifier)
    business.aliases.append(Alias(alias=alias_1, type=Alias.AliasType.TRANSLATION.value))
    business.aliases.append(Alias(alias=alias_2, type=Alias.AliasType.TRANSLATION.value))
    business.save()
    assert len(business.aliases.all()) == 2

    component = {'nameTranslations': [
        {'name': alias_3}
    ]}

    # test
    aliases.update_aliases(business, component.get('nameTranslations'))

    # validate
    business_aliases = business.aliases.all()
    assert 1 == len(business_aliases)
    assert business_aliases[0].alias == alias_3.upper()


def test_all_aliases(app, session):
    """Assert that aliases are altered correctly."""
    # setup
    identifier = 'BC1234567'
    alias_1 = 'A1 LTD.'
    alias_2 = 'A2 LTD.'
    alias_3 = 'A3 LTD.'
    alias_4 = 'A4 LTD.'
    business = create_business(identifier)
    business.aliases.append(Alias(alias=alias_1, type=Alias.AliasType.TRANSLATION.value))
    business.aliases.append(Alias(alias=alias_2, type=Alias.AliasType.TRANSLATION.value))
    business.save()
    business_aliases = business.aliases.all()
    assert len(business_aliases) == 2
    component = {'nameTranslations':  [
        {
            'id': str(business_aliases[0].id),
            'name': alias_3
        },
        {
            'name': alias_4
        }
    ]}

    # test
    aliases.update_aliases(business, component.get('nameTranslations'))

    # validate
    business_aliases = business.aliases.all()
    assert 2 == len(business_aliases)
    assert next((x for x in business_aliases if
                 str(x.id) == component['nameTranslations'][0]['id']), None).alias == alias_3.upper()
    assert next((x for x in business_aliases if x.alias == component['nameTranslations'][1]['name'].upper()), None)
    assert not next((x for x in business_aliases if x.alias == alias_1.upper()), None)
    assert not next((x for x in business_aliases if x.alias == alias_2.upper()), None)
