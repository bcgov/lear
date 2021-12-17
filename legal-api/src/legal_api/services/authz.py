# Copyright © 2019 Province of British Columbia
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
"""This manages all of the authentication and authorization service."""
from http import HTTPStatus
from typing import Final, List

from flask import current_app
from flask_jwt_oidc import JwtManager
from requests import Session, exceptions
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from legal_api.models import Business


SYSTEM_ROLE = 'system'
STAFF_ROLE = 'staff'
BASIC_USER = 'basic'
COLIN_SVC_ROLE = 'colin'
PUBLIC_USER = 'public_user'


def authorized(  # pylint: disable=too-many-return-statements
        identifier: str, jwt: JwtManager, action: List[str]) -> bool:
    """Assert that the user is authorized to create filings against the business identifier."""
    # if they are registry staff, they are always authorized
    if not action or not identifier or not jwt:
        return False

    if jwt.validate_roles([STAFF_ROLE]) \
            or jwt.validate_roles([SYSTEM_ROLE]) \
            or jwt.validate_roles([COLIN_SVC_ROLE]):
        return True

    if jwt.has_one_of_roles([BASIC_USER, PUBLIC_USER]):

        # if the action is create_comment or courtOrder/registrarsNotation/registrarsOrder filings
        # disallow - only staff are allowed
        staff_only_actions = ['add_comment', 'court_order', 'registrars_notation', 'registrars_order']
        if any(elem in action for elem in staff_only_actions):
            return False

        template_url = current_app.config.get('AUTH_SVC_URL')
        auth_url = template_url.format(**vars())

        token = jwt.get_token_auth_header()
        headers = {'Authorization': 'Bearer ' + token}
        try:
            http = Session()
            retries = Retry(total=5,
                            backoff_factor=0.1,
                            status_forcelist=[500, 502, 503, 504])
            http.mount('http://', HTTPAdapter(max_retries=retries))
            rv = http.get(url=auth_url, headers=headers)

            if rv.status_code != HTTPStatus.OK \
                    or not rv.json().get('roles'):
                return False

            if all(elem.lower() in rv.json().get('roles') for elem in action):
                return True

        except (exceptions.ConnectionError,  # pylint: disable=broad-except
                exceptions.Timeout,
                ValueError,
                Exception) as err:
            current_app.logger.error(f'template_url {template_url}, svc:{auth_url}')
            current_app.logger.error(f'Authorization connection failure for {identifier}, using svc:{auth_url}', err)
            return False

    return False


def has_roles(jwt: JwtManager, roles: List[str]) -> bool:
    """Assert the users JWT has the required role(s).

    Assumes the JWT is already validated.
    """
    if jwt.validate_roles(roles):
        return True
    return False


ALLOWABLE_FILINGS_ACTIVE: Final = {
    'alteration': {
        'staff': ['BC', 'BEN'],
        'user': ['BC', 'BEN'],
    },
    'annualReport': {
        'staff': ['CP', 'BEN'],
        'user': ['CP', 'BEN'],
    },
    'changeOfAddress': {
        'staff': ['CP', 'BEN'],
        'user': ['CP', 'BEN'],
    },
    'changeOfDirectors': {
        'staff': ['CP', 'BEN'],
        'user': ['CP', 'BEN'],
    },
    'correction': {
        'staff': ['CP', 'BEN'],
    },
    'courtOrder': {
        'staff': ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'],
    },
    'dissolution': {
        'staff': ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'],
        'user': ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'],
    },
    'incorporationApplication': {
        'staff': ['CP', 'BC', 'BEN'],
        'user': ['CP', 'BC', 'BEN'],
    },
    'restoration': {
        'staff': ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'],
    },
    'specialResolution': {
        'staff': ['CP'],
        'user': ['CP'],
    },
    'transition': {
        'staff': ['BC', 'BEN'],
        'user': ['BC', 'BEN'],
    },
    'registrarsNotation': {
        'staff': ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'],
    },
    'registrarsOrder': {
        'staff': ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'],
    },
}

ALLOWABLE_FILINGS_HISTORICAL: Final = {
    'courtOrder': {
        'staff': ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'],
    },
    'registrarsNotation': {
        'staff': ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'],
    },
    'registrarsOrder': {
        'staff': ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'],
    },
    'restoration': {
        'staff': ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'],
    },
}


def is_allowed(state: Business.State, filing_type: str, legal_type: str, jwt: JwtManager):
    """Is allowed to do filing."""
    user_role = 'user'
    if jwt.contains_role([STAFF_ROLE, SYSTEM_ROLE, COLIN_SVC_ROLE]):
        user_role = 'staff'

    allowable_filings = ALLOWABLE_FILINGS_ACTIVE
    if state == Business.State.HISTORICAL:
        allowable_filings = ALLOWABLE_FILINGS_HISTORICAL

    allowable_legal_types = allowable_filings.get(filing_type, {}).get(user_role, [])
    if legal_type in allowable_legal_types:
        return True

    return False


def get_allowed(state: Business.State, legal_type: str, jwt: JwtManager):
    """Get allowed type of filing types for the current user."""
    user_role = 'user'
    if jwt.contains_role([STAFF_ROLE, SYSTEM_ROLE, COLIN_SVC_ROLE]):
        user_role = 'staff'

    allowable_filings = ALLOWABLE_FILINGS_ACTIVE
    if state == Business.State.HISTORICAL:
        allowable_filings = ALLOWABLE_FILINGS_HISTORICAL

    allowable_filing_types = filter(lambda x: legal_type in x[1].get(user_role, []), allowable_filings.items())
    return [filing_type[0] for filing_type in allowable_filing_types]
