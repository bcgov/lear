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

"""Tests to assure the business-addresses end-point.

Test-Suite to ensure that the /businesses../addresses endpoint is working as expected.
"""
from http import HTTPStatus

from legal_api.services.authz import STAFF_ROLE
from tests.unit.models import Address, Office, factory_business
from tests.unit.services.utils import create_header


def test_get_business_addresses(session, client, jwt):
    """Assert that business addresses are returned."""
    # setup
    identifier = 'CP7654321'
    business = factory_business(identifier)
    mailing_address = Address(city='Test Mailing City', address_type=Address.MAILING)
    #business.mailing_address.append(mailing_address)
    delivery_address = Address(city='Test Delivery City', address_type=Address.DELIVERY)
    #business.delivery_address.append(delivery_address)
    office = Office(office_type='registeredOffice')
    office.addresses.append(mailing_address)
    office.addresses.append(delivery_address)
    business.offices.append(office)
    business.save()

    # test
    rv = client.get(f'/api/v1/businesses/{identifier}/addresses',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.OK
    assert 'registeredOffice' in rv.json
    assert 'mailingAddress' in rv.json['registeredOffice']
    assert 'deliveryAddress' in rv.json['registeredOffice']


def test_get_business_no_addresses(session, client, jwt):
    """Assert that business addresses are not returned."""
    # setup
    identifier = 'CP7654321'
    business = factory_business(identifier)

    # test
    rv = client.get(f'/api/v1/businesses/{identifier}/addresses',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{business.identifier} address not found'}


def test_get_business_addresses_by_id(session, client, jwt):
    """Assert that business address is returned."""
    # setup
    identifier = 'CP7654321'
    business = factory_business(identifier)
    mailing_address = Address(city='Test Mailing City', address_type=Address.MAILING, \
     business_id=business.id)
    office = Office(office_type='registeredOffice')
    office.addresses.append(mailing_address)
    business.offices.append(office)
    business.save()

    # test
    rv = client.get(f'/api/v1/businesses/{identifier}/addresses/{mailing_address.id}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.OK
    assert 'mailingAddress' in rv.json


def test_get_business_addresses_by_invalid_id(session, client, jwt):
    """Assert that business addresses are not returned."""
    # setup
    identifier = 'CP7654321'
    business = factory_business(identifier)
    address_id = 1000
    # mailing_address = Address(city='Test Mailing City', address_type=Address.MAILING)
    # business.mailing_address.append(mailing_address)
    business.save()

    # test
    rv = client.get(f'/api/v1/businesses/{identifier}/addresses/{address_id}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{identifier} address not found'}


def test_get_business_mailing_addresses_by_type(session, client, jwt):
    """Assert that business address type is returned."""
    # setup
    identifier = 'CP7654321'
    business = factory_business(identifier)
    mailing_address = Address(city='Test Mailing City', address_type=Address.MAILING, \
    business_id=business.id)
    office = Office(office_type='registeredOffice')
    office.addresses.append(mailing_address)
    business.offices.append(office)
    business.save()

    # test
    rv = client.get(f'/api/v1/businesses/{identifier}/addresses?addressType={Address.JSON_MAILING}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.OK
    assert Address.JSON_MAILING in rv.json


def test_get_business_delivery_addresses_by_type_missing_address(session, client, jwt):
    """Assert that business addresses are not returned."""
    # setup
    identifier = 'CP7654321'
    business = factory_business(identifier)
    delivery_address = Address(city='Test Delivery City', address_type=Address.DELIVERY, \
    business_id=business.id)
    office = Office(office_type='registeredOffice')
    office.addresses.append(delivery_address)
    business.offices.append(office)
    business.save()

    # test
    rv = client.get(f'/api/v1/businesses/{identifier}/addresses?addressType={Address.JSON_MAILING}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{identifier} address not found'}


def test_get_business_delivery_addresses_by_type(session, client, jwt):
    """Assert that business address type is returned."""
    # setup
    identifier = 'CP7654321'
    business = factory_business(identifier)
    delivery_address = Address(city='Test Delivery City', address_type=Address.DELIVERY, \
    business_id=business.id)
    office = Office(office_type='registeredOffice')
    office.addresses.append(delivery_address)
    business.offices.append(office)
    business.save()

    # test
    rv = client.get(f'/api/v1/businesses/{identifier}/addresses?addressType={Address.JSON_DELIVERY}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.OK
    assert Address.JSON_DELIVERY in rv.json


def test_get_addresses_invalid_business(session, client, jwt):
    """Assert that business is not returned."""
    # setup
    identifier = 'CP7654321'

    # test
    rv = client.get(f'/api/v1/businesses/{identifier}/addresses',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{identifier} not found'}


def test_get_addresses_invalid_type(session, client, jwt):
    """Assert that business addresses is not returned."""
    # setup
    identifier = 'CP7654321'
    address_type = 'INVALID_TYPE'
    business = factory_business(identifier)
    business.save()

    # test
    rv = client.get(f'/api/v1/businesses/{identifier}/addresses?addressType={address_type}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json == {'message': f'{address_type} not a valid address type'}
