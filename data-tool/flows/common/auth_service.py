import json
from http import HTTPStatus
from typing import Dict

import requests


class AuthService:
    """Wrapper to call Authentication Services.
    """

    BEARER: str = 'Bearer '
    CONTENT_TYPE_JSON = {'Content-Type': 'application/json'}

    @classmethod
    def get_time_out(cls, config):
        try:
            timeout = int(config.ACCOUNT_SVC_TIMEOUT, 20)
        except Exception:
            timeout = 20

    @classmethod
    def get_bearer_token(cls, config):
        """Get a valid Bearer token for the service to use."""
        token_url = config.ACCOUNT_SVC_AUTH_URL
        client_id = config.ACCOUNT_SVC_CLIENT_ID
        client_secret = config.ACCOUNT_SVC_CLIENT_SECRET

        data = 'grant_type=client_credentials'

        # get service account token
        res = requests.post(url=token_url,
                             data=data,
                             headers={'content-type': 'application/x-www-form-urlencoded'},
                             auth=(client_id, client_secret),
                             timeout=cls.get_time_out(config))

        try:
            return res.json().get('access_token')
        except Exception:
            return None


    # pylint: disable=too-many-arguments, too-many-locals disable=invalid-name;
    @classmethod
    def create_affiliation(cls,
                           config,
                           account: int,
                           business_registration: str,
                           business_name: str = None,
                           corp_type_code: str = 'TMP',
                           corp_sub_type_code: str = None,
                           pass_code: str = '',
                           details: dict = None):
        """Affiliate a business to an account."""
        auth_url = config.AUTH_SVC_URL
        account_svc_entity_url = f'{auth_url}/entities'
        account_svc_affiliate_url = f'{auth_url}/orgs/{account}/affiliations'

        token = cls.get_bearer_token(config)

        if not token:
            return HTTPStatus.UNAUTHORIZED

        # Create an entity record
        entity_data = {
            'businessIdentifier': business_registration,
            'corpTypeCode': corp_type_code,
            'name': business_name or business_registration
        }
        if corp_sub_type_code:
            entity_data['corpSubTypeCode'] = corp_sub_type_code

        if pass_code:
            entity_data['passCode'] = pass_code

        entity_record = requests.post(
            url=account_svc_entity_url,
            headers={**cls.CONTENT_TYPE_JSON,
                     'Authorization': cls.BEARER + token},
            data=json.dumps(entity_data),
            timeout=cls.get_time_out(config)
        )

        # Create an account:business affiliation
        affiliate_data = {
            'businessIdentifier': business_registration,
        }
        if pass_code:
            affiliate_data['passCode'] = pass_code
        if details:
            affiliate_data['entityDetails'] = details
        affiliate = requests.post(
            url=account_svc_affiliate_url,
            headers={**cls.CONTENT_TYPE_JSON,
                     'Authorization': cls.BEARER + token},
            data=json.dumps(affiliate_data),
            timeout=cls.get_time_out(config)
        )

        if (
            affiliate.status_code != HTTPStatus.CREATED
            or entity_record.status_code not in (HTTPStatus.ACCEPTED, HTTPStatus.CREATED)
        ):
            return HTTPStatus.BAD_REQUEST
        return HTTPStatus.OK

    @classmethod
    def create_entity(cls,
                      config,
                      business_registration: str,
                      business_name: str,
                      corp_type_code: str,
                      pass_code: str = ''):
        """Update an entity."""
        auth_url = config.AUTH_SVC_URL
        account_svc_entity_url = f'{auth_url}/entities'

        token = cls.get_bearer_token(config)

        if not token:
            return HTTPStatus.UNAUTHORIZED

        # Create an entity record
        entity_data = {
            'businessIdentifier': business_registration,
            'corpTypeCode': corp_type_code,
            'name': business_name
        }

        if pass_code:
            entity_data['passCode'] = pass_code

        entity_record = requests.post(
            url=account_svc_entity_url,
            headers={**cls.CONTENT_TYPE_JSON,
                     'Authorization': cls.BEARER + token},
            data=json.dumps(entity_data),
            timeout=cls.get_time_out(config)
        )

        if entity_record.status_code not in (HTTPStatus.ACCEPTED, HTTPStatus.CREATED):
            return HTTPStatus.BAD_REQUEST
        return HTTPStatus.OK


    @classmethod
    def update_entity(cls,
                      config,
                      business_registration: str,
                      business_name: str,
                      corp_type_code: str,
                      state: str = None):
        """Update an entity."""
        auth_url = config.AUTH_SVC_URL
        account_svc_entity_url = f'{auth_url}/entities'

        token = cls.get_bearer_token(config)

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
            timeout=cls.get_time_out(config)
        )

        if entity_record.status_code != HTTPStatus.OK:
            return HTTPStatus.BAD_REQUEST
        return HTTPStatus.OK

    @classmethod
    def delete_affiliation(cls, config, account: int, business_registration: str) -> Dict:
        """Affiliate a business to an account.

        """
        auth_url = config.AUTH_SVC_URL
        account_svc_entity_url = f'{auth_url}/entities'
        account_svc_affiliate_url = f'{auth_url}/orgs/{account}/affiliations'

        token = cls.get_bearer_token(config)

        # Delete an account:business affiliation
        affiliate = requests.delete(
            url=account_svc_affiliate_url + '/' + business_registration,
            headers={**cls.CONTENT_TYPE_JSON,
                     'Authorization': cls.BEARER + token},
            timeout=cls.get_time_out(config)
        )
        # Delete an entity record
        entity_record = requests.delete(
            url=account_svc_entity_url + '/' + business_registration,
            headers={**cls.CONTENT_TYPE_JSON,
                     'Authorization': cls.BEARER + token},
            timeout=cls.get_time_out(config)
        )

        if affiliate.status_code != HTTPStatus.OK \
                or entity_record.status_code not in (HTTPStatus.OK, HTTPStatus.NO_CONTENT):
            return HTTPStatus.BAD_REQUEST
        return HTTPStatus.OK

    @classmethod
    def update_contact_email(cls, config, identifier: str, email: str) -> Dict:
        """Update contact email of the business."""
        token = cls.get_bearer_token(config)
        auth_url = config.AUTH_SVC_URL
        account_svc_entity_url = f'{auth_url}/entities'

        # Create an entity record
        data = {
            'email': email,
            'phone': '',
            'phoneExtension': ''
        }

        rv = requests.post(
            url=f'{account_svc_entity_url}/{identifier}/contacts',
            headers={
                **cls.CONTENT_TYPE_JSON,
                'Authorization': cls.BEARER + token
            },
            data=json.dumps(data),
            timeout=cls.get_time_out(config)
        )

        if (rv.status_code == HTTPStatus.BAD_REQUEST and 'DATA_ALREADY_EXISTS' in rv.text):
            rv = requests.put(
                url=f'{account_svc_entity_url}/{identifier}/contacts',
                headers={
                    **cls.CONTENT_TYPE_JSON,
                    'Authorization': cls.BEARER + token
                },
                data=json.dumps(data),
                timeout=cls.get_time_out(config)
            )

        if rv.status_code in (HTTPStatus.OK, HTTPStatus.CREATED):
            return HTTPStatus.OK

        return rv.status_code
