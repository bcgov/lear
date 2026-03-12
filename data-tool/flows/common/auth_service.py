import json
from http import HTTPStatus
from typing import Optional

import requests


class AuthService:
    """Wrapper to call Authentication Services."""

    BEARER: str = 'Bearer '
    CONTENT_TYPE_JSON = {'Content-Type': 'application/json'}

    @classmethod
    def get_time_out(cls, config) -> int:
        """Return request timeout (seconds)."""
        return getattr(config, 'ACCOUNT_SVC_TIMEOUT', None) or 20

    @classmethod
    def get_bearer_token(cls, config) -> Optional[str]:
        """Get a valid Bearer token for the service to use."""
        token_url = config.ACCOUNT_SVC_AUTH_URL
        client_id = config.ACCOUNT_SVC_CLIENT_ID
        client_secret = config.ACCOUNT_SVC_CLIENT_SECRET

        data = 'grant_type=client_credentials'

        # get service account token
        res = requests.post(
            url=token_url,
            data=data,
            headers={'content-type': 'application/x-www-form-urlencoded'},
            auth=(client_id, client_secret),
            timeout=cls.get_time_out(config)
        )

        try:
            return res.json().get('access_token')
        except Exception:
            return None

    @classmethod
    def _resolve_token(cls, config, token: str | None) -> Optional[str]:
        """Use provided token, or fetch a new one."""
        return token or cls.get_bearer_token(config)

    # pylint: disable=too-many-arguments, too-many-locals disable=invalid-name;
    @classmethod
    def create_affiliation(
        cls,
        config,
        account: int,
        business_registration: str,
        business_name: str = None,
        corp_type_code: str = 'TMP',
        corp_sub_type_code: str = None,
        pass_code: str = '',
        details: dict = None,
        *,
        token: str | None = None
    ) -> HTTPStatus:
        """Affiliate a business to an account."""
        auth_url = config.AUTH_SVC_URL
        account_svc_entity_url = f'{auth_url}/entities'
        account_svc_affiliate_url = f'{auth_url}/orgs/{account}/affiliations'

        token = cls._resolve_token(config, token)
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

        # Be tolerant of idempotent responses (existing entity/affiliation).
        entity_ok = entity_record.status_code in (
            HTTPStatus.ACCEPTED,
            HTTPStatus.CREATED,
            HTTPStatus.OK,
            HTTPStatus.CONFLICT
        )
        if entity_record.status_code == HTTPStatus.BAD_REQUEST and 'DATA_ALREADY_EXISTS' in entity_record.text:
            entity_ok = True

        affiliate_ok = affiliate.status_code in (
            HTTPStatus.CREATED,
            HTTPStatus.OK,
            HTTPStatus.CONFLICT
        )
        if affiliate.status_code == HTTPStatus.BAD_REQUEST and 'DATA_ALREADY_EXISTS' in affiliate.text:
            affiliate_ok = True

        if not (entity_ok and affiliate_ok):
            return HTTPStatus.BAD_REQUEST

        return HTTPStatus.OK

    @classmethod
    def create_entity(
        cls,
        config,
        business_registration: str,
        business_name: str,
        corp_type_code: str,
        pass_code: str = '',
        *,
        token: str | None = None
    ) -> HTTPStatus:
        """Create an entity."""
        auth_url = config.AUTH_SVC_URL
        account_svc_entity_url = f'{auth_url}/entities'

        token = cls._resolve_token(config, token)
        if not token:
            return HTTPStatus.UNAUTHORIZED

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

        if entity_record.status_code in (HTTPStatus.ACCEPTED, HTTPStatus.CREATED, HTTPStatus.OK, HTTPStatus.CONFLICT):
            return HTTPStatus.OK
        if entity_record.status_code == HTTPStatus.BAD_REQUEST and 'DATA_ALREADY_EXISTS' in entity_record.text:
            return HTTPStatus.OK
        return HTTPStatus.BAD_REQUEST

    @classmethod
    def update_entity(
        cls,
        config,
        business_registration: str,
        business_name: str,
        corp_type_code: str,
        state: str = None,
        *,
        token: str | None = None
    ) -> HTTPStatus:
        """Update an entity."""
        auth_url = config.AUTH_SVC_URL
        account_svc_entity_url = f'{auth_url}/entities'

        token = cls._resolve_token(config, token)
        if not token:
            return HTTPStatus.UNAUTHORIZED

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
    def delete_affiliation(cls, config, account: int, business_registration: str, *, token: str | None = None) -> HTTPStatus:
        """Legacy combined delete: deletes BOTH affiliation and entity (avoid in delete flows)."""
        auth_url = config.AUTH_SVC_URL
        account_svc_entity_url = f'{auth_url}/entities'
        account_svc_affiliate_url = f'{auth_url}/orgs/{account}/affiliations'

        token = cls._resolve_token(config, token)
        if not token:
            return HTTPStatus.UNAUTHORIZED

        affiliate = requests.delete(
            url=account_svc_affiliate_url + '/' + business_registration,
            headers={**cls.CONTENT_TYPE_JSON,
                     'Authorization': cls.BEARER + token},
            timeout=cls.get_time_out(config)
        )
        entity_record = requests.delete(
            url=account_svc_entity_url + '/' + business_registration,
            headers={**cls.CONTENT_TYPE_JSON,
                     'Authorization': cls.BEARER + token},
            timeout=cls.get_time_out(config)
        )

        affiliate_ok = affiliate.status_code in (HTTPStatus.OK, HTTPStatus.NO_CONTENT, HTTPStatus.NOT_FOUND)
        entity_ok = entity_record.status_code in (HTTPStatus.OK, HTTPStatus.NO_CONTENT, HTTPStatus.NOT_FOUND)

        if not (affiliate_ok and entity_ok):
            return HTTPStatus.BAD_REQUEST
        return HTTPStatus.OK

    @classmethod
    def delete_entity(cls, config, identifier: str, *, token: str | None = None) -> HTTPStatus:
        """Delete an entity ONLY."""
        auth_url = config.AUTH_SVC_URL
        account_svc_entity_url = f'{auth_url}/entities'

        token = cls._resolve_token(config, token)
        if not token:
            return HTTPStatus.UNAUTHORIZED

        rv = requests.delete(
            url=f'{account_svc_entity_url}/{identifier}',
            headers={**cls.CONTENT_TYPE_JSON,
                     'Authorization': cls.BEARER + token},
            timeout=cls.get_time_out(config)
        )
        try:
            return HTTPStatus(rv.status_code)
        except Exception:
            return HTTPStatus.BAD_REQUEST

    @classmethod
    def delete_affiliation_only(cls, config, account: int, identifier: str, *, token: str | None = None) -> HTTPStatus:
        """Delete an affiliation ONLY (does not delete the entity)."""
        auth_url = config.AUTH_SVC_URL
        account_svc_affiliate_url = f'{auth_url}/orgs/{account}/affiliations'

        token = cls._resolve_token(config, token)
        if not token:
            return HTTPStatus.UNAUTHORIZED

        rv = requests.delete(
            url=f'{account_svc_affiliate_url}/{identifier}',
            headers={**cls.CONTENT_TYPE_JSON,
                     'Authorization': cls.BEARER + token},
            timeout=cls.get_time_out(config)
        )
        try:
            return HTTPStatus(rv.status_code)
        except Exception:
            return HTTPStatus.BAD_REQUEST

    @classmethod
    def update_contact_email(cls, config, identifier: str, email: str, *, token: str | None = None) -> HTTPStatus:
        """Update contact email of the business."""
        token = cls._resolve_token(config, token)
        if not token:
            return HTTPStatus.UNAUTHORIZED

        auth_url = config.AUTH_SVC_URL
        account_svc_entity_url = f'{auth_url}/entities'

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

        if rv.status_code in (HTTPStatus.OK, HTTPStatus.CREATED, HTTPStatus.ACCEPTED):
            return HTTPStatus.OK

        try:
            return HTTPStatus(rv.status_code)
        except Exception:
            return HTTPStatus.BAD_REQUEST

    @classmethod
    def send_unaffiliated_email(cls, config, identifier: str, email: str, *, token: str | None = None) -> HTTPStatus:
        """Send unaffiliated email/invite to the business (if supported by API)."""
        token = cls._resolve_token(config, token)
        if not token:
            return HTTPStatus.UNAUTHORIZED

        auth_url = config.AUTH_SVC_URL
        account_svc_affiliation_invitation_url = f'{auth_url}/affiliationInvitations'
        print(f'👷 Sending unaffiliated email to {email} for {identifier}...')

        data = {}
        rv = requests.post(
            url=f'{account_svc_affiliation_invitation_url}/unaffiliated/{identifier}',
            headers={
                **cls.CONTENT_TYPE_JSON,
                'Authorization': cls.BEARER + token
            },
            data=json.dumps(data),
            timeout=cls.get_time_out(config)
        )

        if rv.status_code in (HTTPStatus.OK, HTTPStatus.CREATED):
            return HTTPStatus.OK

        try:
            return HTTPStatus(rv.status_code)
        except Exception:
            return HTTPStatus.BAD_REQUEST
