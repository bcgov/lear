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

"""This class provides the service for legal-api calls."""
import requests
from flask import current_app

from colin_api.services.account import AccountService


# pylint: disable=too-few-public-methods
class LegalApiService():
    """Provides service to call the legal-api."""

    @staticmethod
    def query_business(identifier: str):
        """Return a JSON object with business information."""
        timeout = int(current_app.config.get('ACCOUNT_SVC_TIMEOUT'))
        legal_api_url = current_app.config.get('LEGAL_API_URL')
        token = AccountService.get_bearer_token()

        try:
            # Perform proxy call using the input identifier (e.g. BC 123456)
            response = requests.get(legal_api_url + '/businesses/' + identifier,
                                    headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                                    timeout=timeout
                                    )
            # If the status code is 200 or 404, return the response
            if response.status_code in (200, 404):
                return response
            response.raise_for_status()

        except Exception as err:  # pylint: disable=broad-except:
            current_app.logger.error(err, exc_info=True)
            raise  # re-throw the exception after logging
