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

"""Tests to assure the RegistrationBootstrap Service.

Test-Suite to ensure that the RegistrationBootstrap Service is working as expected.
"""
import json
import random
import uuid
from http import HTTPStatus
import os

import pytest
import requests
from flask import current_app

from business_account.AccountService import AccountService


@pytest.fixture(scope='function')
def account(app):
    """Create an account to be used for testing."""
    with app.app_context():
        auth_url = current_app.config.get('AUTH_SVC_URL')
        account_url = auth_url + '/orgs/{account_id}/affiliations'
        account_url = account_url[:account_url.rfind('{') - 1]

        org_data = json.dumps({'name': str(uuid.uuid4())})
        token = AccountService.get_bearer_token()

        # with app.app_context():
        rv = requests.post(
            url=account_url,
            data=org_data,
            headers={**AccountService.CONTENT_TYPE_JSON,
                     'Authorization': AccountService.BEARER + token},
            timeout=20
        )

        account_id = rv.json()['id']

        yield account_id

        rv = requests.delete(url=f'{account_url}/{account_id}',
                             headers={'Authorization': AccountService.BEARER + token},
                             timeout=20
                             )
        print(rv)

def test_get_bearer_token(app):
    with app.app_context():
        auth_url = current_app.config.get('AUTH_SVC_URL')
        account_url = auth_url + '/orgs/{account_id}/affiliations'
        account_url = account_url[:account_url.rfind('{') - 1]

        token = AccountService.get_bearer_token()

        assert token is not None

@pytest.mark.skipif((os.getenv('RUN_AFFILIATION_TESTS', False) is False),
                                             reason='Account affiliation tests are only run when requested.')
def test_account_affiliation_integration(account):
    """Assert that the affiliation can be created."""
    business_registration = (f'T{random.SystemRandom().getrandbits(0x58)}')[:10]
    r = AccountService.create_affiliation(account=account,
                                          business_registration=business_registration,
                                          business_name='')

    assert r == HTTPStatus.OK

    r = AccountService.update_entity(business_registration=business_registration,
                                     business_name=business_registration,
                                     corp_type_code='BEN')

    assert r == HTTPStatus.OK

    r = AccountService.delete_affiliation(account=account,
                                          business_registration=business_registration)

    # @TODO change this next sprint when affiliation service is updated.
    assert r == HTTPStatus.OK
