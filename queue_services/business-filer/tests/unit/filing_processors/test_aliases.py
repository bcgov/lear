# Copyright © 2025 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""The Unit Tests for the aliases processor."""
import random
from business_model.models import Alias

from business_filer.filing_processors.filing_components import aliases
from tests.unit import create_business


def test_new_aliases(app, session):
    """Assert that the new aliases are created."""
    # setup
    identifier = f'BC{random.randint(1000000, 9999999)}'
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
    identifier = f'BC{random.randint(1000000, 9999999)}'
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
    identifier = f'BC{random.randint(1000000, 9999999)}'
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
    identifier = f'BC{random.randint(1000000, 9999999)}'
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
