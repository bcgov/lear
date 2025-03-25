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

"""Tests to assure the Resolution Model.

Test-Suite to ensure that the Resolution Model is working as expected.
"""

from business_model.models import Party, Resolution
from tests.models import factory_business


def test_valid_resolution_save(session):
    """Assert that a valid resolution can be saved."""
    identifier = 'CP1234567'
    business = factory_business(identifier)
    resolution = Resolution(
        resolution_date='2020-02-02',
        resolution_type='SPECIAL',
        business_id=business.id
    )
    resolution.save()
    assert resolution.id


def test_resolution_json(session):
    """Assert the json format of resolution."""
    identifier = 'CP1234567'
    business = factory_business(identifier)
    resolution = Resolution(
        resolution_date='2020-02-02',
        resolution_type='SPECIAL',
        business_id=business.id
    )
    resolution.save()
    resolution_json = {
        'id': resolution.id,
        'type': resolution.resolution_type,
        'date': '2020-02-02'
    }
    assert resolution_json == resolution.json


def test_find_resolution_by_id(session):
    """Assert that the method returns correct value."""
    identifier = 'CP1234567'
    business = factory_business(identifier)
    resolution = Resolution(
        resolution_date='2020-02-02',
        resolution_type='SPECIAL',
        business_id=business.id
    )
    resolution.save()

    res = Resolution.find_by_id(resolution.id)

    assert res
    assert res.json == resolution.json


def test_find_resolution_by_business_and_type(session):
    """Assert that the method returns correct value."""
    identifier = 'CP1234567'
    business = factory_business(identifier)
    resolution_1 = Resolution(
        resolution_date='2020-02-02',
        resolution_type='ORDINARY',
        business_id=business.id
    )
    resolution_2 = Resolution(
        resolution_date='2020-03-03',
        resolution_type='SPECIAL',
        business_id=business.id
    )
    resolution_1.save()
    resolution_2.save()

    res = Resolution.find_by_type(business.id, 'SPECIAL')

    assert res
    assert len(res) == 1
    assert res[0].json == resolution_2.json


def test_special_resolution_with_optional_data(session):
    """Assert that a valid resolution can be saved."""
    identifier = 'CP1234567'
    date_str = '2020-02-02'
    business = factory_business(identifier)
    signing_party = Party(
        first_name='Michael',
        last_name='Crane',
        middle_initial='Joe'
    )
    signing_party.save()
    resolution = Resolution(
        resolution_date=date_str,
        resolution_type='SPECIAL',
        business_id=business.id,
        resolution_sub_type='dissolution',
        signing_date=date_str,
        resolution='This is a sample resolution.',
        signing_party_id=signing_party.id
    )
    resolution.save()
    assert resolution.id
    resolution_json = {
        'id': resolution.id,
        'type': resolution.resolution_type,
        'date': date_str,
        'resolution': resolution.resolution,
        'subType': resolution.resolution_sub_type,
        'signingDate': date_str,
        'signatory': {
            'givenName': signing_party.first_name,
            'familyName': signing_party.last_name,
            'additionalName': signing_party.middle_initial
        }
    }
    assert resolution_json == resolution.json


