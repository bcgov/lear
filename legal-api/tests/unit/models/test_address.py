# Copyright © 2019 Province of British Columbia
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

"""Tests to assure the Address Model.

Test-Suite to ensure that the Address Model is working as expected.
"""
from legal_api.models import Address
from tests.unit.models import factory_business


def test_address_json(session):
    """Assert that the address renders our json format correctly."""
    identifier = 'CP1234567'
    address = Address(
        city='Test City',
        street=f'{identifier}-Test Street',
        postal_code='T3S3T3',
        country='TA',
        region='BC',
        address_type=Address.MAILING
    )

    address_json = {
        'streetAddress': address.street,
        'streetAddressAdditional': address.street_additional,
        'addressType': address.address_type,
        'addressCity': address.city,
        'addressRegion': address.region,
        'addressCountry': address.country,
        'postalCode': address.postal_code,
        'deliveryInstructions': address.delivery_instructions
    }

    assert address.json == address_json


def test_address_save(session):
    """Assert that the address saves correctly."""
    identifier = 'CP1234567'
    address = Address(
        city='Test City',
        street=f'{identifier}-Test Street',
        postal_code='T3S3T3',
        country='TA',
        region='BC',
        address_type=Address.MAILING
    )

    address.save()
    assert address.id


def test_address_save_to_business(session):
    """Assert that the address saves correctly."""
    identifier = 'CP1234567'
    business = factory_business(identifier)

    address = Address(
        city='Test City',
        street=f'{identifier}-Test Street',
        postal_code='T3S3T3',
        country='TA',
        region='BC',
        address_type=Address.MAILING
    )

    business.business_mailing_address.append(address)
    business.save()

    mailing = business.business_mailing_address.one_or_none()
    assert mailing.id
