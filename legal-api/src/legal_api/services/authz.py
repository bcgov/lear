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
from datetime import datetime, timezone
from enum import Enum
from http import HTTPStatus
from typing import List
from urllib.parse import urljoin

import jwt as pyjwt
import requests
from flask import current_app
from flask_jwt_oidc import JwtManager
from requests import Session, exceptions
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from legal_api.exceptions import ApiConnectionException
from legal_api.models import EntityRole, Filing, LegalEntity, User
from legal_api.models.business_common import BusinessCommon
from legal_api.services.warnings.business.business_checks import WarningType

ACCOUNT_IDENTITY = "account_identity"
BASIC_USER = "basic"
BCOL_HELP = "helpdesk"
COLIN_ROLE = "colin"
COLIN_SVC_ROLE = "colin"
GOV_ACCOUNT_ROLE = "gov_account_user"
PPR_ROLE = "ppr"
PRO_DATA_USER = "pro_data"
PUBLIC_USER = "public_user"
SBC_STAFF = "sbc_staff"
STAFF_ROLE = "staff"
SYSTEM_ROLE = "system"


class BusinessBlocker(str, Enum):
    """Define an enum for business level blocker checks."""

    # Currently DEFAULT encapsulates a bunch of business level blocker checks
    # to make it easier to check if a business is blocked.  If there is ever a need to be more granular,
    # the individual checks within DEFAULT could be added as an individual enum item.
    DEFAULT = "DEFAULT"
    BUSINESS_FROZEN = "BUSINESS_FROZEN"
    DRAFT_PENDING = "DRAFT_PENDING"
    NOT_IN_GOOD_STANDING = "NOT_IN_GOOD_STANDING"


class BusinessRequirement(str, Enum):
    """Define an enum for business requirement scenarios."""

    EXIST = "EXIST"
    NOT_EXIST = "NOT_EXIST"
    NO_RESTRICTION = "NO_RESTRICTION"


