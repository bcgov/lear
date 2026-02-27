# Copyright © 2020 Province of British Columbia
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

"""This provides the service for namex-api calls."""

import requests
from business_account.AccountService import AccountService
from flask import current_app


class NameXService:
    """Provides services to use the namex-api."""

    @staticmethod
    def query_nr_number(identifier: str):
        """Return a JSON object with name request information."""
        namex_url = current_app.config.get("NAMEX_SVC_URL")

        token = AccountService.get_bearer_token()

        # Perform proxy call using the inputted identifier (e.g. NR 1234567)
        nr_response = requests.get(namex_url + "requests/" + identifier, headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token
        })

        return nr_response
