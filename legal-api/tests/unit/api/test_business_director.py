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
from http import HTTPStatus

from legal_api.services.authz import STAFF_ROLE
from tests.unit.models import Address, Director, factory_business
from tests.unit.services.utils import create_header


def test_get_business_directors(session, client, jwt):
    """Assert that business directors are returned."""
    # setup
    identifier = 'CP7654321'
    business = factory_business(identifier)
    director = Director(
        first_name='Michael',
        last_name='Crane',
        middle_initial='Joe',
        title='VP',
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None
    )
    director_address = Address(city='Test Mailing City', address_type=Address.DELIVERY)
    director.delivery_address = director_address
    business.directors.append(director)
    business.save()

    # test
    rv = client.get(f'/api/v1/businesses/{identifier}/directors',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.OK
    assert 'directors' in rv.json
    assert rv.json['directors'][0]['deliveryAddress']['addressCity'] == 'Test Mailing City'


def test_bcorp_get_business_directors(session, client, jwt):
    """Assert that business directors are returned."""
    # setup
    identifier = 'CP7654321'
    business = factory_business(identifier, datetime.datetime.now(), None, 'BC')
    director = Director(
        first_name='Michael',
        last_name='Crane',
        middle_initial='Joe',
        title='VP',
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None
    )
    director_address = Address(city='Test Delivery City', address_type=Address.DELIVERY)
    director_mailing_address = Address(city='Test Mailing City', address_type=Address.MAILING)
    director.delivery_address = director_address
    director.mailing_address = director_mailing_address
    business.directors.append(director)
    business.save()

    # test
    rv = client.get(f'/api/v1/businesses/{identifier}/directors',
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
    business = factory_business(identifier)

    # test
    rv = client.get(f'/api/v1/businesses/{identifier}/directors',
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
    director = Director(
        first_name='Michael',
        last_name='Crane',
        middle_initial='Joe',
        title='VP',
        appointment_date=datetime.datetime(2012, 5, 17),
        cessation_date=datetime.datetime(2013, 5, 17)
    )
    business.directors.append(director)
    business.save()

    # test
    rv = client.get(f'/api/v1/businesses/{identifier}/directors',
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
    director = Director(
        first_name='Michael',
        last_name='Crane',
        middle_initial='Joe',
        title='VP',
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None
    )
    business.directors.append(director)
    business.save()
    # test
    rv = client.get(f'/api/v1/businesses/{identifier}/directors/{director.id}',
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
    rv = client.get(f'/api/v1/businesses/{identifier}/directors/{director_id}',
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
    rv = client.get(f'/api/v1/businesses/{identifier}/directors',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{identifier} not found'}


def test_directors_mailing_address(session, client, jwt):
    """Assert that bcorp directors have a mailing and delivery address."""
    # setup
    identifier = 'CP7654321'
    business = factory_business(identifier, datetime.datetime(2017, 4, 17), None, 'BC')
    director = Director(
        first_name='Michael',
        last_name='Crane',
        middle_initial='Joe',
        title='VP',
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None
    )
    delivery_address = Address(city='Test Delivery City', address_type=Address.DELIVERY)
    mailing_address = Address(city='Test Mailing City', address_type=Address.MAILING)
    director.delivery_address = delivery_address
    director.mailing_address = mailing_address
    business.directors.append(director)
    business.save()

    # test
    rv = client.get(f'/api/v1/businesses/{identifier}/directors',
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
    director = Director(
        first_name='Michael',
        last_name='Crane',
        middle_initial='Joe',
        title='VP',
        appointment_date=datetime.datetime(2017, 5, 17),
        cessation_date=None
    )
    delivery_address = Address(city='Test Delivery City', address_type=Address.DELIVERY)
    director.delivery_address = delivery_address
    business.directors.append(director)
    business.save()

    # test
    rv = client.get(f'/api/v1/businesses/{identifier}/directors',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.OK
    assert 'directors' in rv.json
    assert rv.json['directors'][0]['deliveryAddress']['addressCity'] == 'Test Delivery City'
    assert 'mailingAddress' not in rv.json['directors'][0]
