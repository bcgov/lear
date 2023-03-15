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

"""Tests to assure the business-directors end-point.

Test-Suite to ensure that the /businesses../directors endpoint is working as expected.
"""
import datetime
import pytest
from http import HTTPStatus

from legal_api.models import Business
from legal_api.services.authz import PUBLIC_USER, STAFF_ROLE, SYSTEM_ROLE
from tests.unit.models import Address, PartyRole, factory_business, factory_party_role
from tests.unit.services.utils import create_header


@pytest.mark.parametrize('test_name,role', [
    ('public-user', PUBLIC_USER),
    ('staff', STAFF_ROLE),
    ('system', SYSTEM_ROLE)
])
def test_get_business_directors(app, session, client, jwt, requests_mock, test_name, role):
    """Assert that business directors are returned."""
    # setup
    identifier = 'CP7654321'
    business = factory_business(identifier)
    director_address = Address(city='Test Mailing City', address_type=Address.DELIVERY)
    officer = {
        'firstName': 'Michael',
        'lastName': 'Crane',
        'middleInitial': 'Joe',
        'partyType': 'person',
        'organizationName': ''
    }
    party_role = factory_party_role(
        director_address,
        None,
        officer,
        datetime.datetime(2017, 5, 17),
        None,
        PartyRole.RoleTypes.DIRECTOR
    )
    business.party_roles.append(party_role)
    business.save()
    
    # mock response from auth to give view access (not needed if staff / system)
    requests_mock.get(f"{app.config.get('AUTH_SVC_URL')}/entities/{identifier}/authorizations", json={'roles': ['view']})

    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/directors',
                    headers=create_header(jwt, [role], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.OK
    assert 'directors' in rv.json
    assert rv.json['directors'][0]['deliveryAddress']['addressCity'] == 'Test Mailing City'


def test_bcorp_get_business_directors(session, client, jwt):
    """Assert that business directors are returned."""
    # setup
    identifier = 'CP7654321'
    business = factory_business(identifier, datetime.datetime.now(), None, Business.LegalTypes.BCOMP.value)
    director_address = Address(city='Test Delivery City', address_type=Address.DELIVERY)
    director_mailing_address = Address(city='Test Mailing City', address_type=Address.MAILING)
    officer = {
        'firstName': 'Michael',
        'lastName': 'Crane',
        'middleInitial': 'Joe',
        'partyType': 'person',
        'organizationName': ''
    }
    party_role = factory_party_role(
        director_address,
        director_mailing_address,
        officer,
        datetime.datetime(2017, 5, 17),
        None,
        PartyRole.RoleTypes.DIRECTOR
    )
    business.party_roles.append(party_role)
    business.save()

    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/directors',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.OK
    assert 'directors' in rv.json
    assert rv.json['directors'][0]['mailingAddress']['addressCity'] == 'Test Mailing City'


def test_get_business_no_directors(session, client, jwt):
    """Assert that business directors are not returned."""
    # setup
    identifier = 'CP7654321'
    factory_business(identifier)

    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/directors',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.OK
    assert rv.json['directors'] == []


def test_get_business_ceased_directors(session, client, jwt):
    """Assert that business directors are not returned."""
    # setup
    identifier = 'CP7654321'
    business = factory_business(identifier)
    officer = {
        'firstName': 'Michael',
        'lastName': 'Crane',
        'middleInitial': 'Joe',
        'partyType': 'person',
        'organizationName': ''
    }
    party_role = factory_party_role(
        None,
        None,
        officer,
        datetime.datetime(2012, 5, 17),
        datetime.datetime(2013, 5, 17),
        PartyRole.RoleTypes.DIRECTOR
    )
    business.party_roles.append(party_role)
    business.save()

    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/directors',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.OK
    assert rv.json['directors'] == []


def test_get_business_director_by_id(session, client, jwt):
    """Assert that business director is returned."""
    # setup
    identifier = 'CP7654321'
    business = factory_business(identifier)
    officer = {
        'firstName': 'Michael',
        'lastName': 'Crane',
        'middleInitial': 'Joe',
        'partyType': 'person',
        'organizationName': ''
    }
    party_role = factory_party_role(
        None,
        None,
        officer,
        datetime.datetime(2017, 5, 17),
        None,
        PartyRole.RoleTypes.DIRECTOR
    )
    business.party_roles.append(party_role)
    business.save()
    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/directors/{party_role.id}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.OK


def test_get_business_director_by_invalid_id(session, client, jwt):
    """Assert that business directors are not returned."""
    # setup
    identifier = 'CP7654321'
    business = factory_business(identifier)
    director_id = 5000
    business.save()

    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/directors/{director_id}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{identifier} director not found'}


def test_get_directors_invalid_business(session, client, jwt):
    """Assert that business is not returned."""
    # setup
    identifier = 'CP7654321'

    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/directors',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{identifier} not found'}


def test_directors_mailing_address(session, client, jwt):
    """Assert that bcorp directors have a mailing and delivery address."""
    # setup
    identifier = 'CP7654321'
    business = factory_business(identifier, datetime.datetime(2017, 4, 17), None, Business.LegalTypes.BCOMP.value)
    delivery_address = Address(city='Test Delivery City', address_type=Address.DELIVERY)
    mailing_address = Address(city='Test Mailing City', address_type=Address.MAILING)
    officer = {
        'firstName': 'Michael',
        'lastName': 'Crane',
        'middleInitial': 'Joe',
        'partyType': 'person',
        'organizationName': ''
    }
    party_role = factory_party_role(
        delivery_address,
        mailing_address,
        officer,
        datetime.datetime(2017, 5, 17),
        None,
        PartyRole.RoleTypes.DIRECTOR
    )
    business.party_roles.append(party_role)
    business.save()

    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/directors',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.OK
    assert 'directors' in rv.json
    assert rv.json['directors'][0]['deliveryAddress']['addressCity'] == 'Test Delivery City'
    assert rv.json['directors'][0]['mailingAddress']['addressCity'] == 'Test Mailing City'


def test_directors_coop_no_mailing_address(session, client, jwt):
    """Assert that coop directors have a mailing and delivery address."""
    # setup
    identifier = 'CP7654321'
    business = factory_business(identifier)
    delivery_address = Address(city='Test Delivery City', address_type=Address.DELIVERY)
    officer = {
        'firstName': 'Michael',
        'lastName': 'Crane',
        'middleInitial': 'Joe',
        'partyType': 'person',
        'organizationName': ''
    }
    party_role = factory_party_role(
        delivery_address,
        None,
        officer,
        datetime.datetime(2017, 5, 17),
        None,
        PartyRole.RoleTypes.DIRECTOR
    )
    business.party_roles.append(party_role)
    business.save()

    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/directors',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.OK
    assert 'directors' in rv.json
    assert rv.json['directors'][0]['deliveryAddress']['addressCity'] == 'Test Delivery City'
    assert 'mailingAddress' not in rv.json['directors'][0]


def test_directors_unauthorized(app, session, client, jwt, requests_mock):
    """Assert that directors are not returned for an unauthorized user."""
    # setup
    identifier = 'CP7654321'
    business = factory_business(identifier)
    business.save()

    requests_mock.get(f"{app.config.get('AUTH_SVC_URL')}/entities/{identifier}/authorizations", json={'roles': []})

    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/directors',
                    headers=create_header(jwt, [PUBLIC_USER], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.UNAUTHORIZED
    assert rv.json == {'message': f'You are not authorized to view directors for {identifier}.'}
