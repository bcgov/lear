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
from enum import Enum
from http import HTTPStatus
from typing import Final, List
from urllib.parse import urljoin

import requests
from flask import current_app
from flask_jwt_oidc import JwtManager
from requests import Session, exceptions
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from legal_api.models import Business, Filing
from legal_api.services.warnings.business.business_checks import WarningType


SYSTEM_ROLE = 'system'
STAFF_ROLE = 'staff'
BASIC_USER = 'basic'
COLIN_SVC_ROLE = 'colin'
PUBLIC_USER = 'public_user'
ACCOUNT_IDENTITY = 'account_identity'


class BusinessBlocker(str, Enum):
    """Define an enum for business level blocker checks."""

    # Currently DEFAULT encapsulates a bunch of business level blocker checks
    # to make it easier to check if a business is blocked.  If there is ever a need to be more granular,
    # the individual checks within DEFAULT could be added as an individual enum item.
    DEFAULT = 'DEFAULT'
    ADMN_FRZE = 'ADMN_FRZE'


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

    # allow IDIM view access on everything
    if len(action) == 1 and action[0] == 'view' and jwt.validate_roles([ACCOUNT_IDENTITY]):
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
            'adminFreeze': {
                'legalTypes': ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'],
            },
            'alteration': {
                'legalTypes': ['BC', 'BEN', 'ULC', 'CC'],
                'blockerChecks': {
                    'business': [BusinessBlocker.DEFAULT]
                }
            },
            'annualReport': {
                'legalTypes': ['CP', 'BEN', 'BC', 'ULC', 'CC'],
                'blockerChecks': {
                    'business': [BusinessBlocker.DEFAULT]
                }
            },
            'changeOfAddress': {
                'legalTypes': ['CP', 'BEN', 'BC', 'ULC', 'CC'],
                'blockerChecks': {
                    'business': [BusinessBlocker.DEFAULT]
                }
            },
            'changeOfDirectors': {
                'legalTypes': ['CP', 'BEN', 'BC', 'ULC', 'CC'],
                'blockerChecks': {
                    'business': [BusinessBlocker.DEFAULT]
                }
            },
            'changeOfRegistration': {
                'legalTypes': ['SP', 'GP'],
                'blockerChecks': {
                    'warningTypes': [WarningType.MISSING_REQUIRED_BUSINESS_INFO],
                    'business': [BusinessBlocker.DEFAULT]
                }
            },
            'consentContinuationOut': {
                'legalTypes': ['BC', 'BEN', 'CC', 'ULC'],
                'blockerChecks': {
                    'business': [BusinessBlocker.DEFAULT]
                }
            },
            'conversion': {
                'legalTypes': ['SP', 'GP']
            },
            'correction': {
                'legalTypes': ['CP', 'BEN', 'SP', 'GP', 'BC', 'ULC', 'CC'],
                'blockerChecks': {
                    'warningTypes': [WarningType.MISSING_REQUIRED_BUSINESS_INFO],
                    'business': [BusinessBlocker.DEFAULT]
                }
            },
            'courtOrder': {
                'legalTypes': ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'],
                'blockerChecks': {
                    'business': [BusinessBlocker.DEFAULT]
                }
            },
            'dissolution': {
                'voluntaryDissolution': {
                    'legalTypes': ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC', 'SP', 'GP'],
                    'blockerChecks': {
                        'warningTypes': [WarningType.MISSING_REQUIRED_BUSINESS_INFO],
                        'business': [BusinessBlocker.DEFAULT]
                    }
                },
                'administrativeDissolution': {
                    'legalTypes': ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC', 'SP', 'GP'],
                    'blockerChecks': {
                        'warningTypes': [WarningType.MISSING_REQUIRED_BUSINESS_INFO],
                        'business': [BusinessBlocker.DEFAULT]
                    }
                }
            },
            'incorporationApplication': {
                'legalTypes': ['CP', 'BC', 'BEN', 'ULC', 'CC'],
                'businessExists': False  # only show filing when providing allowable filings not specific to a business
            },
            'registrarsNotation': {
                'legalTypes': ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'],
                'blockerChecks': {
                    'business': [BusinessBlocker.DEFAULT]
                }
            },
            'registrarsOrder': {
                'legalTypes':  ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'],
                'blockerChecks': {
                    'business': [BusinessBlocker.DEFAULT]
                }
            },
            'registration': {
                'legalTypes': ['SP', 'GP'],
                'businessExists': False  # only show filing when providing allowable filings not specific to a business
            },
            'specialResolution': {
                'legalTypes': ['CP'],
                'blockerChecks': {
                    'business': [BusinessBlocker.DEFAULT]
                }
            },
            'transition': {
                'legalTypes': ['BC', 'BEN', 'CC', 'ULC'],
                'blockerChecks': {
                    'business': [BusinessBlocker.DEFAULT]
                }
            },
            'restoration': {
                'limitedRestorationExtension': {
                    'legalTypes': ['BC', 'BEN', 'CC', 'ULC', 'LLC'],
                    'blockerChecks': {
                        'validStateFilings': ['restoration.limitedRestoration',
                                              'restoration.limitedRestorationExtension'],
                        'business': [BusinessBlocker.DEFAULT]
                    }
                },
                'limitedRestorationToFull': {
                    'legalTypes': ['BC', 'BEN', 'CC', 'ULC', 'LLC'],
                    'blockerChecks': {
                        'validStateFilings': ['restoration.limitedRestoration',
                                              'restoration.limitedRestorationExtension'],
                        'business': [BusinessBlocker.DEFAULT]
                    }
                }
            }
        },
        Business.State.HISTORICAL: {
            'courtOrder': {
                'legalTypes': ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'],
            },
            'putBackOn': {
                'legalTypes': ['SP', 'GP', 'BEN', 'CP', 'BC', 'CC', 'ULC'],
                'blockerChecks': {
                    # FUTURE add outstanding filings to invalidStateFilings when implemented
                    'invalidStateFilings': []
                }
            },
            'registrarsNotation': {
                'legalTypes': ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC']
            },
            'registrarsOrder': {
                'legalTypes': ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC']
            },
            'restoration': {
                'fullRestoration': {
                    'legalTypes': ['BC', 'BEN', 'CC', 'ULC'],
                    'blockerChecks': {
                        # FUTURE add outstanding filings to invalidStateFilings when implemented
                        'invalidStateFilings': ['continuationIn', 'continuationOut']
                    }
                },
                'limitedRestoration': {
                    'legalTypes': ['BC', 'BEN', 'CC', 'ULC'],
                    'blockerChecks': {
                        # FUTURE add outstanding filings to invalidStateFilings when implemented
                        'invalidStateFilings': ['continuationIn', 'continuationOut']
                    }
                }
            }
        }
    },
    'general': {
        Business.State.ACTIVE: {
            'alteration': {
                'legalTypes': ['BC', 'BEN', 'ULC', 'CC'],
                'blockerChecks': {
                    'business': [BusinessBlocker.DEFAULT]
                }
            },
            'annualReport': {
                'legalTypes': ['CP', 'BEN', 'BC', 'ULC', 'CC'],
                'blockerChecks': {
                    'business': [BusinessBlocker.DEFAULT]
                }
            },
            'changeOfAddress': {
                'legalTypes': ['CP', 'BEN', 'BC', 'ULC', 'CC'],
                'blockerChecks': {
                    'business': [BusinessBlocker.DEFAULT],
                }
            },
            'changeOfDirectors': {
                'legalTypes': ['CP', 'BEN', 'BC', 'ULC', 'CC'],
                'blockerChecks': {
                    'business': [BusinessBlocker.DEFAULT]
                }
            },
            'changeOfRegistration': {
                'legalTypes': ['SP', 'GP'],
                'blockerChecks': {
                    'warningTypes': [WarningType.MISSING_REQUIRED_BUSINESS_INFO],
                    'business': [BusinessBlocker.DEFAULT]
                }
            },
            'dissolution': {
                'voluntaryDissolution': {
                    'legalTypes': ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC', 'SP', 'GP'],
                    'blockerChecks': {
                        'warningTypes': [WarningType.MISSING_REQUIRED_BUSINESS_INFO],
                        'business': [BusinessBlocker.DEFAULT]
                    }
                },
            },
            'incorporationApplication': {
                'legalTypes': ['CP', 'BC', 'BEN', 'ULC', 'CC'],
                'businessExists': False  # only show filing when providing allowable filings not specific to a business
            },
            'registration': {
                'legalTypes': ['SP', 'GP'],
                'businessExists': False  # only show filing when providing allowable filings not specific to a business
            },
            'specialResolution': {
                'legalTypes': ['CP'],
                'blockerChecks': {
                    'business': [BusinessBlocker.DEFAULT]
                }
            },
            'transition': {
                'legalTypes': ['BC', 'BEN', 'CC', 'ULC'],
                'blockerChecks': {
                    'business': [BusinessBlocker.DEFAULT]
                }
            }
        },
        Business.State.HISTORICAL: {}
    }
}


