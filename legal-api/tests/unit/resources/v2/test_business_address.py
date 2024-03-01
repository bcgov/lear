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

import pytest

from legal_api.services.authz import ACCOUNT_IDENTITY, PUBLIC_USER, STAFF_ROLE, SYSTEM_ROLE
from tests.unit import nested_session
from tests.unit.models import Address, Office, factory_legal_entity
from tests.unit.services.utils import create_header

#TODO: Works with unique identifiers but DB reset fix will resolve the randomly failing tests (ticket# 20121)
@pytest.mark.parametrize(
    "test_name,role,identifier",
    [
        ("public-user", PUBLIC_USER, "CP7654321"),
        ("account-identity", ACCOUNT_IDENTITY, "CP7654322"),
        ("staff", STAFF_ROLE, "CP7654323"),
        ("system", SYSTEM_ROLE, "CP7654324"),
    ],
)
def test_get_business_addresses(app, session, client, jwt, requests_mock, test_name, role, identifier):
    """Assert that business addresses are returned."""
    # setup
    with nested_session(session):
        legal_entity = factory_legal_entity(identifier)
        mailing_address = Address(city="Test Mailing City", address_type=Address.MAILING)
        delivery_address = Address(city="Test Delivery City", address_type=Address.DELIVERY)
        office = Office(office_type="registeredOffice")
        office.addresses.append(mailing_address)
        office.addresses.append(delivery_address)
        legal_entity.offices.append(office)
        legal_entity.save()

        # mock response from auth to give view access (not needed if staff / system)
        requests_mock.get(
            f"{app.config.get('AUTH_SVC_URL')}/entities/{identifier}/authorizations", json={"roles": ["view"]}
        )

        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/addresses",
            headers=create_header(jwt, [role], identifier, **{"Accept-Version": "v1"}),
        )

        # check response
        assert rv.status_code == HTTPStatus.OK
        assert "registeredOffice" in rv.json
        assert "mailingAddress" in rv.json["registeredOffice"]
        assert "deliveryAddress" in rv.json["registeredOffice"]


def test_get_business_no_addresses(session, client, jwt):
    """Assert that business addresses are not returned."""
    # setup
    with nested_session(session):
        identifier = "CP7654321"
        legal_entity = factory_legal_entity(identifier)

        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/addresses", headers=create_header(jwt, [STAFF_ROLE], identifier)
        )
        # check
        assert rv.status_code == HTTPStatus.NOT_FOUND
        assert rv.json == {"message": f"{legal_entity.identifier} address not found"}


def test_get_business_addresses_by_id(session, client, jwt):
    """Assert that business address is returned."""
    # setup
    with nested_session(session):
        identifier = "CP7654321"
        legal_entity = factory_legal_entity(identifier)
        mailing_address = Address(
            city="Test Mailing City", address_type=Address.MAILING, legal_entity_id=legal_entity.id
        )
        office = Office(office_type="registeredOffice")
        office.addresses.append(mailing_address)
        legal_entity.offices.append(office)
        legal_entity.save()

        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/addresses/{mailing_address.id}",
            headers=create_header(jwt, [STAFF_ROLE], identifier),
        )
        # check
        assert rv.status_code == HTTPStatus.OK
        assert "mailingAddress" in rv.json


def test_get_business_addresses_by_invalid_id(session, client, jwt):
    """Assert that business addresses are not returned."""
    # setup
    with nested_session(session):
        identifier = "CP7654321"
        legal_entity = factory_legal_entity(identifier)
        address_id = 1000
        # mailing_address = Address(city='Test Mailing City', address_type=Address.MAILING)
        # legal_entity.mailing_address.append(mailing_address)
        legal_entity.save()

        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/addresses/{address_id}",
            headers=create_header(jwt, [STAFF_ROLE], identifier),
        )
        # check
        assert rv.status_code == HTTPStatus.NOT_FOUND
        assert rv.json == {"message": f"{identifier} address not found"}


