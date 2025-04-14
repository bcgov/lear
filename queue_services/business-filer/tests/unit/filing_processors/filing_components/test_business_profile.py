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
"""The Unit Tests for the business filing component processors."""
import pytest
from business_model.models import Business

from business_filer.filing_processors.filing_components import business_profile


@pytest.mark.parametrize('test_name,response_json,response_status,put_status,expected_error', [
    ('no business profile',
     {'message': 'The requested business could not be found.'},
     404,
     None,
     {'error': 'No business profile found.'}),
    ('post success', {}, 200, None, None),
    ('update existing profile', {
        'code': 'DATA_ALREADY_EXISTS',
        'message': 'The data you want to insert already exists.'
    }, 400, 200, None),
    ('failed to update existing profile', {
        'code': 'DATA_ALREADY_EXISTS',
        'message': 'The data you want to insert already exists.'
    }, 400, 400, {'error': 'Unable to update existing business profile.'})
])
def test_update_business_profile(app, session, requests_mock,
                                 test_name, response_json, response_status, put_status, expected_error):
    """Assert that the business profile is updated.

    WHITE BOX test, as I'm mocking out 2 end points to
    work the business logic.
    """
    from flask import current_app

    email_address = 'no.one@never.get.there.com'
    phone_number = '555-555-5555'
    new_data = {
        'contactPoint': {
            'email': email_address,
            'phone': phone_number
        }
    }
    business = Business(identifier='BC1234567', legal_type='BEN')

    with app.app_context():
        # setup
        requests_mock.post(f'{current_app.config["ACCOUNT_SVC_AUTH_URL"]}',
                           json={'access_token': 'token'})
        requests_mock.post(f'{current_app.config["ACCOUNT_SVC_ENTITY_URL"]}/{business.identifier}/contacts',
                           json=response_json,
                           status_code=response_status)
        requests_mock.put(f'{current_app.config["ACCOUNT_SVC_ENTITY_URL"]}/{business.identifier}/contacts',
                          status_code=put_status)

        # test
        err = business_profile._update_business_profile(business, new_data['contactPoint'])

        assert err == expected_error