def authorized(  # pylint: disable=too-many-return-statements
    identifier: str, jwt: JwtManager, action: List[str]
) -> bool:
    """Assert that the user is authorized to create filings against the business identifier."""
    # if they are registry staff, they are always authorized
    if not action or not identifier or not jwt:
        return False

    if jwt.validate_roles([STAFF_ROLE]) or jwt.validate_roles([SYSTEM_ROLE]) or jwt.validate_roles([COLIN_SVC_ROLE]):
        return True

    # allow IDIM view access on everything
    if len(action) == 1 and action[0] == "view" and jwt.validate_roles([ACCOUNT_IDENTITY]):
        return True

    if jwt.has_one_of_roles([BASIC_USER, PUBLIC_USER]):
        # disallow - only staff are allowed
        staff_only_actions = ["add_comment"]
        if any(elem in action for elem in staff_only_actions):
            return False

        template_url = current_app.config.get("AUTH_SVC_URL")
        auth_url = f"{template_url}/entities/{identifier}/authorizations"

        token = jwt.get_token_auth_header()
        headers = {"Authorization": "Bearer " + token}
        try:
            http = Session()
            retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
            http.mount("http://", HTTPAdapter(max_retries=retries))
            rv = http.get(url=auth_url, headers=headers)

            if rv.status_code != HTTPStatus.OK or not rv.json().get("roles"):
                return False

            if all(elem.lower() in rv.json().get("roles") for elem in action):
                return True

        except (
            exceptions.ConnectionError,  # pylint: disable=broad-except
            exceptions.Timeout,
            ValueError,
            Exception,
        ) as err:
            current_app.logger.error(f"template_url {template_url}, svc:{auth_url}")
            current_app.logger.error(f"Authorization connection failure for {identifier}, using svc:{auth_url}, {err}")
            return False

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
        "staff": {
            BusinessCommon.State.ACTIVE: {
                "adminFreeze": {
                    "legalTypes": ["SP", "GP", "CP", "BC", "BEN", "CC", "ULC"],
                },
                "agmExtension": {
                    "legalTypes": ["BC", "BEN", "ULC", "CC"],
                    "blockerChecks": {"business": [BusinessBlocker.DEFAULT, BusinessBlocker.NOT_IN_GOOD_STANDING]},
                },
                "agmLocationChange": {
                    "legalTypes": ["BC", "BEN", "ULC", "CC"],
                    "blockerChecks": {"business": [BusinessBlocker.DEFAULT, BusinessBlocker.NOT_IN_GOOD_STANDING]},
                },
                "alteration": {
                    "legalTypes": ["BC", "BEN", "ULC", "CC"],
                    "blockerChecks": {"business": [BusinessBlocker.DEFAULT]},
                },
                "amalgamationApplication": {
                    "businessRequirement": BusinessRequirement.NO_RESTRICTION,
                    "regular": {
                        "legalTypes": ["BEN", "BC", "ULC", "CC"],
                        "blockerChecks": {
                            "business": [BusinessBlocker.BUSINESS_FROZEN],
                            "futureEffectiveFilings": [
                                filing_types_compact.DISSOLUTION_VOLUNTARY,
                                filing_types_compact.DISSOLUTION_ADMINISTRATIVE,
                            ],
                        },
                    },
                    "vertical": {
                        "legalTypes": ["BEN", "BC", "ULC", "CC"],
                        "blockerChecks": {
                            "business": [BusinessBlocker.BUSINESS_FROZEN],
                            "futureEffectiveFilings": [
                                filing_types_compact.DISSOLUTION_VOLUNTARY,
                                filing_types_compact.DISSOLUTION_ADMINISTRATIVE,
                            ],
                        },
                    },
                    "horizontal": {
                        "legalTypes": ["BEN", "BC", "ULC", "CC"],
                        "blockerChecks": {
                            "business": [BusinessBlocker.BUSINESS_FROZEN],
                            "futureEffectiveFilings": [
                                filing_types_compact.DISSOLUTION_VOLUNTARY,
                                filing_types_compact.DISSOLUTION_ADMINISTRATIVE,
                            ],
                        },
                    },
                },
                "annualReport": {
                    "legalTypes": ["CP", "BEN", "BC", "ULC", "CC"],
                    "blockerChecks": {"business": [BusinessBlocker.DEFAULT]},
                },
                "changeOfAddress": {
                    "legalTypes": ["CP", "BEN", "BC", "ULC", "CC"],
                    "blockerChecks": {"business": [BusinessBlocker.DEFAULT]},
                },
                "changeOfDirectors": {
                    "legalTypes": ["CP", "BEN", "BC", "ULC", "CC"],
                    "blockerChecks": {"business": [BusinessBlocker.DEFAULT]},
                },
                "changeOfRegistration": {
                    "legalTypes": ["SP", "GP"],
                    "blockerChecks": {
                        "warningTypes": [WarningType.MISSING_REQUIRED_BUSINESS_INFO],
                        "business": [BusinessBlocker.DEFAULT],
                    },
                },
                "consentContinuationOut": {
                    "legalTypes": ["BC", "BEN", "CC", "ULC"],
                    "blockerChecks": {"business": [BusinessBlocker.DEFAULT, BusinessBlocker.NOT_IN_GOOD_STANDING]},
                },
                "continuationOut": {
                    "legalTypes": ["BC", "BEN", "CC", "ULC"],
                    "blockerChecks": {
                        "business": [BusinessBlocker.NOT_IN_GOOD_STANDING],
                        "completedFilings": ["consentContinuationOut"],
                    },
                },
                "conversion": {"legalTypes": ["SP", "GP"]},
                "correction": {
                    "legalTypes": ["CP", "BEN", "SP", "GP", "BC", "ULC", "CC"],
                    "blockerChecks": {
                        "warningTypes": [WarningType.MISSING_REQUIRED_BUSINESS_INFO],
                        "business": [BusinessBlocker.DEFAULT],
                    },
                },
                "courtOrder": {"legalTypes": ["SP", "GP", "CP", "BC", "BEN", "CC", "ULC"]},
                "dissolution": {
                    "voluntary": {
                        "legalTypes": ["CP", "BC", "BEN", "CC", "ULC", "SP", "GP"],
                        "blockerChecks": {
                            "warningTypes": [WarningType.MISSING_REQUIRED_BUSINESS_INFO],
                            "business": [BusinessBlocker.DEFAULT, BusinessBlocker.NOT_IN_GOOD_STANDING],
                        },
                    },
                    "administrative": {
                        "legalTypes": ["CP", "BC", "BEN", "CC", "ULC", "SP", "GP"],
                        "blockerChecks": {
                            "warningTypes": [WarningType.MISSING_REQUIRED_BUSINESS_INFO],
                            "business": [BusinessBlocker.DRAFT_PENDING],
                        },
                    },
                },
                "incorporationApplication": {
                    "legalTypes": ["CP", "BC", "BEN", "ULC", "CC"],
                    # only show filing when providing allowable filings not specific to a business
                    "businessRequirement": BusinessRequirement.NOT_EXIST,
                },
                "registrarsNotation": {"legalTypes": ["SP", "GP", "CP", "BC", "BEN", "CC", "ULC"]},
                "registrarsOrder": {"legalTypes": ["SP", "GP", "CP", "BC", "BEN", "CC", "ULC"]},
                "registration": {
                    "legalTypes": ["SP", "GP"],
                    # only show filing when providing allowable filings not specific to a business
                    "businessRequirement": BusinessRequirement.NOT_EXIST,
                },
                "specialResolution": {"legalTypes": ["CP"], "blockerChecks": {"business": [BusinessBlocker.DEFAULT]}},
                "transition": {"legalTypes": ["BC", "BEN", "CC", "ULC"]},
                "restoration": {
                    "limitedRestorationExtension": {
                        "legalTypes": ["BC", "BEN", "CC", "ULC"],
                        "blockerChecks": {
                            "validStateFilings": [
                                filing_types_compact.RESTORATION_LIMITED_RESTORATION,
                                filing_types_compact.RESTORATION_LIMITED_RESTORATION_EXT,
                            ],
                            "business": [BusinessBlocker.DEFAULT],
                        },
                    },
                    "limitedRestorationToFull": {
                        "legalTypes": ["BC", "BEN", "CC", "ULC"],
                        "blockerChecks": {
                            "validStateFilings": [
                                filing_types_compact.RESTORATION_LIMITED_RESTORATION,
                                filing_types_compact.RESTORATION_LIMITED_RESTORATION_EXT,
                            ],
                            "business": [BusinessBlocker.DEFAULT],
                        },
                    },
                },
            },
            BusinessCommon.State.HISTORICAL: {
                "courtOrder": {
                    "legalTypes": ["SP", "GP", "CP", "BC", "BEN", "CC", "ULC"],
                },
                "putBackOn": {
                    "legalTypes": ["SP", "GP", "BEN", "CP", "BC", "CC", "ULC"],
                    "blockerChecks": {"validStateFilings": [filing_types_compact.DISSOLUTION_ADMINISTRATIVE]},
                },
                "registrarsNotation": {"legalTypes": ["SP", "GP", "CP", "BC", "BEN", "CC", "ULC"]},
                "registrarsOrder": {"legalTypes": ["SP", "GP", "CP", "BC", "BEN", "CC", "ULC"]},
                "restoration": {
                    "fullRestoration": {
                        "legalTypes": ["BC", "BEN", "CC", "ULC"],
                        "blockerChecks": {"invalidStateFilings": ["continuationIn", "continuationOut"]},
                    },
                    "limitedRestoration": {
                        "legalTypes": ["BC", "BEN", "CC", "ULC"],
                        "blockerChecks": {"invalidStateFilings": ["continuationIn", "continuationOut"]},
                    },
                },
            },
        },
        "general": {
            BusinessCommon.State.ACTIVE: {
                "agmExtension": {
                    "legalTypes": ["BC", "BEN", "ULC", "CC"],
                    "blockerChecks": {"business": [BusinessBlocker.DEFAULT, BusinessBlocker.NOT_IN_GOOD_STANDING]},
                },
                "agmLocationChange": {
                    "legalTypes": ["BC", "BEN", "ULC", "CC"],
                    "blockerChecks": {"business": [BusinessBlocker.DEFAULT, BusinessBlocker.NOT_IN_GOOD_STANDING]},
                },
                "alteration": {
                    "legalTypes": ["BC", "BEN", "ULC", "CC"],
                    "blockerChecks": {"business": [BusinessBlocker.DEFAULT]},
                },
                "amalgamationApplication": {
                    "businessRequirement": BusinessRequirement.NO_RESTRICTION,
                    "regular": {
                        "legalTypes": ["BEN", "BC", "ULC", "CC"],
                        "blockerChecks": {
                            "business": [BusinessBlocker.BUSINESS_FROZEN],
                            "futureEffectiveFilings": [
                                filing_types_compact.DISSOLUTION_VOLUNTARY,
                                filing_types_compact.DISSOLUTION_ADMINISTRATIVE,
                            ],
                        },
                    },
                    "vertical": {
                        "legalTypes": ["BEN", "BC", "ULC", "CC"],
                        "blockerChecks": {
                            "business": [BusinessBlocker.BUSINESS_FROZEN],
                            "futureEffectiveFilings": [
                                filing_types_compact.DISSOLUTION_VOLUNTARY,
                                filing_types_compact.DISSOLUTION_ADMINISTRATIVE,
                            ],
                        },
                    },
                    "horizontal": {
                        "legalTypes": ["BEN", "BC", "ULC", "CC"],
                        "blockerChecks": {
                            "business": [BusinessBlocker.BUSINESS_FROZEN],
                            "futureEffectiveFilings": [
                                filing_types_compact.DISSOLUTION_VOLUNTARY,
                                filing_types_compact.DISSOLUTION_ADMINISTRATIVE,
                            ],
                        },
                    },
                },
                "annualReport": {
                    "legalTypes": ["CP", "BEN", "BC", "ULC", "CC"],
                    "blockerChecks": {"business": [BusinessBlocker.DEFAULT]},
                },
                "changeOfAddress": {
                    "legalTypes": ["CP", "BEN", "BC", "ULC", "CC"],
                    "blockerChecks": {
                        "business": [BusinessBlocker.DEFAULT],
                    },
                },
                "changeOfDirectors": {
                    "legalTypes": ["CP", "BEN", "BC", "ULC", "CC"],
                    "blockerChecks": {"business": [BusinessBlocker.DEFAULT]},
                },
                "changeOfRegistration": {
                    "legalTypes": ["SP", "GP"],
                    "blockerChecks": {
                        "warningTypes": [WarningType.MISSING_REQUIRED_BUSINESS_INFO],
                        "business": [BusinessBlocker.DEFAULT],
                    },
                },
                "consentContinuationOut": {
                    "legalTypes": ["BC", "BEN", "CC", "ULC"],
                    "blockerChecks": {"business": [BusinessBlocker.DEFAULT, BusinessBlocker.NOT_IN_GOOD_STANDING]},
                },
                "dissolution": {
                    "voluntary": {
                        "legalTypes": ["CP", "BC", "BEN", "CC", "ULC", "SP", "GP"],
                        "blockerChecks": {
                            "warningTypes": [WarningType.MISSING_REQUIRED_BUSINESS_INFO],
                            "business": [BusinessBlocker.DEFAULT, BusinessBlocker.NOT_IN_GOOD_STANDING],
                        },
                    },
                },
                "incorporationApplication": {
                    "legalTypes": ["CP", "BC", "BEN", "ULC", "CC"],
                    # only show filing when providing allowable filings not specific to a business
                    "businessRequirement": BusinessRequirement.NOT_EXIST,
                },
                "registration": {
                    "legalTypes": ["SP", "GP"],
                    # only show filing when providing allowable filings not specific to a business
                    "businessRequirement": BusinessRequirement.NOT_EXIST,
                },
                "specialResolution": {"legalTypes": ["CP"], "blockerChecks": {"business": [BusinessBlocker.DEFAULT]}},
                "transition": {"legalTypes": ["BC", "BEN", "CC", "ULC"]},
            },
            BusinessCommon.State.HISTORICAL: {},
        },
    }