# pylint: disable=(too-many-arguments,too-many-locals
def is_allowed(state: Business.State,
               filing_type: str,
               legal_type: str,
               jwt: JwtManager,
               sub_filing_type: str = None):
    """Is allowed to do filing."""
    user_role = 'general'
    if jwt.contains_role([STAFF_ROLE, SYSTEM_ROLE, COLIN_SVC_ROLE]):
        user_role = 'staff'

    allowable_filing = ALLOWABLE_FILINGS.get(user_role, {}).get(state, {}).get(filing_type, {})
    allowable_filing_legal_types = allowable_filing.get('legalTypes', [])

    if allowable_filing and sub_filing_type:
        allowable_filing_legal_types = allowable_filing.get(sub_filing_type, {}).get('legalTypes', [])

    return legal_type in allowable_filing_legal_types


def get_allowable_actions(jwt: JwtManager, business: Business):
    """Get allowable actions."""
    base_url = current_app.config.get('LEGAL_API_BASE_URL')
    allowed_filings = get_allowed_filings(business, business.state, business.legal_type, jwt)
    filing_submission_url = urljoin(base_url, f'{business.identifier}/filings')
    result = {
        'filing': {
            'filingSubmissionLink': filing_submission_url,
            'filingTypes': allowed_filings
        }
    }
    return result


