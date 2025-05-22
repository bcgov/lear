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

# pylint: disable=too-many-lines
"""This manages all of the authentication and authorization service."""
from datetime import datetime, timezone
from enum import Enum
from http import HTTPStatus
from typing import List
from urllib.parse import urljoin

from flask import Response, current_app, request
from flask_caching import Cache
from flask_jwt_oidc import JwtManager
from requests import Session, exceptions
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from legal_api.models import Business, Filing
from legal_api.services.digital_credentials_auth import (
    are_digital_credentials_allowed,
    get_digital_credentials_preconditions,
)
from legal_api.services.warnings.business.business_checks import WarningType


cache = Cache()

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
    BUSINESS_FROZEN = 'BUSINESS_FROZEN'
    DRAFT_PENDING = 'DRAFT_PENDING'
    NOT_IN_GOOD_STANDING = 'NOT_IN_GOOD_STANDING'
    AMALGAMATING_BUSINESS = 'AMALGAMATING_BUSINESS'
    IN_DISSOLUTION = 'IN_DISSOLUTION'
    FILING_WITHDRAWAL = 'FILING_WITHDRAWAL'


class BusinessRequirement(str, Enum):
    """Define an enum for business requirement scenarios."""

    EXIST = 'EXIST'
    NOT_EXIST = 'NOT_EXIST'
    NO_RESTRICTION = 'NO_RESTRICTION'


def _call_auth_api(path: str, token: str) -> Response:
    """Return the auth api response for the given endpoint path."""
    if not token:
        return None

    current_app.logger.debug(f'Auth get {path}...')
    template_url = current_app.config.get('AUTH_SVC_URL')
    auth_url = template_url + '/' if template_url[-1] != '/' else template_url
    auth_url += path

    headers = {'Authorization': 'Bearer ' + token}
    try:
        http = Session()
        retries = Retry(total=5,
                        backoff_factor=0.1,
                        status_forcelist=[500, 502, 503, 504])
        http.mount('http://', HTTPAdapter(max_retries=retries))
        resp = http.get(url=auth_url, headers=headers)
        current_app.logger.debug(f'Auth get {path} response status: {str(resp.status_code)}')
        return resp

    except (exceptions.ConnectionError,  # pylint: disable=broad-except
            exceptions.Timeout,
            ValueError,
            Exception) as err:
        current_app.logger.debug(err.with_traceback(None))
        current_app.logger.error(f'Auth connection failure, url: {auth_url}')
        return None


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

    # allow IDIM and Competent Authorities view access on everything
    if len(action) == 1 and action[0] == 'view':
        if jwt.validate_roles([ACCOUNT_IDENTITY]) or has_product('CA_SEARCH', jwt.get_token_auth_header()):
            return True

    if jwt.has_one_of_roles([BASIC_USER, PUBLIC_USER]):

        # disallow - only staff are allowed
        staff_only_actions = ['add_comment']
        if any(elem in action for elem in staff_only_actions):
            return False

        rv = _call_auth_api(f'entities/{identifier}/authorizations', jwt.get_token_auth_header())
        if rv and rv.status_code == HTTPStatus.OK and (roles := rv.json().get('roles')):
            return all(elem.lower() in roles for elem in action)

    return False


def has_roles(jwt: JwtManager, roles: List[str]) -> bool:
    """Assert the users JWT has the required role(s).

    Assumes the JWT is already validated.
    """
    if jwt.validate_roles(roles):
        return True
    return False