# pylint: disable=(too-many-arguments,too-many-locals
def is_allowed(
    legal_entity: LegalEntity,
    state: LegalEntity.State,
    filing_type: str,
    legal_type: str,
    jwt: JwtManager,
    sub_filing_type: str = None,
    filing_id: int = None,
):
    """Is allowed to do filing."""
    is_ignore_draft_blockers = False

    if filing_id:
        filing = Filing.find_by_id(filing_id)
        if filing and filing.status == Filing.Status.DRAFT.value:
            is_ignore_draft_blockers = True

    allowable_filings = get_allowed_filings(legal_entity, state, legal_type, jwt, is_ignore_draft_blockers)

    for allowable_filing in allowable_filings:
        if allowable_filing["name"] == filing_type:
            if not sub_filing_type or allowable_filing["type"] == sub_filing_type:
                return True

    return False


def get_allowable_actions(jwt: JwtManager, business: any):
    """Get allowable actions."""
    base_url = current_app.config.get("LEGAL_API_BASE_URL")
    allowed_filings = get_allowed_filings(business, business.state, business.entity_type, jwt)
    filing_submission_url = urljoin(base_url, f"{business.identifier}/filings")
    result = {
        "filing": {"filingSubmissionLink": filing_submission_url, "filingTypes": allowed_filings},
        "digitalBusinessCard": are_digital_credentials_allowed(business, jwt),
    }
    return result


