# Copyright © 2024 Province of British Columbia
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

"""This provides the service for colin-api calls."""
import requests
from flask import current_app

from legal_api.services.bootstrap import AccountService


class ColinService():
    """Provides services to use the colin-api."""

    @staticmethod
    def query_business(identifier: str):
        """Return a JSON object with business information."""
        # Perform proxy call with identifier
        url = f'{current_app.config["COLIN_URL"]}/businesses/{identifier}/public'
        token = AccountService.get_bearer_token()
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
        }
        response = requests.get(url, headers=headers)

        return response
