# Copyright © 2025 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
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

    current_app.config["ACCOUNT_SVC_AUTH_URL"] = "http://example.com/auth"
    current_app.config["ACCOUNT_SVC_ENTITY_URL"] = "http://example.com/entity"

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
