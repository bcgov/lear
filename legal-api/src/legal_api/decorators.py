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
import time
from datetime import datetime
from functools import wraps
from http import HTTPStatus

import jwt as pyjwt
import requests
from flask import current_app, jsonify
from jwt import ExpiredSignatureError

from legal_api.models import Business
from legal_api.services.authz import are_digital_credentials_allowed
from legal_api.utils.auth import jwt


MAX_RETRIES = 5  # Number of times to retry getting the token
TOKEN_RETRY_WAIT = 2  # Delay in seconds between retries


def _get_traction_token():
    """Get a traction token and check if it is valid."""
    if not (traction_api_url := current_app.config.get('TRACTION_API_URL')):
        raise EnvironmentError('TRACTION_API_URL environment variable is not set')

    if not (traction_tenant_id := current_app.config.get('TRACTION_TENANT_ID')):
        raise EnvironmentError('TRACTION_TENANT_ID environment variable is not set')

    if not (traction_api_key := current_app.config.get('TRACTION_API_KEY')):
        raise EnvironmentError('TRACTION_API_KEY environment variable is not set')

    for attempt in range(MAX_RETRIES):
        try:
            # Fetch a Traction token for the tenant using the Tenant API key
            token_response = requests.post(
                f'{traction_api_url}/multitenancy/tenant/{traction_tenant_id}/token',
                headers={'Content-Type': 'application/json'},
                data=json.dumps({'api_key': traction_api_key})
            )
            token_response.raise_for_status()

            # Decode the token to check its validity
            token = token_response.json().get('token', None)
            pyjwt.decode(token, options={'verify_signature': False})

            # Use the token to check if it is valid by calling the tenant endpoint
            check_response = requests.get(
                f'{traction_api_url}/tenant',
                headers={
                    'Authorization': f'Bearer {token}'
                }
            )

            if check_response.status_code == 401:
                current_app.logger.warning(f'Attempt {attempt + 1}: Received 401 checking token. Retry.')
                time.sleep(TOKEN_RETRY_WAIT)
                continue

            check_response.raise_for_status()
            current_app.logger.debug(f'New Traction token obtained: {token}')
            return token

        except pyjwt.InvalidTokenError as err:
            current_app.logger.warning(f'Attempt {attempt + 1}: Invalid Traction token: {err}')
        except requests.RequestException as err:
            # If a non-401 request fails, log the error and move on out of the loop
            # (IE Traction API is down or unreachable, or config is wrong)
            current_app.logger.error(f'Attempt {attempt + 1}: Failed to get Traction token: {err}')
            break

    raise EnvironmentError('Failed to get Traction token')


def requires_traction_auth(f):
    """Check for a valid Traction token and refresh or get first-time if needed."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            if not hasattr(current_app, 'api_token'):
                raise pyjwt.ExpiredSignatureError

            if not (decoded := pyjwt.decode(current_app.api_token, options={'verify_signature': False})):
                raise pyjwt.ExpiredSignatureError

            if datetime.utcfromtimestamp(decoded['exp']) <= datetime.utcnow():
                raise pyjwt.ExpiredSignatureError
        except ExpiredSignatureError:
            current_app.logger.info('Traction token expired or is missing, requesting new token')
            current_app.api_token = _get_traction_token()

        return f(*args, **kwargs)
    return decorated_function


def can_access_digital_credentials(f):
    """Ensure the business can has access to digital credentials."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        identifier = kwargs.get('identifier', None)

        if not (business := Business.find_by_identifier(identifier)):
            return jsonify({'message': f'{identifier} not found.'}), HTTPStatus.NOT_FOUND

        if not are_digital_credentials_allowed(business, jwt):
            return jsonify({'message': f'digital credential not available for: {identifier}.'}), HTTPStatus.UNAUTHORIZED

        return f(*args, **kwargs)
    return decorated_function