def test_get_business_mailing_addresses_by_type(session, client, jwt):
    """Assert that business address type is returned."""
    # setup
    with nested_session(session):
        identifier = "CP7654321"
        legal_entity = factory_legal_entity(identifier)
        mailing_address = Address(
            city="Test Mailing City", address_type=Address.MAILING, legal_entity_id=legal_entity.id
        )
        office = Office(office_type="registeredOffice")
        office.addresses.append(mailing_address)
        legal_entity.offices.append(office)
        legal_entity.save()

        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/addresses?addressType={Address.JSON_MAILING}",
            headers=create_header(jwt, [STAFF_ROLE], identifier),
        )
        # check
        assert rv.status_code == HTTPStatus.OK
        assert Address.JSON_MAILING in rv.json


def test_get_business_delivery_addresses_by_type_missing_address(session, client, jwt):
    """Assert that business addresses are not returned."""
    # setup
    with nested_session(session):
        identifier = "CP7654321"
        legal_entity = factory_legal_entity(identifier)
        delivery_address = Address(
            city="Test Delivery City", address_type=Address.DELIVERY, legal_entity_id=legal_entity.id
        )
        office = Office(office_type="registeredOffice")
        office.addresses.append(delivery_address)
        legal_entity.offices.append(office)
        legal_entity.save()

        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/addresses?addressType={Address.JSON_MAILING}",
            headers=create_header(jwt, [STAFF_ROLE], identifier),
        )
        # check
        assert rv.status_code == HTTPStatus.NOT_FOUND
        assert rv.json == {"message": f"{identifier} address not found"}


def test_get_business_delivery_addresses_by_type(session, client, jwt):
    """Assert that business address type is returned."""
    # setup
    with nested_session(session):
        identifier = "CP7654321"
        legal_entity = factory_legal_entity(identifier)
        delivery_address = Address(
            city="Test Delivery City", address_type=Address.DELIVERY, legal_entity_id=legal_entity.id
        )
        office = Office(office_type="registeredOffice")
        office.addresses.append(delivery_address)
        legal_entity.offices.append(office)
        legal_entity.save()

        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/addresses?addressType={Address.JSON_DELIVERY}",
            headers=create_header(jwt, [STAFF_ROLE], identifier),
        )
        # check
        assert rv.status_code == HTTPStatus.OK
        assert Address.JSON_DELIVERY in rv.json


def test_get_addresses_invalid_business(session, client, jwt):
    """Assert that business is not returned."""
    # setup
    with nested_session(session):
        identifier = "CP7654321"

        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/addresses", headers=create_header(jwt, [STAFF_ROLE], identifier)
        )
        # check
        assert rv.status_code == HTTPStatus.NOT_FOUND
        assert rv.json == {"message": f"{identifier} not found"}


def test_get_addresses_invalid_type(session, client, jwt):
    """Assert that business addresses is not returned."""
    # setup
    with nested_session(session):
        identifier = "CP7654321"
        address_type = "INVALID_TYPE"
        legal_entity = factory_legal_entity(identifier)
        legal_entity.save()

        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/addresses?addressType={address_type}",
            headers=create_header(jwt, [STAFF_ROLE], identifier),
        )
        # check
        assert rv.status_code == HTTPStatus.BAD_REQUEST
        assert rv.json == {"message": f"{address_type} not a valid address type"}


def test_get_addresses_unauthorized(app, session, client, jwt, requests_mock):
    """Assert that business addresses is not returned for an unauthorized user."""
    # setup
    with nested_session(session):
        identifier = "CP7654321"
        legal_entity = factory_legal_entity(identifier)
        legal_entity.save()

        requests_mock.get(f"{app.config.get('AUTH_SVC_URL')}/entities/{identifier}/authorizations", json={"roles": []})

        # test
        rv = client.get(
            f"/api/v2/businesses/{identifier}/addresses", headers=create_header(jwt, [PUBLIC_USER], identifier)
        )
        # check
        assert rv.status_code == HTTPStatus.UNAUTHORIZED
        assert rv.json == {"message": f"You are not authorized to view addresses for {identifier}."}