def get_allowed_filings(business: Business, state: Business.State, legal_type: str, jwt: JwtManager):
    """Get allowed type of filing types for the current user."""
    # importing here to avoid circular dependencies
    # pylint: disable=import-outside-toplevel
    from legal_api.core.meta import FilingMeta

    user_role = 'general'
    if jwt.contains_role([STAFF_ROLE, SYSTEM_ROLE, COLIN_SVC_ROLE]):
        user_role = 'staff'

    state_filing = None
    if business and business.state_filing_id:
        state_filing = Filing.find_by_id(business.state_filing_id)

    # doing this check up front to cache result
    business_blocker_dict: dict = business_blocker_check(business)
    allowable_filings = ALLOWABLE_FILINGS.get(user_role, {}).get(state, {})
    allowable_filing_types = []

    for allowable_filing_key, allowable_filing_value in allowable_filings.items():
        # skip if business does not exist and filing is not required
        if not business and allowable_filing_value.get('businessExists', True):
            continue
        # skip if this filing does not need to be returned for existing businesses
        if business and not allowable_filing_value.get('businessExists', True):
            continue

        allowable_filing_legal_types = allowable_filing_value.get('legalTypes', [])
        if allowable_filing_legal_types:
            if legal_type in allowable_filing_legal_types:
                if has_blocker(business, state_filing, allowable_filing_value, business_blocker_dict):
                    continue
                allowable_filing_types \
                    .append({'name': allowable_filing_key,
                             'displayName': FilingMeta.get_display_name(legal_type, allowable_filing_key),
                             'feeCode': Filing.get_fee_code(legal_type, allowable_filing_key)})
        else:
            filing_sub_type_items = \
                filter(lambda x: legal_type in x[1].get('legalTypes', []), allowable_filing_value.items())
            for filing_sub_type_item_key, filing_sub_type_item_value in filing_sub_type_items:
                if has_blocker(business, state_filing, filing_sub_type_item_value, business_blocker_dict):
                    continue
                allowable_filing_types \
                    .append({'name': allowable_filing_key,
                             'type': filing_sub_type_item_key,
                             'displayName': FilingMeta.get_display_name(legal_type,
                                                                        allowable_filing_key,
                                                                        filing_sub_type_item_key),
                             'feeCode': Filing.get_fee_code(legal_type,
                                                            allowable_filing_key,
                                                            filing_sub_type_item_key)})

    return allowable_filing_types


def has_blocker(business: Business, state_filing: Filing, allowable_filing: dict, business_blocker_dict: dict):
    """Return True if allowable filing has a blocker."""
    if not (blocker_checks := allowable_filing.get('blockerChecks', {})):
        return False

    if has_business_blocker(blocker_checks, business_blocker_dict):
        return True

    if has_blocker_valid_state_filing(state_filing, blocker_checks):
        return True

    if has_blocker_invalid_state_filing(state_filing, blocker_checks):
        return True

    if has_blocker_warning_filing(business.warnings, blocker_checks):
        return True

    return False


def has_business_blocker(blocker_checks: dict, business_blocker_dict: dict):
    """Return True if the business has a default blocker."""
    if not (business_blocker_checks := blocker_checks.get('business', [])):
        return False

    for business_blocker_check_type in business_blocker_checks:
        if business_blocker_dict[business_blocker_check_type]:
            return True

    return False


