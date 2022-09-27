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

"""This is a service to bootstrap the Incorporation Application process."""
import contextlib
import json
import secrets
import string
from http import HTTPStatus
from typing import Dict, Union

import requests
from flask import current_app
from flask_babel import _ as babel  # noqa: N813, I001, I003 casting _ to babel
from sqlalchemy.orm.exc import FlushError  # noqa: I001

from legal_api.models import RegistrationBootstrap  # noqa: D204, I003, I001;# due to babel cast above


class RegistrationBootstrapService:
    """Provides services to bootstrap the IA registration and account affiliation."""

    @staticmethod
    def create_bootstrap(account: int) -> Union[Dict, RegistrationBootstrap]:
        """Return either a new bootstrap registration or an error struct."""
        if not account:
            return {'error': babel('An account number must be provided.')}

        bootstrap = RegistrationBootstrap(account=account)
        allowed_encoded = string.ascii_letters + string.digits

        # try to create a bootstrap registration with a unique ID
        for _ in range(5):
            bootstrap.identifier = 'T' + ''.join(secrets.choice(allowed_encoded) for _ in range(9))
            try:
                bootstrap.save()
                return bootstrap
            except FlushError:
                pass  # we try again
            except Exception:
                break

        return {'error': babel('Unable to create bootstrap registration.')}

    @staticmethod
    def delete_bootstrap(bootstrap: RegistrationBootstrap):
        """Delete the bootstrap registration."""
        with contextlib.suppress(Exception):
            bootstrap.delete()
        return HTTPStatus.OK

    @staticmethod
    def register_bootstrap(bootstrap: RegistrationBootstrap,
                           business_name: str,
                           corp_type_code: str = 'TMP') -> Union[HTTPStatus, Dict]:
        """Return either a new bootstrap registration or an error struct."""
        if not bootstrap:
            return {'error': babel('An account number must be provided.')}

        rv = AccountService.create_affiliation(account=bootstrap.account,
                                               business_registration=bootstrap.identifier,
                                               business_name=business_name,
                                               corp_type_code=corp_type_code)

        if rv == HTTPStatus.OK:
            return HTTPStatus.OK

        with contextlib.suppress(Exception):
            AccountService.delete_affiliation(account=bootstrap.account,
                                              business_registration=bootstrap.identifier)
        return {'error': babel('Unable to create bootstrap registration.')}

    @staticmethod
    def deregister_bootstrap(bootstrap: RegistrationBootstrap) -> HTTPStatus:
        """Remove the bootstrap registration."""
        affiliation_status = AccountService.delete_affiliation(account=bootstrap.account,
                                                               business_registration=bootstrap.identifier)
        return affiliation_status


class AccountService:
    """Wrapper to call Authentication Services.

    @TODO Cache and refresh / retry token as needed to reduce calls.
    """

    BEARER: str = 'Bearer '
    CONTENT_TYPE_JSON = {'Content-Type': 'application/json'}

    try:
        timeout = int(current_app.config.get('ACCOUNT_SVC_TIMEOUT', 20))
    except Exception:
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
        except Exception:
            return None

    @classmethod
    # pylint: disable=too-many-arguments;
    def create_affiliation(cls, account: int,
                           business_registration: str,
                           business_name: str = None,
                           corp_type_code: str = 'TMP',
                           pass_code: str = ''):
        """Affiliate a business to an account."""
        auth_url = current_app.config.get('AUTH_SVC_URL')
        account_svc_entity_url = f'{auth_url}/entities'
        account_svc_affiliate_url = f'{auth_url}/orgs/{account}/affiliations'

        token = cls.get_bearer_token()

        if not token:
            return HTTPStatus.UNAUTHORIZED

        # Create an entity record
        entity_data = json.dumps({'businessIdentifier': business_registration,
                                  'corpTypeCode': corp_type_code,
                                  'name': business_name or business_registration
                                  })
        entity_record = requests.post(
            url=account_svc_entity_url,
            headers={**cls.CONTENT_TYPE_JSON,
                     'Authorization': cls.BEARER + token},
            data=entity_data,
            timeout=cls.timeout
        )

        # Create an account:business affiliation
        affiliate_data = json.dumps({
            'businessIdentifier': business_registration,
            'passCode': pass_code
        })
        affiliate = requests.post(
            url=account_svc_affiliate_url,
            headers={**cls.CONTENT_TYPE_JSON,
                     'Authorization': cls.BEARER + token},
            data=affiliate_data,
            timeout=cls.timeout
        )

        # @TODO delete affiliation and entity record next sprint when affiliation service is updated
        if affiliate.status_code != HTTPStatus.CREATED or entity_record.status_code != HTTPStatus.CREATED:
            return HTTPStatus.BAD_REQUEST
        return HTTPStatus.OK

    @classmethod
    def update_entity(cls,
                      business_registration: str,
                      business_name: str,
                      corp_type_code: str,
                      state: str = None):
        """Update an entity."""
        auth_url = current_app.config.get('AUTH_SVC_URL')
        account_svc_entity_url = f'{auth_url}/entities'

        token = cls.get_bearer_token()

        if not token:
            return HTTPStatus.UNAUTHORIZED

        # Create an entity record
        entity_data = {
            'businessIdentifier': business_registration,
            'corpTypeCode': corp_type_code,
            'name': business_name
        }
        if state:
            entity_data['state'] = state

        entity_record = requests.patch(
            url=account_svc_entity_url + '/' + business_registration,
            headers={**cls.CONTENT_TYPE_JSON,
                     'Authorization': cls.BEARER + token},
            data=json.dumps(entity_data),
            timeout=cls.timeout
        )

        if entity_record.status_code != HTTPStatus.OK:
            return HTTPStatus.BAD_REQUEST
        return HTTPStatus.OK

    @classmethod
    def delete_affiliation(cls, account: int, business_registration: str) -> Dict:
        """Affiliate a business to an account.

        @TODO Update this when account affiliation is changed next sprint.
        """
        auth_url = current_app.config.get('AUTH_SVC_URL')
        account_svc_entity_url = f'{auth_url}/entities'
        account_svc_affiliate_url = f'{auth_url}/orgs/{account}/affiliations'

        token = cls.get_bearer_token()

        # Delete an account:business affiliation
        affiliate = requests.delete(
            url=account_svc_affiliate_url + '/' + business_registration,
            headers={**cls.CONTENT_TYPE_JSON,
                     'Authorization': cls.BEARER + token},
            timeout=cls.timeout
        )
        # Delete an entity record
        entity_record = requests.delete(
            url=account_svc_entity_url + '/' + business_registration,
            headers={**cls.CONTENT_TYPE_JSON,
                     'Authorization': cls.BEARER + token},
            timeout=cls.timeout
        )

        if affiliate.status_code != HTTPStatus.OK \
                or entity_record.status_code not in (HTTPStatus.OK, HTTPStatus.NO_CONTENT):
            return HTTPStatus.BAD_REQUEST
        return HTTPStatus.OK

    @classmethod
    def get_account_by_affiliated_identifier(cls, identifier: str):
        """Return the account affiliated to the business."""
        token = cls.get_bearer_token()
        auth_url = current_app.config.get('AUTH_SVC_URL')
        url = f'{auth_url}/orgs?affiliation={identifier}'

        res = requests.get(url,
                           headers={**cls.CONTENT_TYPE_JSON,
                                    'Authorization': cls.BEARER + token})
        try:
            return res.json()
        except Exception:  # noqa B902; pylint: disable=W0703;
            current_app.logger.error('Failed to get response')
            return None
