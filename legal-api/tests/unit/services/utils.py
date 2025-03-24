# Copyright © 2019 Province of British Columbia
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
"""Utility functions for tests."""

from flask_jwt_oidc import JwtManager
import random
from datetime import datetime, timezone
from typing import List, Union
from legal_api.models.address import Address
from legal_api.models.business import Business
from legal_api.models.party_role import PartyRole
from tests.unit.models import factory_business, factory_party_role


jwt_json_token_header = {
    'alg': 'RS256',
    'typ': 'JWT',
    'kid': 'flask-jwt-oidc-test-client'
}


def helper_create_jwt_json_token_claims(roles: List[str] = [], username: str = 'test-user'):
    """Create a jwt token claims"""
    return {
        'iss': 'https://example.localdomain/auth/realms/example',
        'sub': '43e6a245-0bf7-4ccf-9bd0-e7fb85fd18cc',
        'aud': 'example',
        'exp': 2539722391,
        'iat': 1539718791,
        'jti': 'flask-jwt-oidc-test-support',
        'typ': 'Bearer',
        'username': f'{username}',
        'idp_userid': '123',
        'loginSource': 'IDIR',
        'realm_access': {
            'roles': [] + roles
        }
    }


def helper_create_jwt(jwt_manager: JwtManager, roles: List[str] = [], username: str = 'test-user'):
    """Create a jwt bearer token with the correct keys, roles and username."""
    token_header = jwt_json_token_header
    token_claims = helper_create_jwt_json_token_claims(roles=roles, username=username)
    return jwt_manager.create_jwt(token_claims, token_header)


def create_header(jwt_manager, roles: List[str] = [], username: str = 'test-user', **kwargs):
    """Return a header containing a JWT bearer token."""
    token = helper_create_jwt(jwt_manager, roles=roles, username=username)
    headers = {**kwargs, **{'Authorization': 'Bearer ' + token}}
    return headers


def create_test_user(first_name: Union[str, None] = None, last_name: Union[str, None] = None,
                     middle_initial: Union[str, None] = None, suffix: Union[str, None] = '',
                     default_first: bool = True, default_last: bool = True, default_middle: bool = True):
    first = first_name or ('TEST' if default_first else None)
    last = last_name or ('USER' if default_last else None)
    middle = middle_initial or ('TU' if default_middle else None)

    return {
        'first_name': f'{first}{suffix}' if first else None,
        'last_name': f'{last}{suffix}' if last else None,
        'middle_initial': f'{middle}{suffix}' if middle else None,
    }


def create_business(legal_type: str, state: Business.State):
    """Create a business."""
    identifier = (f'BC{random.SystemRandom().getrandbits(0x58)}')[:9]
    business = factory_business(identifier=identifier,
                                entity_type=legal_type,
                                state=state,
                                founding_date=datetime.now(timezone.utc),)
    return business


def create_party_role(role=PartyRole.RoleTypes.COMPLETING_PARTY,
                      first_name: Union[str, None] = None,
                      last_name: Union[str, None] = None,
                      middle_initial: Union[str, None] = None):
    completing_party_address = Address(
        city='Test Mailing City', address_type=Address.DELIVERY)
    officer = {
        'firstName': first_name,
        'middleInitial': middle_initial,
        'lastName': last_name,
        'partyType': 'person',
        'organizationName': ''
    }
    party_role = factory_party_role(
        completing_party_address,
        None,
        officer,
        datetime.now(timezone.utc),
        None,
        role
    )
    return party_role
