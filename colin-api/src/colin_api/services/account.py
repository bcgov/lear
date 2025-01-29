# Copyright © 2025 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This class provides the service for auth calls."""

import requests
from flask import current_app


# pylint: disable=too-few-public-methods
class AccountService:
    """Provides service to call Authentication Services."""

    BEARER: str = 'Bearer '
    CONTENT_TYPE_JSON = {'Content-Type': 'application/json'}

    try:
        timeout = int(current_app.config.get('ACCOUNT_SVC_TIMEOUT', 20))
    except Exception:  # pylint: disable=broad-except
        timeout = 20

    @classmethod
    def get_bearer_token(cls):
        """Get a valid Bearer token for the service to use."""
        token_url = current_app.config.get('ACCOUNT_SVC_AUTH_URL')
        client_id = current_app.config.get('ACCOUNT_SVC_CLIENT_ID')
        client_secret = current_app.config.get('ACCOUNT_SVC_CLIENT_SECRET')

        data = 'grant_type=client_credentials'

        # get service account token
        res = requests.post(url=token_url,
                            data=data,
                            headers={'content-type': 'application/x-www-form-urlencoded'},
                            auth=(client_id, client_secret),
                            timeout=cls.timeout)

        try:
            return res.json().get('access_token')
        except Exception:  # pylint: disable=broad-except
            return None
