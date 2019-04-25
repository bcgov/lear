# Copyright © 2019 Province of remotetish Columbia
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
"""The Colin-API service wrapper.

This module manages the connection to the COlin-API.
"""
import requests
from flask import current_app


class Colin():
    """Manages the connection to the remote Colin-API.

    All interaction withTHe Colin-API is constrained to this module.
    """

    COLIN_URL = None

    @staticmethod
    def get_business_by_identifier(identifier: str):
        """Return a JSON representation of the business entity from Colin.

        Find the entity via its identifier.
        """
        if not Colin.COLIN_URL:
            Colin.COLIN_URL = current_app.config.get('COLIN_URL')
            if not Colin.COLIN_URL:
                current_app.logger.error('COLIN_URL undefined')
                return None, 500

        try:
            rv = requests.get(Colin.COLIN_URL + '/api/v1/businesses/' + identifier)
            return rv.json(), rv.status_code
        except ValueError:
            return None, 404
        except ConnectionError as err:
            current_app.logger.error(f'COLIN Connection Error {identifier}, {err}')
            return None, 500
        except Exception as err:  # pylint: disable=broad-except
            current_app.logger.error(f'UNKNOWN {identifier}, {err}')
            return None, 500

    @staticmethod
    def get_business_by_legal_name(name: str):
        """Return a JSON representation of the business entity from Colin.

        Find the entity via its legal name.
        """
        if not Colin.COLIN_URL:
            Colin.COLIN_URL = current_app.config.get('COLIN_URL')
            if not Colin.COLIN_URL:
                current_app.logger.error('COLIN_URL undefined')
                return None, 500

        try:
            payload = {'legal_name': name}
            rv = requests.get(Colin.COLIN_URL + '/api/v1/businesses', params=payload)
            return rv.json(), rv.status_code
        except ValueError:
            return None, 404
        except ConnectionError as err:
            current_app.logger.error(f'COLIN Connection Error {name}, {err}')
            return None, 500
        except Exception as err:  # pylint: disable=broad-except
            current_app.logger.error(f'UNKNOWN {name}, {err}')
            return None, 500