def get_allowed_filings(
    business: any,
    state: BusinessCommon.State,
    entity_type: str,
    jwt: JwtManager,
    is_ignore_draft_blockers: bool = False,
):
    """Get allowed type of filing types for the current user."""
    # importing here to avoid circular dependencies
    # pylint: disable=import-outside-toplevel
    from legal_api.core.meta import FilingMeta

    user_role = "general"
    if jwt.contains_role([STAFF_ROLE, SYSTEM_ROLE, COLIN_SVC_ROLE]):
        user_role = "staff"

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

        business_status = allowable_filing_value.get("businessRequirement", BusinessRequirement.EXIST)

        if business_status != BusinessRequirement.NO_RESTRICTION and bool(business) ^ (
            business_status == BusinessRequirement.EXIST
        ):
            continue

        allowable_filing_legal_types = allowable_filing_value.get("legalTypes", [])

        if allowable_filing_legal_types:
            is_blocker = has_blocker(business, state_filing, allowable_filing_value, business_blocker_dict)
            is_include_legal_type = entity_type in allowable_filing_legal_types
            is_allowable = not is_blocker and is_include_legal_type
            allowable_filing_type = {
                "name": allowable_filing_key,
                "displayName": FilingMeta.get_display_name(entity_type, allowable_filing_key),
                "feeCode": Filing.get_fee_code(entity_type, allowable_filing_key),
            }
            allowable_filing_types = add_allowable_filing_type(
                is_allowable, allowable_filing_types, allowable_filing_type
            )
            continue

        filing_sub_type_items = filter(
            lambda x: isinstance(x[1], dict) and entity_type in x[1].get("legalTypes", []),
            allowable_filing_value.items(),
        )

        for filing_sub_type_item_key, filing_sub_type_item_value in filing_sub_type_items:
            is_allowable = not has_blocker(business, state_filing, filing_sub_type_item_value, business_blocker_dict)
            allowable_filing_sub_type = {
                "name": allowable_filing_key,
                "type": filing_sub_type_item_key,
                "displayName": FilingMeta.get_display_name(entity_type, allowable_filing_key, filing_sub_type_item_key),
                "feeCode": Filing.get_fee_code(entity_type, allowable_filing_key, filing_sub_type_item_key),
            }
            allowable_filing_types = add_allowable_filing_type(
                is_allowable, allowable_filing_types, allowable_filing_sub_type
            )

    return allowable_filing_types