def get_allowable_filings_dict():
    """Return dictionary containing rules for when filings are allowed."""
    # importing here to avoid circular dependencies
    # pylint: disable=import-outside-toplevel
    from legal_api.core.filing import Filing as CoreFiling

    filing_types_compact = CoreFiling.FilingTypesCompact

    return {
        'staff': {
            Business.State.ACTIVE: {
                'adminFreeze': {
                    'legalTypes': ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC', 'C', 'CBEN', 'CUL', 'CCC'],
                },
                'agmExtension': {
                    'legalTypes': ['BC', 'BEN', 'ULC', 'CC', 'C', 'CBEN', 'CUL', 'CCC'],
                    'blockerChecks': {
                        'business': [BusinessBlocker.DEFAULT, BusinessBlocker.NOT_IN_GOOD_STANDING]
                    }
                },
                'agmLocationChange': {
                    'legalTypes': ['BC', 'BEN', 'ULC', 'CC', 'C', 'CBEN', 'CUL', 'CCC'],
                    'blockerChecks': {
                        'business': [BusinessBlocker.DEFAULT, BusinessBlocker.NOT_IN_GOOD_STANDING]
                    }
                },
                'alteration': {
                    'legalTypes': ['BC', 'BEN', 'ULC', 'CC', 'C', 'CBEN', 'CUL', 'CCC'],
                    'blockerChecks': {
                        'business': [BusinessBlocker.DEFAULT, BusinessBlocker.IN_DISSOLUTION]
                    }
                },
                'amalgamationApplication': {
                    'businessRequirement': BusinessRequirement.NO_RESTRICTION,
                    'regular': {
                        'legalTypes': ['BEN', 'BC', 'ULC', 'CC', 'C', 'CBEN', 'CUL', 'CCC'],
                        'blockerChecks': {
                            'business': [BusinessBlocker.DEFAULT,
                                         BusinessBlocker.NOT_IN_GOOD_STANDING,
                                         BusinessBlocker.IN_DISSOLUTION],
                            'futureEffectiveFilings': [filing_types_compact.DISSOLUTION_VOLUNTARY,
                                                       filing_types_compact.DISSOLUTION_ADMINISTRATIVE]
                        }
                    },
                    'vertical': {
                        'legalTypes': ['BEN', 'BC', 'ULC', 'CC', 'C', 'CBEN', 'CUL', 'CCC'],
                        'blockerChecks': {
                            'business': [BusinessBlocker.DEFAULT,
                                         BusinessBlocker.NOT_IN_GOOD_STANDING,
                                         BusinessBlocker.IN_DISSOLUTION],
                            'futureEffectiveFilings': [filing_types_compact.DISSOLUTION_VOLUNTARY,
                                                       filing_types_compact.DISSOLUTION_ADMINISTRATIVE]
                        }
                    },
                    'horizontal': {
                        'legalTypes': ['BEN', 'BC', 'ULC', 'CC', 'C', 'CBEN', 'CUL', 'CCC'],
                        'blockerChecks': {
                            'business': [BusinessBlocker.DEFAULT,
                                         BusinessBlocker.NOT_IN_GOOD_STANDING,
                                         BusinessBlocker.IN_DISSOLUTION],
                            'futureEffectiveFilings': [filing_types_compact.DISSOLUTION_VOLUNTARY,
                                                       filing_types_compact.DISSOLUTION_ADMINISTRATIVE]
                        }
                    }
                },
                'amalgamationOut': {
                    'legalTypes': ['BC', 'BEN', 'CC', 'ULC', 'C', 'CBEN', 'CUL', 'CCC'],
                    'blockerChecks': {
                        'business': [BusinessBlocker.DEFAULT, BusinessBlocker.NOT_IN_GOOD_STANDING],
                        'completedFilings': ['consentAmalgamationOut']
                    }
                },
                'annualReport': {
                    'legalTypes': ['CP', 'BEN', 'BC', 'ULC', 'CC', 'C', 'CBEN', 'CUL', 'CCC'],
                    'blockerChecks': {
                        'business': [BusinessBlocker.DEFAULT]
                    }
                },
                'appointReceiver': {
                    'legalTypes': ['BC', 'BEN', 'ULC', 'CC', 'C', 'CBEN', 'CUL', 'CCC'],
                    'blockerChecks': {
                        'business': [BusinessBlocker.DEFAULT]
                    }
                },
                'ceaseReceiver': {
                    'legalTypes': ['BC', 'BEN', 'ULC', 'CC', 'C', 'CBEN', 'CUL', 'CCC'],
                    'blockerChecks': {
                        'business': [BusinessBlocker.DEFAULT]
                    }
                },
                'changeOfAddress': {
                    'legalTypes': ['CP', 'BEN', 'BC', 'ULC', 'CC', 'C', 'CBEN', 'CUL', 'CCC'],
                    'blockerChecks': {
                        'business': [BusinessBlocker.DEFAULT]
                    }
                },
                'changeOfDirectors': {
                    'legalTypes': ['CP', 'BEN', 'BC', 'ULC', 'CC', 'C', 'CBEN', 'CUL', 'CCC'],
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
                'continuationIn': {
                    'legalTypes': ['C', 'CBEN', 'CUL', 'CCC'],
                    # only show filing when providing allowable filings not specific to a business
                    'businessRequirement': BusinessRequirement.NOT_EXIST
                },
                'consentAmalgamationOut': {
                    'legalTypes': ['BC', 'BEN', 'CC', 'ULC', 'C', 'CBEN', 'CUL', 'CCC'],
                    'blockerChecks': {
                        'business': [BusinessBlocker.DEFAULT, BusinessBlocker.NOT_IN_GOOD_STANDING]
                    }
                },
                'consentContinuationOut': {
                    'legalTypes': ['BC', 'BEN', 'CC', 'ULC', 'C', 'CBEN', 'CUL', 'CCC'],
                    'blockerChecks': {
                        'business': [BusinessBlocker.DEFAULT, BusinessBlocker.NOT_IN_GOOD_STANDING]
                    }
                },
                'continuationOut': {
                    'legalTypes': ['BC', 'BEN', 'CC', 'ULC', 'C', 'CBEN', 'CUL', 'CCC'],
                    'blockerChecks': {
                        'business': [BusinessBlocker.DEFAULT, BusinessBlocker.NOT_IN_GOOD_STANDING],
                        'completedFilings': ['consentContinuationOut']
                    }
                },
                'conversion': {
                    'legalTypes': ['SP', 'GP']
                },
                'correction': {
                    'legalTypes': ['CP', 'BEN', 'SP', 'GP', 'BC', 'ULC', 'CC', 'C', 'CBEN', 'CUL', 'CCC'],
                    'blockerChecks': {
                        'warningTypes': [WarningType.MISSING_REQUIRED_BUSINESS_INFO],
                        'business': [BusinessBlocker.DEFAULT]
                    }
                },
                'courtOrder': {
                    'legalTypes': ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC', 'C', 'CBEN', 'CUL', 'CCC']
                },
                'dissolution': {
                    'voluntary': {
                        'legalTypes': ['CP', 'BC', 'BEN', 'CC', 'ULC', 'SP', 'GP', 'C', 'CBEN', 'CUL', 'CCC'],
                        'blockerChecks': {
                            'warningTypes': [WarningType.MISSING_REQUIRED_BUSINESS_INFO],
                            'business': [BusinessBlocker.DEFAULT,
                                         BusinessBlocker.IN_DISSOLUTION]
                        }
                    },
                    'administrative': {
                        'legalTypes': ['CP', 'BC', 'BEN', 'CC', 'ULC', 'SP', 'GP', 'C', 'CBEN', 'CUL', 'CCC'],
                        'blockerChecks': {
                            'warningTypes': [WarningType.MISSING_REQUIRED_BUSINESS_INFO],
                            'business': [BusinessBlocker.DRAFT_PENDING]
                        }
                    }
                },
                'incorporationApplication': {
                    'legalTypes': ['CP', 'BC', 'BEN', 'ULC', 'CC'],
                    # only show filing when providing allowable filings not specific to a business
                    'businessRequirement': BusinessRequirement.NOT_EXIST
                },
                'putBackOff': {
                    'legalTypes': ['BEN', 'BC', 'CC', 'ULC', 'C', 'CBEN', 'CUL', 'CCC']
                },
                'registrarsNotation': {
                    'legalTypes': ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC', 'C', 'CBEN', 'CUL', 'CCC']
                },
                'registrarsOrder': {
                    'legalTypes': ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC', 'C', 'CBEN', 'CUL', 'CCC']
                },
                'registration': {
                    'legalTypes': ['SP', 'GP'],
                    # only show filing when providing allowable filings not specific to a business
                    'businessRequirement': BusinessRequirement.NOT_EXIST
                },
                'specialResolution': {
                    'legalTypes': ['CP'],
                    'blockerChecks': {
                        'business': [BusinessBlocker.DEFAULT]
                    }
                },
                'transition': {
                    'legalTypes': ['BC', 'BEN', 'CC', 'ULC', 'C', 'CBEN', 'CUL', 'CCC']
                },
                'restoration': {
                    'limitedRestorationExtension': {
                        'legalTypes': ['BC', 'BEN', 'CC', 'ULC', 'C', 'CBEN', 'CUL', 'CCC'],
                        'blockerChecks': {
                            'validStateFilings': [filing_types_compact.RESTORATION_LIMITED_RESTORATION,
                                                  filing_types_compact.RESTORATION_LIMITED_RESTORATION_EXT],
                            'business': [BusinessBlocker.DEFAULT]
                        }
                    },
                    'limitedRestorationToFull': {
                        'legalTypes': ['BC', 'BEN', 'CC', 'ULC', 'C', 'CBEN', 'CUL', 'CCC'],
                        'blockerChecks': {
                            'validStateFilings': [filing_types_compact.RESTORATION_LIMITED_RESTORATION,
                                                  filing_types_compact.RESTORATION_LIMITED_RESTORATION_EXT],
                            'business': [BusinessBlocker.DEFAULT]
                        }
                    }
                },
                'noticeOfWithdrawal': {
                    'legalTypes': ['BC', 'BEN', 'CC', 'ULC', 'C', 'CBEN', 'CUL', 'CCC'],
                    'blockerChecks': {
                        'business': [BusinessBlocker.FILING_WITHDRAWAL]
                    },
                    'businessRequirement': BusinessRequirement.NO_RESTRICTION
                }
            },
            Business.State.HISTORICAL: {
                'courtOrder': {
                    'legalTypes': ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC', 'C', 'CBEN', 'CUL', 'CCC'],
                },
                'putBackOn': {
                    'legalTypes': ['SP', 'GP', 'BEN', 'CP', 'BC', 'CC', 'ULC', 'C', 'CBEN', 'CUL', 'CCC'],
                },
                'registrarsNotation': {
                    'legalTypes': ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC', 'C', 'CBEN', 'CUL', 'CCC']
                },
                'registrarsOrder': {
                    'legalTypes': ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC', 'C', 'CBEN', 'CUL', 'CCC']
                },
                'restoration': {
                    'fullRestoration': {
                        'legalTypes': ['BC', 'BEN', 'CC', 'ULC', 'C', 'CBEN', 'CUL', 'CCC'],
                        'blockerChecks': {
                            'invalidStateFilings': ['continuationOut'],
                            'business': [BusinessBlocker.AMALGAMATING_BUSINESS]
                        }
                    },
                    'limitedRestoration': {
                        'legalTypes': ['BC', 'BEN', 'CC', 'ULC', 'C', 'CBEN', 'CUL', 'CCC'],
                        'blockerChecks': {
                            'invalidStateFilings': ['continuationOut'],
                            'business': [BusinessBlocker.AMALGAMATING_BUSINESS]
                        }
                    }
                }
            }
        },
        'general': {
            Business.State.ACTIVE: {
                'agmExtension': {
                    'legalTypes': ['BC', 'BEN', 'ULC', 'CC', 'C', 'CBEN', 'CUL', 'CCC'],
                    'blockerChecks': {
                        'business': [BusinessBlocker.DEFAULT, BusinessBlocker.NOT_IN_GOOD_STANDING]
                    }
                },
                'agmLocationChange': {
                    'legalTypes': ['BC', 'BEN', 'ULC', 'CC', 'C', 'CBEN', 'CUL', 'CCC'],
                    'blockerChecks': {
                        'business': [BusinessBlocker.DEFAULT, BusinessBlocker.NOT_IN_GOOD_STANDING]
                    }
                },
                'alteration': {
                    'legalTypes': ['BC', 'BEN', 'ULC', 'CC', 'C', 'CBEN', 'CUL', 'CCC'],
                    'blockerChecks': {
                        'business': [BusinessBlocker.DEFAULT,
                                     BusinessBlocker.NOT_IN_GOOD_STANDING,
                                     BusinessBlocker.IN_DISSOLUTION],
                        'invalidStateFilings': ['restoration.limitedRestoration',
                                                'restoration.limitedRestorationExtension']
                    }
                },
                'amalgamationApplication': {
                    'businessRequirement': BusinessRequirement.NO_RESTRICTION,
                    'regular': {
                        'legalTypes': ['BEN', 'BC', 'ULC', 'CC', 'C', 'CBEN', 'CUL', 'CCC'],
                        'blockerChecks': {
                            'business': [BusinessBlocker.DEFAULT,
                                         BusinessBlocker.NOT_IN_GOOD_STANDING,
                                         BusinessBlocker.IN_DISSOLUTION],
                            'futureEffectiveFilings': [filing_types_compact.DISSOLUTION_VOLUNTARY,
                                                       filing_types_compact.DISSOLUTION_ADMINISTRATIVE]
                        }
                    },
                    'vertical': {
                        'legalTypes': ['BEN', 'BC', 'ULC', 'CC', 'C', 'CBEN', 'CUL', 'CCC'],
                        'blockerChecks': {
                            'business': [BusinessBlocker.DEFAULT,
                                         BusinessBlocker.NOT_IN_GOOD_STANDING,
                                         BusinessBlocker.IN_DISSOLUTION],
                            'futureEffectiveFilings': [filing_types_compact.DISSOLUTION_VOLUNTARY,
                                                       filing_types_compact.DISSOLUTION_ADMINISTRATIVE]
                        }
                    },
                    'horizontal': {
                        'legalTypes': ['BEN', 'BC', 'ULC', 'CC', 'C', 'CBEN', 'CUL', 'CCC'],
                        'blockerChecks': {
                            'business': [BusinessBlocker.DEFAULT,
                                         BusinessBlocker.NOT_IN_GOOD_STANDING,
                                         BusinessBlocker.IN_DISSOLUTION],
                            'futureEffectiveFilings': [filing_types_compact.DISSOLUTION_VOLUNTARY,
                                                       filing_types_compact.DISSOLUTION_ADMINISTRATIVE]
                        }
                    }
                },
                'annualReport': {
                    'legalTypes': ['CP', 'BEN', 'BC', 'ULC', 'CC', 'C', 'CBEN', 'CUL', 'CCC'],
                    'blockerChecks': {
                        'business': [BusinessBlocker.DEFAULT]
                    }
                },
                'changeOfAddress': {
                    'legalTypes': ['CP', 'BEN', 'BC', 'ULC', 'CC', 'C', 'CBEN', 'CUL', 'CCC'],
                    'blockerChecks': {
                        'business': [BusinessBlocker.DEFAULT],
                    }
                },
                'changeOfDirectors': {
                    'legalTypes': ['CP', 'BEN', 'BC', 'ULC', 'CC', 'C', 'CBEN', 'CUL', 'CCC'],
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
                'consentAmalgamationOut': {
                    'legalTypes': ['BC', 'BEN', 'CC', 'ULC', 'C', 'CBEN', 'CUL', 'CCC'],
                    'blockerChecks': {
                        'business': [BusinessBlocker.DEFAULT, BusinessBlocker.NOT_IN_GOOD_STANDING]
                    }
                },
                'consentContinuationOut': {
                    'legalTypes': ['BC', 'BEN', 'CC', 'ULC', 'C', 'CBEN', 'CUL', 'CCC'],
                    'blockerChecks': {
                        'business': [BusinessBlocker.DEFAULT, BusinessBlocker.NOT_IN_GOOD_STANDING]
                    }
                },
                'continuationIn': {
                    'legalTypes': ['C', 'CBEN', 'CUL', 'CCC'],
                    # only show filing when providing allowable filings not specific to a business
                    'businessRequirement': BusinessRequirement.NOT_EXIST
                },
                'dissolution': {
                    'voluntary': {
                        'legalTypes': ['CP', 'BC', 'BEN', 'CC', 'ULC', 'SP', 'GP', 'C', 'CBEN', 'CUL', 'CCC'],
                        'blockerChecks': {
                            'warningTypes': [WarningType.MISSING_REQUIRED_BUSINESS_INFO],
                            'business': [BusinessBlocker.DEFAULT,
                                         BusinessBlocker.NOT_IN_GOOD_STANDING,
                                         BusinessBlocker.IN_DISSOLUTION]
                        }
                    },
                },
                'incorporationApplication': {
                    'legalTypes': ['CP', 'BC', 'BEN', 'ULC', 'CC'],
                    # only show filing when providing allowable filings not specific to a business
                    'businessRequirement': BusinessRequirement.NOT_EXIST
                },
                'registration': {
                    'legalTypes': ['SP', 'GP'],
                    # only show filing when providing allowable filings not specific to a business
                    'businessRequirement': BusinessRequirement.NOT_EXIST
                },
                'specialResolution': {
                    'legalTypes': ['CP'],
                    'blockerChecks': {
                        'business': [BusinessBlocker.DEFAULT,
                                     BusinessBlocker.NOT_IN_GOOD_STANDING]
                    }
                },
                'transition': {
                    'legalTypes': ['BC', 'BEN', 'CC', 'ULC', 'C', 'CBEN', 'CUL', 'CCC']
                },
                CoreFiling.FilingTypes.TRANSPARENCY_REGISTER.value: {
                    'annual': {
                        'legalTypes': ['BC', 'BEN', 'CC', 'ULC', 'C', 'CBEN', 'CUL', 'CCC'],
                        'blockerChecks': {
                            'business': [BusinessBlocker.BUSINESS_FROZEN],
                            'futureEffectiveFilings': [CoreFiling.FilingTypes.INCORPORATIONAPPLICATION.value]
                        }
                    },
                    'change': {
                        'legalTypes': ['BC', 'BEN', 'CC', 'ULC', 'C', 'CBEN', 'CUL', 'CCC'],
                        'blockerChecks': {
                            'business': [BusinessBlocker.BUSINESS_FROZEN],
                            'futureEffectiveFilings': [CoreFiling.FilingTypes.INCORPORATIONAPPLICATION.value]
                        }
                    },
                    'initial': {
                        'legalTypes': ['BC', 'BEN', 'CC', 'ULC', 'C', 'CBEN', 'CUL', 'CCC'],
                        'blockerChecks': {
                            'business': [BusinessBlocker.BUSINESS_FROZEN],
                            'futureEffectiveFilings': [CoreFiling.FilingTypes.INCORPORATIONAPPLICATION.value]
                        }
                    }
                }
            },
            Business.State.HISTORICAL: {}
        }
    }


# pylint: disable=(too-many-arguments,too-many-locals
def is_allowed(business: Business,
               state: Business.State,
               filing_type: str,
               legal_type: str,
               jwt: JwtManager,
               sub_filing_type: str = None,
               filing: Filing = None):
    """Is allowed to do filing."""
    is_ignore_draft_blockers = False

    if filing:
        if filing.status not in [Filing.Status.DRAFT.value,
                                 Filing.Status.CHANGE_REQUESTED.value,
                                 Filing.Status.APPROVED.value]:
            return False  # common for all filings
        else:
            is_ignore_draft_blockers = True

    # Special case: handling authorization for amalgamation application
    # this check is to make sure that amalgamation application is not allowed/authorized with continue in corps
    if filing_type == 'amalgamationApplication' and legal_type in ['C', 'CBEN', 'CUL', 'CCC']:
        return False

    allowable_filings = get_allowed_filings(business, state, legal_type, jwt, is_ignore_draft_blockers)

    for allowable_filing in allowable_filings:
        if allowable_filing['name'] == filing_type:
            if not sub_filing_type or allowable_filing['type'] == sub_filing_type:
                return True

    return False


def get_could_files(jwt: JwtManager, business_type: str, business_state: str):
    """Get allowable actions."""
    if is_competent_authority(jwt):
        allowed_filings = []
    else:
        allowed_filings = get_could_file(business_type, business_state, jwt)

    result = {
        'filing': {
            'filingTypes': allowed_filings
        }
    }
    return result


def get_allowable_actions(jwt: JwtManager, business: Business):
    """Get allowable actions."""
    if is_competent_authority(jwt):
        allowed_filings = []
    else:
        allowed_filings = get_allowed_filings(business, business.state, business.legal_type, jwt)

    base_url = current_app.config.get('LEGAL_API_BASE_URL')
    filing_submission_url = urljoin(base_url, f'{business.identifier}/filings')

    result = {
        'filing': {
            'filingSubmissionLink': filing_submission_url,
            'filingTypes': allowed_filings
        },
        'digitalBusinessCard': are_digital_credentials_allowed(business, jwt),
        'digitalBusinessCardPreconditions': get_digital_credentials_preconditions(business, jwt),
        'viewAll': is_competent_authority(jwt)
    }
    return result


def get_could_file(legal_type: str,
                   state: str,
                   jwt: JwtManager):
    """Get allowed type of filing types for the current user."""
    # importing here to avoid circular dependencies
    # pylint: disable=import-outside-toplevel
    from legal_api.core.meta import FilingMeta

    user_role = 'general'
    if jwt.contains_role([STAFF_ROLE, SYSTEM_ROLE, COLIN_SVC_ROLE]):
        user_role = 'staff'

    bs_state = getattr(Business.State, state, '')

    allowable_filings = get_allowable_filings_dict().get(user_role, {}).get(bs_state, {})
    could_filing_types = []

    for allowable_filing_key, allowable_filing_value in allowable_filings.items():
        allowable_filing_legal_types = allowable_filing_value.get('legalTypes', [])

        if allowable_filing_legal_types:
            is_allowable = legal_type in allowable_filing_legal_types
            allowable_filing_type = {'name': allowable_filing_key,
                                     'displayName': FilingMeta.get_display_name(legal_type, allowable_filing_key)}
            could_filing_types = add_allowable_filing_type(is_allowable,
                                                           could_filing_types,
                                                           allowable_filing_type)
            continue

        filing_sub_type_items = \
            filter(lambda x: isinstance(x[1], dict) and legal_type in
                   x[1].get('legalTypes', []), allowable_filing_value.items())

        for filing_sub_type_item_key, _ in filing_sub_type_items:

            allowable_filing_sub_type = {'name': allowable_filing_key,
                                         'type': filing_sub_type_item_key,
                                         'displayName': FilingMeta.get_display_name(legal_type,
                                                                                    allowable_filing_key,
                                                                                    filing_sub_type_item_key)}
            could_filing_types = add_allowable_filing_type(True,
                                                           could_filing_types,
                                                           allowable_filing_sub_type)

    return could_filing_types


def get_allowed_filings(business: Business,
                        state: Business.State,
                        legal_type: str,
                        jwt: JwtManager,
                        is_ignore_draft_blockers: bool = False):
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
    business_blocker_dict: dict = business_blocker_check(business, is_ignore_draft_blockers)
    allowable_filings = get_allowable_filings_dict().get(user_role, {}).get(state, {})
    allowable_filing_types = []

    for allowable_filing_key, allowable_filing_value in allowable_filings.items():
        # skip if business does not exist and filing is not required
        # skip if this filing does not need to be returned for existing businesses

        business_status = allowable_filing_value.get('businessRequirement', BusinessRequirement.EXIST)

        if business_status != BusinessRequirement.NO_RESTRICTION and \
                bool(business) ^ (business_status == BusinessRequirement.EXIST):
            continue

        allowable_filing_legal_types = allowable_filing_value.get('legalTypes', [])

        if allowable_filing_legal_types:
            is_blocker = has_blocker(business, state_filing, allowable_filing_value, business_blocker_dict)
            is_include_legal_type = legal_type in allowable_filing_legal_types
            is_allowable = not is_blocker and is_include_legal_type
            allowable_filing_type = {'name': allowable_filing_key,
                                     'displayName': FilingMeta.get_display_name(legal_type, allowable_filing_key),
                                     'feeCode': Filing.get_fee_code(legal_type, allowable_filing_key)}
            allowable_filing_types = add_allowable_filing_type(is_allowable,
                                                               allowable_filing_types,
                                                               allowable_filing_type)
            continue

        filing_sub_type_items = \
            filter(lambda x: isinstance(x[1], dict) and legal_type in
                   x[1].get('legalTypes', []), allowable_filing_value.items())

        for filing_sub_type_item_key, filing_sub_type_item_value in filing_sub_type_items:
            is_allowable = not has_blocker(business, state_filing, filing_sub_type_item_value, business_blocker_dict)

            allowable_filing_sub_type = {'name': allowable_filing_key,
                                         'type': filing_sub_type_item_key,
                                         'displayName': FilingMeta.get_display_name(legal_type,
                                                                                    allowable_filing_key,
                                                                                    filing_sub_type_item_key),
                                         'feeCode': Filing.get_fee_code(legal_type,
                                                                        allowable_filing_key,
                                                                        filing_sub_type_item_key)}
            allowable_filing_types = add_allowable_filing_type(is_allowable,
                                                               allowable_filing_types,
                                                               allowable_filing_sub_type)

    return allowable_filing_types


def has_blocker(business: Business, state_filing: Filing, allowable_filing: dict, business_blocker_dict: dict):
    """Return True if allowable filing has a blocker."""
    if not business:
        return False

    if not (blocker_checks := allowable_filing.get('blockerChecks', {})):
        return False

    if has_business_blocker(blocker_checks, business_blocker_dict):
        return True

    if has_blocker_valid_state_filing(state_filing, blocker_checks):
        return True

    if has_blocker_invalid_state_filing(state_filing, blocker_checks):
        return True

    if has_blocker_completed_filing(business, blocker_checks):
        return True

    if has_blocker_future_effective_filing(business, blocker_checks):
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


def business_blocker_check(business: Business, is_ignore_draft_blockers: bool = False):
    """Return True if the business has a default blocker condition."""
    business_blocker_checks: dict = {
        BusinessBlocker.DEFAULT: False,
        BusinessBlocker.BUSINESS_FROZEN: False,
        BusinessBlocker.DRAFT_PENDING: False,
        BusinessBlocker.NOT_IN_GOOD_STANDING: False,
        BusinessBlocker.AMALGAMATING_BUSINESS: False,
        BusinessBlocker.IN_DISSOLUTION: False,
        BusinessBlocker.FILING_WITHDRAWAL: False
    }

    if not business:
        return business_blocker_checks

    if has_blocker_filing(business, is_ignore_draft_blockers):
        business_blocker_checks[BusinessBlocker.DRAFT_PENDING] = True
        business_blocker_checks[BusinessBlocker.DEFAULT] = True

    if business.admin_freeze:
        business_blocker_checks[BusinessBlocker.BUSINESS_FROZEN] = True
        business_blocker_checks[BusinessBlocker.DEFAULT] = True

    if not business.good_standing:
        business_blocker_checks[BusinessBlocker.NOT_IN_GOOD_STANDING] = True

    if business.get_amalgamated_into():
        business_blocker_checks[BusinessBlocker.AMALGAMATING_BUSINESS] = True

    if business.in_dissolution:
        business_blocker_checks[BusinessBlocker.IN_DISSOLUTION] = True

    if has_notice_of_withdrawal_filing_blocker(business, is_ignore_draft_blockers):
        business_blocker_checks[BusinessBlocker.FILING_WITHDRAWAL] = True

    return business_blocker_checks


def has_blocker_filing(business: Business, is_ignore_draft_blockers: bool = False):
    """Check if there are any incomplete states filings. This is a blocker because it needs to be completed first."""
    # importing here to avoid circular dependencies
    # pylint: disable=import-outside-toplevel
    from legal_api.core.filing import Filing as CoreFiling

    filing_statuses = [Filing.Status.PENDING.value,
                       Filing.Status.PENDING_CORRECTION.value,
                       Filing.Status.ERROR.value,
                       Filing.Status.PAID.value]
    if not is_ignore_draft_blockers:
        filing_statuses.extend([Filing.Status.DRAFT.value,
                                Filing.Status.AWAITING_REVIEW.value,
                                Filing.Status.CHANGE_REQUESTED.value,
                                Filing.Status.APPROVED.value])
    blocker_filing_matches = Filing.get_filings_by_status(business.id, filing_statuses)
    if any(blocker_filing_matches):
        return True

    filing_types = [CoreFiling.FilingTypes.ALTERATION.value, CoreFiling.FilingTypes.CORRECTION.value]
    excluded_statuses = [Filing.Status.DRAFT.value] if is_ignore_draft_blockers else []
    blocker_filing_matches = Filing.get_incomplete_filings_by_types(business.id, filing_types, excluded_statuses)
    return any(blocker_filing_matches)


def has_blocker_valid_state_filing(state_filing: Filing, blocker_checks: dict):
    """Check if there is a required state filing that business does not have."""
    if not (state_filing_types := blocker_checks.get('validStateFilings', [])):
        return False

    if not state_filing:
        return True

    return not has_filing_match(state_filing, state_filing_types)


def has_blocker_invalid_state_filing(state_filing: Filing, blocker_checks: dict):
    """Check if business has an invalid state filing."""
    if not (state_filing_types := blocker_checks.get('invalidStateFilings', [])):
        return False

    if not state_filing:
        return False

    return has_filing_match(state_filing, state_filing_types)


def has_blocker_completed_filing(business: Business, blocker_checks: dict):
    """Check if business has an completed filing."""
    if not (complete_filing_types := blocker_checks.get('completedFilings', [])):
        return False

    filing_type_pairs = [(parse_filing_info(x)) for x in complete_filing_types]
    completed_filings = Filing.get_filings_by_type_pairs(business.id,
                                                         filing_type_pairs,
                                                         [Filing.Status.COMPLETED.value],
                                                         True)

    if len(completed_filings) == len(complete_filing_types):
        return False

    return True


def has_blocker_future_effective_filing(business: Business, blocker_checks: dict):
    """Check if business has a future effective filing."""
    if not (fed_filing_types := blocker_checks.get('futureEffectiveFilings', [])):
        return False

    filing_type_pairs = [(parse_filing_info(x)) for x in fed_filing_types]

    pending_filings = Filing.get_filings_by_type_pairs(business.id,
                                                       filing_type_pairs,
                                                       [Filing.Status.PENDING.value, Filing.Status.PAID.value],
                                                       True)

    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    is_fed = any(f.effective_date > now for f in pending_filings)

    return is_fed


def has_filing_match(filing: Filing, filing_types: list):
    """Return if filing matches any filings provided in filing_types arg ."""
    for filing_type in filing_types:
        filing_type, filing_sub_type = parse_filing_info(filing_type)
        if is_filing_type_match(filing, filing_type, filing_sub_type):
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


def has_notice_of_withdrawal_filing_blocker(business: Business, is_ignore_draft_blockers: bool = False):
    """Check if there are any blockers specific to Notice of Withdrawal."""
    if business.admin_freeze:
        return True

    filing_statuses = [Filing.Status.PENDING.value,
                       Filing.Status.PENDING_CORRECTION.value,
                       Filing.Status.ERROR.value]
    if not is_ignore_draft_blockers:
        filing_statuses.append(Filing.Status.DRAFT.value)
    blocker_filing_matches = Filing.get_filings_by_status(business.id, filing_statuses)
    if any(blocker_filing_matches):
        return True

    now = datetime.now(timezone.utc)
    paid_filings = Filing.get_filings_by_status(business.id, [Filing.Status.PAID.value])
    return not any(f.effective_date and f.effective_date > now for f in paid_filings)


def get_allowed(state: Business.State, legal_type: str, jwt: JwtManager):
    """Get allowed type of filing types for the current user."""
    user_role = 'general'
    if jwt.contains_role([STAFF_ROLE, SYSTEM_ROLE, COLIN_SVC_ROLE]):
        user_role = 'staff'

    allowable_filings = get_allowable_filings_dict().get(user_role, {}).get(state, {})
    allowable_filing_types = []
    for allowable_filing_key, allowable_filing_value in allowable_filings.items():
        if legal_types := allowable_filing_value.get('legalTypes', None):
            if legal_type in legal_types:
                allowable_filing_types.append(allowable_filing_key)
        else:
            sub_filing_types = [x for x in allowable_filing_value.items()
                                if isinstance(x[1], dict) and legal_type in x[1].get('legalTypes')]
            if sub_filing_types:
                allowable_filing_types.append({
                    allowable_filing_key: [sub_filing_type[0] for sub_filing_type in sub_filing_types]
                })

    return allowable_filing_types


def add_allowable_filing_type(is_allowable: bool = False,
                              allowable_filing_types: list = None,
                              allowable_filing_type: dict = None):
    """Append allowable filing type."""
    if is_allowable:
        allowable_filing_types.append(allowable_filing_type)

    return allowable_filing_types


def get_account_id(_, account_id: str = None) -> str:
    """Return the account id."""
    return account_id or request.headers.get('Account-Id', None)


@cache.cached(timeout=600, make_cache_key=get_account_id, cache_none=True)
def get_account_products(token: str, account_id: str = None) -> list:
    """Return the account products of the org identified by the account id."""
    account_id = account_id or request.headers.get('Account-Id', None)
    resp = _call_auth_api(f'orgs/{account_id}/products?include_hidden=true', token)
    if not resp or resp.status_code != HTTPStatus.OK or not isinstance(resp.json(), list):
        return None
    return resp.json()


def has_product(code: str, token: str) -> bool:
    """Return if the user has the active product subscription for the given code."""
    user_products = get_account_products(token)
    if not user_products or not isinstance(user_products, list):
        return False

    return any(p['code'] == code and p['subscriptionStatus'] == 'ACTIVE' for p in user_products)

def is_competent_authority(jwt: JwtManager) -> bool:
    """Return if the user has the active ca_search subscription."""
    return has_product('CA_SEARCH', jwt.get_token_auth_header())
