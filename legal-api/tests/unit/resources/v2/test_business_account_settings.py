# Copyright (c) 2025, Province of British Columbia
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""Tests to assure the BusinessAccountSettings endpoints."""
from http import HTTPStatus

from legal_api.models import BusinessAccountSettings
from legal_api.services.authz import PUBLIC_USER

from tests.unit.models import factory_business
from tests.unit.services.utils import create_header


def test_get_business_account_settings(app, session, client, jwt, requests_mock):
    """Assert that business account settings are returned."""
    # setup
    identifier = 'BC1234567'
    account_id = 1
    business = factory_business(identifier)
    settings = BusinessAccountSettings.create_or_update(business.id, account_id, {})

    # mock response from auth to give view access
    requests_mock.get(f"{app.config.get('AUTH_SVC_URL')}/entities/{identifier}/authorizations", json={'roles': ['view']})

    # test
    rv = client.get(f'/api/v2/businesses/settings/{account_id}/{identifier}',
                    headers=create_header(jwt, [PUBLIC_USER], identifier))
    # check
    assert rv.status_code == HTTPStatus.OK
    assert settings.json == rv.json


def test_get_business_account_settings_default(app, session, client, jwt, requests_mock):
    """Assert that default business account settings are returned if none exist for the account."""
    # setup
    identifier = 'BC1234567'
    account_id = 1
    business = factory_business(identifier)
    default_settings = BusinessAccountSettings.create_or_update(business.id, None, {'email': 'default@email.com'})

    # mock response from auth to give view access
    requests_mock.get(f"{app.config.get('AUTH_SVC_URL')}/entities/{identifier}/authorizations", json={'roles': ['view']})

    # verify setup
    assert not BusinessAccountSettings.find_by_business_account(business.id, account_id)
    # test
    rv = client.get(f'/api/v2/businesses/settings/{account_id}/{identifier}',
                    headers=create_header(jwt, [PUBLIC_USER], identifier))
    # check
    assert rv.status_code == HTTPStatus.OK
    assert default_settings.json == rv.json


def test_get_business_account_settings_default_exists(app, session, client, jwt, requests_mock):
    """Assert that the business account settings specific to the account are returned when default settings exist."""
    # setup
    identifier = 'BC1234567'
    account_id = 1
    business = factory_business(identifier)
    default_settings = BusinessAccountSettings.create_or_update(business.id, None, {'email': 'default@email.com'})
    account_settings = BusinessAccountSettings.create_or_update(business.id, account_id, {'email': 'account@email.com'})

    # mock response from auth to give view access
    requests_mock.get(f"{app.config.get('AUTH_SVC_URL')}/entities/{identifier}/authorizations", json={'roles': ['view']})

    # verify setup
    assert BusinessAccountSettings.find_by_business_account(business.id, account_id)
    assert default_settings.json != account_settings.json
    # test
    rv = client.get(f'/api/v2/businesses/settings/{account_id}/{identifier}',
                    headers=create_header(jwt, [PUBLIC_USER], identifier))
    # check
    assert rv.status_code == HTTPStatus.OK
    assert account_settings.json == rv.json


def test_get_all_business_account_settings(app, session, client, jwt, requests_mock):
    """Assert that all business account settings specific to the account are returned when default settings exist."""
    # setup
    identifier_1 = 'BC1234567'
    identifier_2 = 'BC1111111'
    account_id = 1
    business_1 = factory_business(identifier_1)
    business_2 = factory_business(identifier_2)
    BusinessAccountSettings.create_or_update(business_1.id, account_id, {})
    BusinessAccountSettings.create_or_update(business_2.id, account_id, {})

    # mock response from auth to give view access
    requests_mock.get(f"{app.config.get('AUTH_SVC_URL')}/orgs/{account_id}/products?include_hidden=true", json=[{'code': 'product'}])

    # verify setup
    assert BusinessAccountSettings.find_by_business_account(business_1.id, account_id)
    assert BusinessAccountSettings.find_by_business_account(business_2.id, account_id)
    # test
    rv = client.get(f'/api/v2/businesses/settings/{account_id}',
                    headers=create_header(jwt, [PUBLIC_USER]))
    # check
    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json) == 2
    assert rv.json[0]['businessIdentifier'] in [identifier_1, identifier_2]
    assert rv.json[1]['businessIdentifier'] in [identifier_1, identifier_2]
    assert rv.json[0]['businessIdentifier'] != rv.json[1]['businessIdentifier']


def test_create_business_account_settings(app, session, client, jwt, requests_mock):
    """Assert creating the business account settings."""
    # setup
    identifier = 'BC1234567'
    account_id = 1
    business = factory_business(identifier)

    # mock response from auth to give edit access
    requests_mock.get(f"{app.config.get('AUTH_SVC_URL')}/entities/{identifier}/authorizations", json={'roles': ['edit']})

    # verify setup
    assert not BusinessAccountSettings.find_by_business_account(business.id, account_id)
    # test
    new_json = {
        'email': 'new@email.com',
        'phone': '123456789',
        'phoneExtension': '1',
        'arReminder': False
    }
    rv = client.patch(f'/api/v2/businesses/settings/{account_id}/{identifier}',
                      headers=create_header(jwt, [PUBLIC_USER], identifier),
                      json=new_json)
    # check
    assert rv.status_code == HTTPStatus.CREATED
    assert rv.json['businessIdentifier'] == identifier
    assert rv.json['accountId'] == account_id
    assert rv.json['email'] == new_json['email']
    assert rv.json['phone'] == new_json['phone']
    assert rv.json['phoneExtension'] == new_json['phoneExtension']
    assert rv.json['arReminder'] == new_json['arReminder']


def test_update_business_account_settings(app, session, client, jwt, requests_mock):
    """Assert updating the business account settings."""
    # setup
    identifier = 'BC1234567'
    account_id = 1
    business = factory_business(identifier)
    initial_email = 'account@email.com'
    BusinessAccountSettings.create_or_update(business.id, account_id, {'email': initial_email})

    # mock response from auth to give edit access
    requests_mock.get(f"{app.config.get('AUTH_SVC_URL')}/entities/{identifier}/authorizations", json={'roles': ['edit']})

    # verify setup
    assert initial_email == (BusinessAccountSettings.find_by_business_account(business.id, account_id)).json['email']
    # test
    new_email = 'new@email.com'
    rv = client.patch(f'/api/v2/businesses/settings/{account_id}/{identifier}',
                      headers=create_header(jwt, [PUBLIC_USER], identifier),
                      json={'email': new_email})
    # check
    assert rv.status_code == HTTPStatus.CREATED
    assert rv.json['email'] == new_email


def test_delete_business_account_settings(app, session, client, jwt, requests_mock):
    """Assert deleting the business account settings."""
    # setup
    identifier = 'BC1234567'
    account_id = 1
    business = factory_business(identifier)
    BusinessAccountSettings.create_or_update(business.id, account_id, {})

    # mock response from auth to give edit access
    requests_mock.get(f"{app.config.get('AUTH_SVC_URL')}/entities/{identifier}/authorizations", json={'roles': ['edit']})

    # verify setup
    assert BusinessAccountSettings.find_by_business_account(business.id, account_id)
    # test
    rv = client.delete(f'/api/v2/businesses/settings/{account_id}/{identifier}',
                       headers=create_header(jwt, [PUBLIC_USER], identifier))
    # check
    assert rv.status_code == HTTPStatus.OK
    assert not BusinessAccountSettings.find_by_business_account(business.id, account_id)