def has_blocker(legal_entity: LegalEntity, state_filing: Filing, allowable_filing: dict, business_blocker_dict: dict):
    """Return True if allowable filing has a blocker."""
    if not legal_entity:
        return False

    if not (blocker_checks := allowable_filing.get("blockerChecks", {})):
        return False

    if has_business_blocker(blocker_checks, business_blocker_dict):
        return True

    if has_blocker_valid_state_filing(state_filing, blocker_checks):
        return True

    if has_blocker_invalid_state_filing(state_filing, blocker_checks):
        return True

    if has_blocker_completed_filing(legal_entity, blocker_checks):
        return True

    if has_blocker_future_effective_filing(legal_entity, blocker_checks):
        return True

    if has_blocker_warning_filing(legal_entity.warnings, blocker_checks):
        return True

    return False


def has_business_blocker(blocker_checks: dict, business_blocker_dict: dict):
    """Return True if the business has a default blocker."""
    if not (business_blocker_checks := blocker_checks.get("business", [])):
        return False

    for business_blocker_check_type in business_blocker_checks:
        if business_blocker_dict[business_blocker_check_type]:
            return True

    return False


def business_blocker_check(business: any, is_ignore_draft_blockers: bool = False):
    """Return True if the business has a default blocker condition."""
    business_blocker_checks: dict = {
        BusinessBlocker.DEFAULT: False,
        BusinessBlocker.BUSINESS_FROZEN: False,
        BusinessBlocker.DRAFT_PENDING: False,
        BusinessBlocker.NOT_IN_GOOD_STANDING: False,
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

    return business_blocker_checks


def has_blocker_filing(business: any, is_ignore_draft_blockers: bool = False):
    """Check if there are any incomplete states filings. This is a blocker because it needs to be completed first."""
    # importing here to avoid circular dependencies
    # pylint: disable=import-outside-toplevel
    from legal_api.core.filing import Filing as CoreFiling

    filing_statuses = [
        Filing.Status.PENDING.value,
        Filing.Status.PENDING_CORRECTION.value,
        Filing.Status.ERROR.value,
        Filing.Status.PAID.value,
    ]
    if not is_ignore_draft_blockers:
        filing_statuses.append(Filing.Status.DRAFT.value)
    blocker_filing_matches = Filing.get_filings_by_status(business, filing_statuses)
    if any(blocker_filing_matches):
        return True

    filing_types = [CoreFiling.FilingTypes.ALTERATION.value, CoreFiling.FilingTypes.CORRECTION.value]
    excluded_statuses = [Filing.Status.DRAFT.value] if is_ignore_draft_blockers else []
    blocker_filing_matches = Filing.get_incomplete_filings_by_types(business.id, filing_types, excluded_statuses)
    return any(blocker_filing_matches)


def has_blocker_valid_state_filing(state_filing: Filing, blocker_checks: dict):
    """Check if there is a required state filing that business does not have."""
    if not (state_filing_types := blocker_checks.get("validStateFilings", [])):
        return False

    if not state_filing:
        return True

    return not has_filing_match(state_filing, state_filing_types)


def has_blocker_invalid_state_filing(state_filing: Filing, blocker_checks: dict):
    """Check if business has an invalid state filing."""
    if not (state_filing_types := blocker_checks.get("invalidStateFilings", [])):
        return False

    if not state_filing:
        return False

    return has_filing_match(state_filing, state_filing_types)


def has_blocker_completed_filing(legal_entity: LegalEntity, blocker_checks: dict):
    """Check if business has an completed filing."""
    if not (complete_filing_types := blocker_checks.get("completedFilings", [])):
        return False

    filing_type_pairs = [(parse_filing_info(x)) for x in complete_filing_types]
    completed_filings = Filing.get_filings_by_type_pairs(
        legal_entity.id, filing_type_pairs, [Filing.Status.COMPLETED.value], True
    )

    if len(completed_filings) == len(complete_filing_types):
        return False

    return True


def has_blocker_future_effective_filing(legal_entity: LegalEntity, blocker_checks: dict):
    """Check if business has a future effective filing."""
    if not (fed_filing_types := blocker_checks.get("futureEffectiveFilings", [])):
        return False

    filing_type_pairs = [(parse_filing_info(x)) for x in fed_filing_types]

    pending_filings = Filing.get_filings_by_type_pairs(
        legal_entity.id, filing_type_pairs, [Filing.Status.PENDING.value, Filing.Status.PAID.value], True
    )

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
    filing_info = filing_info.split(".")
    filing_type = filing_info[0]
    filing_sub_type = filing_info[1] if len(filing_info) > 1 else None
    return filing_type, filing_sub_type


def has_blocker_warning_filing(warnings: List, blocker_checks: dict):
    """Return if business has a warning that blocks filing."""
    if not (blocker_warning_filings := blocker_checks.get("warningTypes", [])):
        return False

    warning_types = [x["warningType"] for x in warnings]
    # update to only keep unique warning types
    warning_types = list(set(warning_types))
    warning_matches = any(x for x in warning_types if x in blocker_warning_filings)
    return warning_matches


def get_allowed(state: LegalEntity.State, legal_type: str, jwt: JwtManager):
    """Get allowed type of filing types for the current user."""
    user_role = "general"
    if jwt.contains_role([STAFF_ROLE, SYSTEM_ROLE, COLIN_SVC_ROLE]):
        user_role = "staff"

    allowable_filings = get_allowable_filings_dict().get(user_role, {}).get(state, {})
    allowable_filing_types = []
    for allowable_filing_key, allowable_filing_value in allowable_filings.items():
        if legal_types := allowable_filing_value.get("legalTypes", None):
            if legal_type in legal_types:
                allowable_filing_types.append(allowable_filing_key)
        else:
            sub_filing_types = [
                x
                for x in allowable_filing_value.items()
                if isinstance(x[1], dict) and legal_type in x[1].get("legalTypes")
            ]
            if sub_filing_types:
                allowable_filing_types.append(
                    {allowable_filing_key: [sub_filing_type[0] for sub_filing_type in sub_filing_types]}
                )

    return allowable_filing_types


def get_account_by_affiliated_identifier(token, identifier: str):
    """Return the account affiliated to the LegalEntity."""
    auth_url = current_app.config.get("AUTH_SVC_URL")
    url = f"{auth_url}/orgs?affiliation={identifier}"

    headers = {"Authorization": f"Bearer {token}"}

    res = requests.get(url, headers=headers)
    try:
        return res.json()
    except Exception:  # noqa B902; pylint: disable=W0703;
        current_app.logger.error("Failed to get response")
        return None


def add_allowable_filing_type(
    is_allowable: bool = False, allowable_filing_types: list = None, allowable_filing_type: dict = None
):
    """Append allowable filing type."""
    if is_allowable:
        allowable_filing_types.append(allowable_filing_type)

    return allowable_filing_types


def _call_auth_api(path: str, token: str) -> dict:
    """Return the auth api response for the given endpoint path."""
    response = None
    if not token:
        return response

    service_url = current_app.config.get("AUTH_SVC_URL")
    api_url = service_url + "/" if service_url[-1] != "/" else service_url
    api_url += path

    try:
        headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
        # current_app.logger.debug('Auth get user orgs url=' + url)
        with Session() as http:
            retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
            http.mount("http://", HTTPAdapter(max_retries=retries))
            ret_val = http.get(url=api_url, headers=headers)
            current_app.logger.debug(f"Auth get {path} response status: {str(ret_val.status_code)}")
            response = ret_val.json()
    except (
        exceptions.ConnectionError,  # pylint: disable=broad-except
        exceptions.Timeout,
        ValueError,
        Exception,
    ) as err:
        current_app.logger.error(f"Auth api connection failure using svc:{api_url}", err)
    return response


def get_bearer_token():
    """Get a valid Bearer token for the service to use."""
    token_url = current_app.config.get("ACCOUNT_SVC_AUTH_URL")
    client_id = current_app.config.get("ACCOUNT_SVC_CLIENT_ID")
    client_secret = current_app.config.get("ACCOUNT_SVC_CLIENT_SECRET")
    auth_api_timeout = current_app.config.get("AUTH_API_TIMEOUT")

    data = "grant_type=client_credentials"

    # get service account token
    try:
        res = requests.post(
            url=token_url,
            data=data,
            headers={"content-type": "application/x-www-form-urlencoded"},
            auth=(client_id, client_secret),
            timeout=auth_api_timeout,
        )

        return res.json().get("access_token")
    except (exceptions.ConnectionError, exceptions.Timeout) as err:
        current_app.logger.error("AUTH connection failure:", err)
        raise ApiConnectionException(  # pylint: disable=raise-missing-from
            HTTPStatus.GATEWAY_TIMEOUT, [{"message": "Unable to get service account token from auth."}]
        )
    except Exception as err:  # noqa: B902
        current_app.logger.error("AUTH connection failure:", err)
        raise ApiConnectionException(  # pylint: disable=raise-missing-from
            HTTPStatus.INTERNAL_SERVER_ERROR, [{"message": "Unable to get service account token from auth."}]
        )


def user_info(token: str) -> dict:
    """Auth API call to get the stored user info."""
    return _call_auth_api("users/@me", token)


def user_orgs(token: str) -> dict:
    """Auth API call to get user organizations for the user identified by the token."""
    return _call_auth_api("users/orgs", token)


def account_org(token: str, account_id: str) -> dict:
    """Auth API call to get the account organization info identified by the account id."""
    if not account_id:
        return None
    return _call_auth_api(f"orgs/{account_id}", token)


def is_staff(jwt: JwtManager) -> bool:  # pylint: disable=too-many-return-statements
    """Return True if the user has the BC Registries staff role."""
    if not jwt:
        return False
    if jwt.validate_roles([STAFF_ROLE]):
        return True

    return False


def is_bcol_help(account_id: str) -> bool:
    """Return True if the account id is a bcol help account id."""
    return account_id is not None and account_id == BCOL_HELP


def is_staff_account(account_id: str) -> bool:
    """Return True if the account id is a registries staff or sbc office account id."""
    return account_id is not None and account_id == STAFF_ROLE


def is_reg_staff_account(account_id: str) -> bool:
    """Return True if the account id is a staff registries account id."""
    return account_id is not None and account_id == STAFF_ROLE


def is_sbc_office_account(token: str, account_id: str) -> bool:
    """Return True if the account id is an sbc office account id."""
    try:
        org_info = account_org(token, account_id)
        if org_info and "branchName" in org_info:
            return "Service BC" in org_info["branchName"]
        return None
    except Exception as err:  # pylint: disable=broad-except # noqa F841;
        current_app.logger.error("is_sbc_office_account failed: " + repr(err))
        return None


def is_gov_account(jwt: JwtManager) -> bool:  # pylint: disable=too-many-return-statements
    """Return True if the user has the gov account user role."""
    if not jwt:
        return False
    if jwt.validate_roles([GOV_ACCOUNT_ROLE]):
        return True

    return False


def is_all_staff_account(account_id: str) -> bool:
    """Return True if the account id is any staff role."""
    return account_id is not None and account_id in (STAFF_ROLE, BCOL_HELP)


def get_role(jwt: JwtManager, account_id) -> str:
    """Return the role."""
    role = BASIC_USER
    if is_staff(jwt):
        role = STAFF_ROLE
    elif is_gov_account(jwt) and is_sbc_office_account(jwt.get_token_auth_header(), account_id):
        role = SBC_STAFF

    return role


def are_digital_credentials_allowed(legal_entity: LegalEntity, jwt: JwtManager):
    """Return True if the business is allowed to have/view a digital business card."""
    if not (token := pyjwt.decode(jwt.get_token_auth_header(), options={"verify_signature": False})):
        return False

    if not (user := User.find_by_jwt_token(token)):
        return False

    is_staff = jwt.contains_role([STAFF_ROLE])  # pylint: disable=redefined-outer-name

    # TODO: cannot identify SOLE_PROP by checking legal_entity.entity_type
    is_sole_prop = legal_entity and legal_entity.entity_type == LegalEntity.EntityTypes.SOLE_PROP.value

    is_login_source_bcsc = user.login_source == "BCSC"

    is_owner_operator = is_self_registered_owner_operator(legal_entity, user)

    return is_login_source_bcsc and is_sole_prop and is_owner_operator and not is_staff


def is_self_registered_owner_operator(legal_entity, user):
    """Return True if the user is the owner operator of the LegalEntity."""
    if not (registration_filing := get_registration_filing(legal_entity)):
        return False

    if len(proprietors := EntityRole.get_parties_by_role(legal_entity.id, EntityRole.RoleTypes.proprietor)) <= 0:
        return False

    if (
        len(
            completing_parties := EntityRole.get_entity_roles_by_filing(
                registration_filing.id, datetime.utcnow(), EntityRole.RoleTypes.completing_party
            )
        )
        <= 0
    ):
        return False

    if not ((proprietor := proprietors[0].related_entity) and proprietor.is_related_person):
        return False

    if not (completing_party := completing_parties[0].related_entity):
        return False

    completing_party_first_name = (completing_party.first_name or "").lower()
    completing_party_last_name = (completing_party.last_name or "").lower()
    proprietor_first_name = (proprietor.first_name or "").lower()
    proprietor_middle_initial = (proprietor.middle_initial or "").lower()
    if proprietor_middle_initial:
        proprietor_first_name = f"{proprietor_first_name} {proprietor_middle_initial}"
    proprietor_last_name = (proprietor.last_name or "").lower()
    user_first_name = (user.firstname or "").lower()
    user_last_name = (user.lastname or "").lower()

    return (
        registration_filing.submitter_id == user.id
        and completing_party_first_name == proprietor_first_name
        and completing_party_last_name == proprietor_last_name
        and proprietor_first_name == user_first_name
        and proprietor_last_name == user_last_name
    )


def get_registration_filing(legal_entity):
    """Return the registration filing for the LegalEntity."""
    if len(registration_filings := Filing.get_filings_by_types(legal_entity.id, ["registration"])) <= 0:
        return None

    return registration_filings[0]
