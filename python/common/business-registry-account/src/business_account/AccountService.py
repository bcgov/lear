from flask import current_app
from http import HTTPStatus
import json
import requests
from typing import Dict

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
    # pylint: disable=too-many-arguments, too-many-locals disable=invalid-name, disable=redefined-outer-name;
    def create_affiliation(cls, account: int,
                           business_registration: str,
                           business_name: str = None,
                           corp_type_code: str = 'TMP',
                           corp_sub_type_code: str = None,
                           pass_code: str = '',
                           details: dict = None,
                           flags: any = None):
        """Affiliate a business to an account."""
        current_app.logger.info(f'Creating affiliation of {business_registration} for {account}')
        auth_url = current_app.config.get('AUTH_SVC_URL')
        account_svc_entity_url = f'{auth_url}/entities'
        account_svc_affiliate_url = f'{auth_url}/orgs/{account}/affiliations'

        token = cls.get_bearer_token()

        if not token:
            current_app.logger.info('Missing token for affiliation call')
            return HTTPStatus.UNAUTHORIZED

        # Create an entity record
        entity_data = {
            'businessIdentifier': business_registration,
            'corpTypeCode': corp_type_code,
            'name': business_name or business_registration
        }
        if corp_sub_type_code:
            entity_data['corpSubTypeCode'] = corp_sub_type_code

        entity_record = requests.post(
            url=account_svc_entity_url,
            headers={**cls.CONTENT_TYPE_JSON,
                     'Authorization': cls.BEARER + token},
            data=json.dumps(entity_data),
            timeout=cls.timeout
        )

        # Create an account:business affiliation
        # headers with conditional sandbox override
        headers = {**cls.CONTENT_TYPE_JSON, 'Authorization': cls.BEARER + token}
        if flags and isinstance(flags, Flags) and flags.is_on('enable-sandbox'):
            current_app.logger.info('Appending Environment-Override = sandbox header to create affiliation call')
            headers['Environment-Override'] = 'sandbox'

        affiliate_data = {
            'businessIdentifier': business_registration,
            'passCode': pass_code
        }
        if details:
            affiliate_data['entityDetails'] = details
        affiliate = requests.post(
            url=account_svc_affiliate_url,
            headers=headers,
            data=json.dumps(affiliate_data),
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

    @classmethod
    def get_affiliations(cls, account: int):
        """Affiliate a business to an account."""
        auth_url = current_app.config.get('AUTH_SVC_URL')
        account_svc_affiliate_url = f'{auth_url}/orgs/{account}/affiliations'

        token = cls.get_bearer_token()

        if not token:
            current_app.logger.error('Not Authorized')
            return None

        affiliates = requests.get(
            url=account_svc_affiliate_url,
            headers={**cls.CONTENT_TYPE_JSON,
                     'Authorization': cls.BEARER + token},
            timeout=cls.timeout
        )

        if affiliates.status_code == HTTPStatus.OK:
            return affiliates.json().get('entities')

        return None
