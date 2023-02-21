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

import requests
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

        # disallow - only staff are allowed
        staff_only_actions = ['add_comment']
        if any(elem in action for elem in staff_only_actions):
            return False

        template_url = current_app.config.get('AUTH_SVC_URL')
        auth_url = f'{template_url}/entities/{identifier}/authorizations'

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


ALLOWABLE_FILINGS: Final = {
    'staff': {
        Business.State.ACTIVE: {
            'adminFreeze': ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'],
            'alteration': ['BC', 'BEN', 'ULC', 'CC'],
            'annualReport': ['CP', 'BEN', 'BC', 'ULC', 'CC'],
            'changeOfAddress': ['CP', 'BEN', 'BC', 'ULC', 'CC'],
            'changeOfDirectors': ['CP', 'BEN', 'BC', 'ULC', 'CC'],
            'changeOfRegistration': ['SP', 'GP'],
            'consentContinuationOut': ['BC', 'BEN', 'CC', 'ULC'],
            'conversion': ['SP', 'GP', 'BEN'],
            'correction': ['CP', 'BEN', 'SP', 'GP', 'BC', 'ULC', 'CC'],
            'courtOrder': ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'],
            'dissolution': ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC', 'SP', 'GP'],
            'incorporationApplication': ['CP', 'BC', 'BEN', 'ULC', 'CC'],
            'registrarsNotation': ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'],
            'registrarsOrder': ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'],
            'registration': ['SP', 'GP'],
            'specialResolution': ['CP'],
            'transition': ['BC', 'BEN', 'CC', 'ULC'],
            'restoration': {
                'limitedRestorationExtension': ['BC', 'BEN', 'CC', 'ULC', 'LLC'],
                'limitedRestorationToFull': ['BC', 'BEN', 'CC', 'ULC', 'LLC']
            }
        },
        Business.State.HISTORICAL: {
            'courtOrder': ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'],
            'putBackOn': ['SP', 'GP', 'BEN', 'CP', 'BC', 'CC', 'ULC'],
            'registrarsNotation': ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'],
            'registrarsOrder': ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'],
            'restoration': {
                'fullRestoration': ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'],
                'limitedRestoration': ['BC', 'BEN', 'CC', 'ULC', 'LLC']
            }
        }
    },
    'user': {
        Business.State.ACTIVE: {
            'alteration': ['BC', 'BEN', 'ULC', 'CC'],
            'annualReport': ['CP', 'BEN', 'BC', 'ULC', 'CC'],
            'changeOfAddress': ['CP', 'BEN', 'BC', 'ULC', 'CC'],
            'changeOfDirectors': ['CP', 'BEN', 'BC', 'ULC', 'CC'],
            'changeOfRegistration': ['SP', 'GP'],
            'dissolution': ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC', 'SP', 'GP'],
            'incorporationApplication': ['CP', 'BC', 'BEN', 'ULC', 'CC'],
            'registration': ['SP', 'GP'],
            'specialResolution': ['CP'],
            'transition': ['BC', 'BEN', 'CC', 'ULC'],
        },
        Business.State.HISTORICAL: {
            'restoration': {
                'fullRestoration': ['BC', 'BEN', 'CC', 'ULC'],
                'limitedRestoration': ['BC', 'BEN', 'CC', 'ULC'],
                'limitedRestorationExtension': ['BC', 'BEN', 'CC', 'ULC'],
                'limitedRestorationToFull': ['BC', 'BEN', 'CC', 'ULC']
            }
        }
    }
}


def is_allowed(state: Business.State, filing_type: str, legal_type: str, jwt: JwtManager, sub_filing_type: str = None):
    """Is allowed to do filing."""
    user_role = 'user'
    if jwt.contains_role([STAFF_ROLE, SYSTEM_ROLE, COLIN_SVC_ROLE]):
        user_role = 'staff'

    allowable_filing = ALLOWABLE_FILINGS.get(user_role, {}).get(state, {}).get(filing_type, [])
    if allowable_filing and sub_filing_type:
        allowable_filing = allowable_filing.get(sub_filing_type, [])

    return legal_type in allowable_filing


def get_allowed(state: Business.State, legal_type: str, jwt: JwtManager):
    """Get allowed type of filing types for the current user."""
    user_role = 'user'
    if jwt.contains_role([STAFF_ROLE, SYSTEM_ROLE, COLIN_SVC_ROLE]):
        user_role = 'staff'

    allowable_filings = ALLOWABLE_FILINGS.get(user_role, {}).get(state, {})

    allowable_filing_types = []
    for allowable_filing in allowable_filings.items():
        types = allowable_filing[1]
        if isinstance(types, list):
            if legal_type in types:
                allowable_filing_types.append(allowable_filing[0])
        else:
            sub_filing_types = filter(lambda x: legal_type in x[1], types.items())
            allowable_filing_types.append({
                allowable_filing[0]: [sub_filing_type[0] for sub_filing_type in sub_filing_types]
            })

    return allowable_filing_types


def get_account_by_affiliated_identifier(token, identifier: str):
    """Return the account affiliated to the business."""
    auth_url = current_app.config.get('AUTH_SVC_URL')
    url = f'{auth_url}/orgs?affiliation={identifier}'

    headers = {
        'Authorization': f'Bearer {token}'
    }

    res = requests.get(url, headers=headers)
    try:
        return res.json()
    except Exception:  # noqa B902; pylint: disable=W0703;
        current_app.logger.error('Failed to get response')
        return None