def business_blocker_check(business: Business):
    """Return True if the business has a default blocker condition."""
    business_blocker_checks: dict = {
        BusinessBlocker.ADMN_FRZE: False,
        BusinessBlocker.DEFAULT: False
    }

    if not business:
        return business_blocker_checks

    if has_blocker_filing(business):
        business_blocker_checks[BusinessBlocker.DEFAULT] = True

    if business.admin_freeze:
        business_blocker_checks = {
            BusinessBlocker.ADMN_FRZE: True,
            BusinessBlocker.DEFAULT: True
        }

    return business_blocker_checks


def has_blocker_filing(business: Business):
    """Check if there are any incomplete states filings. This is a blocker because it needs to be completed first."""
    # importing here to avoid circular dependencies
    # pylint: disable=import-outside-toplevel
    from legal_api.core.filing import Filing as CoreFiling

    filing_statuses = [Filing.Status.DRAFT.value,
                       Filing.Status.PENDING.value,
                       Filing.Status.PENDING_CORRECTION.value,
                       Filing.Status.ERROR.value,
                       Filing.Status.PAID.value]
    blocker_filing_matches = Filing.get_filings_by_status(business.id, filing_statuses)
    if any(blocker_filing_matches):
        return True

    filing_types = [CoreFiling.FilingTypes.ALTERATION.value, CoreFiling.FilingTypes.CORRECTION.value]
    blocker_filing_matches = Filing.get_incomplete_filings_by_types(business.id, filing_types)
    return any(blocker_filing_matches)


def has_pending_filings(business: Business):
    """Return True if there are any pending filings."""
    result = len(Filing.get_filings_by_status(business.id, [Filing.Status.PAID.value])) > 0
    return result


def has_blocker_valid_state_filing(state_filing: Filing, blocker_checks: dict):
    """Check if there is a required state filing that business does not have."""
    if not (state_filing_types := blocker_checks.get('validStateFilings', [])):
        return False

    if not state_filing:
        return True

    return not has_state_filing(state_filing, state_filing_types)


def has_blocker_invalid_state_filing(state_filing: Filing, blocker_checks: dict):
    """Check if business has an invalid state filing."""
    if not (state_filing_types := blocker_checks.get('invalidStateFilings', [])):
        return False

    if not state_filing:
        return False

    return has_state_filing(state_filing, state_filing_types)


def has_state_filing(state_filing: Filing, state_filing_types: list):
    """Return if state filing matches any filings provided in state_filing_types arg ."""
    for state_filing_type in state_filing_types:
        filing_type, filing_sub_type = parse_filing_info(state_filing_type)
        if is_filing_type_match(state_filing, filing_type, filing_sub_type):
            return True

    return False


def is_filing_type_match(filing: Filing, filing_type: str, filing_sub_type: str):
    """Return if the filing type and filing sub-type matches.  Skip matching on sub-type if value is None."""
    if not filing_sub_type:
        return filing.filing_type == filing_type

    return filing.filing_type == filing_type and filing.filing_sub_type == filing_sub_type


def parse_filing_info(filing_info: str):
    """Parse the filing info from a string that separates filing type and filing sub-type with a period."""
    filing_info = filing_info.split('.')
    filing_type = filing_info[0]
    filing_sub_type = filing_info[1] if len(filing_info) > 1 else None
    return filing_type, filing_sub_type


def has_blocker_warning_filing(warnings: List, blocker_checks: dict):
    """Return if business has a warning that blocks filing."""
    if not (blocker_warning_filings := blocker_checks.get('warningTypes', [])):
        return False

    warning_types = [x['warningType'] for x in warnings]
    # update to only keep unique warning types
    warning_types = list(set(warning_types))
    warning_matches = any(x for x in warning_types if x in blocker_warning_filings)
    return warning_matches


def get_allowed(state: Business.State, legal_type: str, jwt: JwtManager):
    """Get allowed type of filing types for the current user."""
    user_role = 'general'
    if jwt.contains_role([STAFF_ROLE, SYSTEM_ROLE, COLIN_SVC_ROLE]):
        user_role = 'staff'

    allowable_filings = ALLOWABLE_FILINGS.get(user_role, {}).get(state, {})
    allowable_filing_types = []
    for allowable_filing_key, allowable_filing_value in allowable_filings.items():
        if legal_types := allowable_filing_value.get('legalTypes', None):
            if legal_type in legal_types:
                allowable_filing_types.append(allowable_filing_key)
        else:
            sub_filing_types = [x for x in allowable_filing_value.items() if legal_type in x[1].get('legalTypes')]
            if sub_filing_types:
                allowable_filing_types.append({
                    allowable_filing_key: [sub_filing_type[0] for sub_filing_type in sub_filing_types]
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
