# Copyright © 2022 Province of British Columbia
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
    def find_by_corp_num(corp_num: str):
        """Return corp's information."""
        try:
            colin_url = current_app.config.get('COLIN_URL')
            token = AccountService.get_bearer_token()
            response = requests.get(colin_url + '/api/v1/businesses/' + corp_num, headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            })
            response.raise_for_status()
            return response.json()
        except Exception as err:
            current_app.logger.error(err)
            return None
