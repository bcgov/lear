# Copyright © 2025 Province of British Columbia
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

"""Tests to assure the Office Model.

Test-Suite to ensure that the Office Model is working as expected.
"""
from business_model.models import Address, Office
from business_model.models.db import VersioningProxy
from tests.models import factory_business, factory_filing


def factory_office_with_addresses(office_type='registeredOffice') -> tuple[Office, Address, Address]:
    """Return the office with mailing and delivery address."""
    mailing_address = Address(
        city="Test City",
        street='mailing-Test Street',
        postal_code='T3S3T3',
        country='TA',
        region='BC',
        address_type=Address.MAILING
    )
    delivery_address = Address(
        city="Test City",
        street='delivery-Test Street',
        postal_code='T3S3T3',
        country='TA',
        region='BC',
        address_type=Address.DELIVERY
    )
    office = Office(office_type=office_type)
    office.addresses.append(mailing_address)
    office.addresses.append(delivery_address)
    return office, mailing_address, delivery_address


def test_office_save(session):
    """Assert that the Office saves."""
    office = Office(office_type='registeredOffice')
    session.add(office)
    session.commit()
    assert office.id


def test_office_with_addresses(session):
    """Assert that the Office can add addresses as expected."""
    office, mailing_address, delivery_address = factory_office_with_addresses()
    session.add(office)
    session.commit()

    assert office.id
    assert mailing_address.id
    assert mailing_address.office_id == office.id
    assert delivery_address.id
    assert delivery_address.office_id == office.id


def test_office_save_to_business(session):
    """Assert that the office integrates with the business model as expected."""
    identifier = 'CP1234567'
    business = factory_business(identifier)

    office, mailing_address, delivery_address = factory_office_with_addresses()
    business.offices.append(office)
    business.save()

    assert office.id
    assert business.id
    assert office.business_id == business.id
    mailing = business.mailing_address.one_or_none()
    delivery = business.delivery_address.one_or_none()
    assert mailing.id == mailing_address.id
    assert delivery.id == delivery_address.id


def test_office_remove_from_business(session):
    """Assert that the office removal from a business creates the expected versioned records."""
    identifier = 'CP1234567'
    business = factory_business(identifier)

    office, mailing_address, delivery_address = factory_office_with_addresses()
    business.offices.append(office)
    business.save()
    office_id = office.id
    mailing_id = mailing_address.id
    delivery_id = delivery_address.id

    transaction_id = VersioningProxy.get_transaction_id(session())
    business.offices.remove(office)
    business.save()

    # assert office and addresses are removed
    mailing = business.mailing_address.one_or_none()
    delivery = business.delivery_address.one_or_none()
    assert mailing is None
    assert delivery is None

    # assert office and mailng exist in versioning tables
    offices_version = VersioningProxy.version_class(session(), Office)
    addresses_version = VersioningProxy.version_class(session(), Address)

    versioned_office: Office = session.query(offices_version)\
        .filter(offices_version.transaction_id == transaction_id)\
        .filter(offices_version.id == office_id).one_or_none()
    assert versioned_office
    assert versioned_office.business_id == business.id

    versioned_mailing_address: Address = session.query(addresses_version)\
        .filter(addresses_version.id == mailing_id).one_or_none()
    assert versioned_mailing_address
    assert versioned_mailing_address.office_id == versioned_office.id
    assert versioned_mailing_address.transaction_id <= versioned_office.transaction_id
    
    versioned_delivery_address: Address = session.query(addresses_version)\
        .filter(addresses_version.id == delivery_id).one_or_none()
    assert versioned_delivery_address
    assert versioned_delivery_address.office_id == versioned_office.id
    assert versioned_delivery_address.transaction_id <= versioned_office.transaction_id
