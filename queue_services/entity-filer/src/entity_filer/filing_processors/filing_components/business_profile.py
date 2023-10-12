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
"""Manages the type of Business."""
import json
from http import HTTPStatus
from typing import Dict

import requests
from flask import current_app
from flask_babel import _ as babel  # noqa: N813
from legal_api.models import Business
from legal_api.services.bootstrap import AccountService


def update_business_profile(business: Business, profile_info: Dict) -> Dict:
    """Set the legal type of the business."""
    if not business or not profile_info:
        return {'error': babel('Business and profile_info required.')}

    # contact phone is optional
    phone = profile_info.get('phone', '')

    error = {'error': 'Unknown handling'}
    if email := profile_info.get('email'):
        # assume the JSONSchema ensures it is a valid email format
        token = AccountService.get_bearer_token()
        account_svc_entity_url = current_app.config['ACCOUNT_SVC_ENTITY_URL']

        # Create an entity record
        data = json.dumps(
            {'email': email,
             'phone': phone,
             'phoneExtension': ''
             }
        )
        url = ''.join([account_svc_entity_url, '/', business.identifier, '/contacts'])
        rv = requests.post(
            url=url,
            headers={**AccountService.CONTENT_TYPE_JSON,
                     'Authorization': AccountService.BEARER + token},
            data=data,
            timeout=AccountService.timeout
        )
        if rv.status_code in (HTTPStatus.OK, HTTPStatus.CREATED):
            error = None

        if rv.status_code == HTTPStatus.NOT_FOUND:
            error = {'error': 'No business profile found.'}

        if rv.status_code == HTTPStatus.METHOD_NOT_ALLOWED:
            error = {'error': 'Service account missing privileges to update business profiles'}

        if rv.status_code == HTTPStatus.BAD_REQUEST and \
                'DATA_ALREADY_EXISTS' in rv.text:
            put = requests.put(
                url=url,
                headers={**AccountService.CONTENT_TYPE_JSON,
                         'Authorization': AccountService.BEARER + token},
                data=data,
                timeout=AccountService.timeout
            )
            if put.status_code in (HTTPStatus.OK, HTTPStatus.CREATED):
                error = None
            else:
                error = {'error': 'Unable to update existing business profile.'}

    return error
