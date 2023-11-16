# Copyright © 2023 Province of British Columbia
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
"""This module holds function decorators."""

import json
from datetime import datetime
from functools import wraps

import jwt
import requests
from flask import current_app
from jwt import ExpiredSignatureError


def requires_traction_auth(f):
    """Check for a valid Traction token and refresh if needed."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not (traction_api_url := current_app.config['TRACTION_API_URL']):
            raise EnvironmentError('TRACTION_API_URL environment variable is not set')

        if not (traction_tenant_id := current_app.config['TRACTION_TENANT_ID']):
            raise EnvironmentError('TRACTION_TENANT_ID environment variable is not set')

        if not (traction_api_key := current_app.config['TRACTION_API_KEY']):
            raise EnvironmentError('TRACTION_API_KEY environment variable is not set')

        try:
            if not hasattr(current_app, 'api_token'):
                raise jwt.ExpiredSignatureError

            if not (decoded := jwt.decode(current_app.api_token, options={'verify_signature': False})):
                raise jwt.ExpiredSignatureError

            if datetime.utcfromtimestamp(decoded['exp']) <= datetime.utcnow():
                raise jwt.ExpiredSignatureError
        except ExpiredSignatureError:
            current_app.logger.info('JWT token expired or is missing, requesting new token')
            response = requests.post(f'{traction_api_url}/multitenancy/tenant/{traction_tenant_id}/token',
                                     headers={'Content-Type': 'application/json'},
                                     data=json.dumps({'api_key': traction_api_key}))
            response.raise_for_status()
            current_app.api_token = response.json()['token']

        return f(*args, **kwargs)
    return decorated_function
