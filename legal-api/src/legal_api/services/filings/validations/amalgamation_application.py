# Copyright © 2023 Province of British Columbia
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
"""Validation for the Amalgamation Application filing."""
from http import HTTPStatus
from typing import Dict, Final, Optional

from flask_babel import _ as babel  # noqa: N813, I004, I001; importing camelcase '_' as a name
from legal_api.errors import Error
from legal_api.models import AmalgamatingBusiness, Amalgamation, Business, Filing, PartyRole
from legal_api.services import STAFF_ROLE
from legal_api.services.bootstrap import AccountService
from legal_api.services.filings.validations.common_validations import (
    validate_court_order,
    validate_foreign_jurisdiction,
    validate_name_request,
    validate_parties_names,
    validate_share_structure,
)
from legal_api.services.filings.validations.incorporation_application import validate_offices
from legal_api.services.utils import get_str
from legal_api.utils.auth import jwt
# noqa: I003


def validate(amalgamation_json: Dict, account_id) -> Optional[Error]:
    """Validate the Amalgamation Application filing."""
    filing_type = 'amalgamationApplication'
    if not amalgamation_json:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid filing is required.')}])
    msg = []

    legal_type_path = f'/filing/{filing_type}/nameRequest/legalType'
    legal_type = get_str(amalgamation_json, legal_type_path)
    if not legal_type:
        msg.append({'error': babel('Legal type is required.'), 'path': legal_type_path})
        return msg  # Cannot continue validation without legal_type

    amalgamation_type = get_str(amalgamation_json, f'/filing/{filing_type}/type')

    if amalgamation_json.get('filing', {}).get(filing_type, {}).get('nameRequest', {}).get('nrNumber', None):
        # Adopt from one of the amalgamating businesses contains name not nrNumber
        msg.extend(validate_name_request(amalgamation_json, legal_type, filing_type))

    msg.extend(validate_party(amalgamation_json, amalgamation_type, filing_type))
    msg.extend(validate_parties_names(amalgamation_json, filing_type))

    if amalgamation_type == Amalgamation.AmalgamationTypes.regular.name:
        msg.extend(validate_offices(amalgamation_json, filing_type))
        err = validate_share_structure(amalgamation_json, filing_type)
        if err:
            msg.extend(err)

    msg.extend(validate_amalgamation_court_order(amalgamation_json, filing_type))
    msg.extend(validate_amalgamating_businesses(amalgamation_json,
                                                filing_type,
                                                legal_type,
                                                amalgamation_type,
                                                account_id))

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def validate_amalgamating_businesses(  # pylint: disable=too-many-branches,too-many-statements,too-many-locals
        amalgamation_json,
        filing_type,
        legal_type,
        amalgamation_type,
        account_id) -> list:
    """Validate amalgamating businesses."""
    is_staff = jwt.validate_roles([STAFF_ROLE])
    msg = []
    amalgamating_businesses_json = amalgamation_json.get('filing', {}) \
                                                    .get(filing_type, {})\
                                                    .get('amalgamatingBusinesses', [])
    amalgamating_businesses_path = f'/filing/{filing_type}/amalgamatingBusinesses'
    is_any_business = {
        Business.LegalTypes.BCOMP.value: False,
        Business.LegalTypes.COMP.value: False,
        Business.LegalTypes.BC_CCC.value: False,
        Business.LegalTypes.BC_ULC_COMPANY.value: False
    }
    is_any_expro_a = False
    is_any_foreign = False
    business_identifiers = []
    duplicate_businesses = []
    adoptable_names = []
    primary_or_holding_business = None
    amalgamating_business_roles = {
        AmalgamatingBusiness.Role.amalgamating.name: 0,
        AmalgamatingBusiness.Role.holding.name: 0,
        AmalgamatingBusiness.Role.primary.name: 0
    }
    amalgamating_businesses = {}

    # collect data for validation
    for amalgamating_business_json in amalgamating_businesses_json:
        amalgamating_business_roles[amalgamating_business_json['role']] += 1
        identifier = amalgamating_business_json.get('identifier')
        if identifier in business_identifiers:
            duplicate_businesses.append(identifier)
            continue

        business_identifiers.append(identifier)

        # Check if its a foreign business
        if foreign_jurisdiction := amalgamating_business_json.get('foreignJurisdiction'):
            is_any_foreign = True
            if (identifier.startswith('A') and
                    foreign_jurisdiction.get('country') == 'CA' and foreign_jurisdiction.get('region') == 'BC'):
                is_any_expro_a = True
        elif business := Business.find_by_identifier(identifier):
            amalgamating_businesses[identifier] = business
            is_any_business[business.legal_type] = True
            if legal_type == business.legal_type:
                adoptable_names.append(business.legal_name)
            if amalgamating_business_json['role'] in [AmalgamatingBusiness.Role.primary.name,
                                                      AmalgamatingBusiness.Role.holding.name]:
                primary_or_holding_business = business

    is_any_bc_company = (is_any_business[Business.LegalTypes.BCOMP.value] or
                         is_any_business[Business.LegalTypes.COMP.value] or
                         is_any_business[Business.LegalTypes.BC_CCC.value] or
                         is_any_business[Business.LegalTypes.BC_ULC_COMPANY.value])

    # validate each TING business
    for index, amalgamating_business_json in enumerate(amalgamating_businesses_json):
        # foreignJurisdiction and legalName are dependent in the schema. one cannot be present without the other
        if foreign_legal_name := amalgamating_business_json.get('legalName'):
            msg.extend(_validate_foreign_businesses(is_staff,
                                                    is_any_bc_company,
                                                    is_any_business[Business.LegalTypes.BC_ULC_COMPANY.value],
                                                    legal_type,
                                                    foreign_legal_name,
                                                    amalgamating_business_json,
                                                    f'{amalgamating_businesses_path}/{index}'))
        else:
            identifier = amalgamating_business_json.get('identifier')
            amalgamating_business = amalgamating_businesses.get(identifier)
            msg.extend(_validate_lear_businesses(identifier,
                                                 amalgamating_business,
                                                 account_id,
                                                 is_staff,
                                                 f'{amalgamating_businesses_path}/{index}'))

    if duplicate_businesses:
        msg.append({
            'error': f'Duplicate amalgamating business entry found in list: {", ".join(duplicate_businesses)}.',
            'path': amalgamating_businesses_path
        })

    name_request = amalgamation_json.get('filing', {}).get(filing_type, {}).get('nameRequest', {})
    if amalgamation_type == Amalgamation.AmalgamationTypes.regular.name:
        if (not name_request.get('nrNumber') and
            (adopted_name := name_request.get('legalName')) and
                adopted_name not in adoptable_names):
            msg.append({
                'error': 'Adopt a name that have the same business type as the resulting business.',
                'path': f'/filing/{filing_type}/nameRequest/legalName'
            })

    if primary_or_holding_business:
        continued_types_map = {
            'C': 'BC',
            'CBEN': 'BEN',
            'CUL': 'ULC',
            'CCC': 'CC'
        }
        legal_type_to_compare = continued_types_map.get(primary_or_holding_business.legal_type,
                                                        primary_or_holding_business.legal_type)
        if legal_type_to_compare != legal_type:
            msg.append({
                'error': 'Legal type should be same as the legal type in primary or holding business.',
                'path': f'/filing/{filing_type}/nameRequest/legalType'
            })

    msg.extend(_validate_amalgamation_type(amalgamation_type,
                                           amalgamating_business_roles,
                                           is_any_foreign,
                                           is_any_expro_a,
                                           amalgamating_businesses_path))

    if legal_type == Business.LegalTypes.BC_CCC.value and not is_any_business[Business.LegalTypes.BC_CCC.value]:
        msg.append({
            'error': ('A BC Community Contribution Company must amalgamate to form '
                      'a new BC Community Contribution Company.'),
            'path': amalgamating_businesses_path
        })
    elif (legal_type in [Business.LegalTypes.BC_CCC.value, Business.LegalTypes.BC_ULC_COMPANY.value] and
          is_any_expro_a and is_any_bc_company):
        msg.append({
            'error': ('An extra-Pro cannot amalgamate with anything to become '
                      'a BC Unlimited Liability Company or a BC Community Contribution Company.'),
            'path': amalgamating_businesses_path
        })

    return msg


def _validate_foreign_businesses(  # pylint: disable=too-many-arguments
        is_staff,
        is_any_bc_company,
        is_any_ulc,
        legal_type,
        foreign_legal_name,
        amalgamating_business,
        amalgamating_business_path) -> list:
    msg = []
    if is_staff:
        msg.extend(validate_foreign_jurisdiction(amalgamating_business['foreignJurisdiction'],
                                                 f'{amalgamating_business_path}/foreignJurisdiction',
                                                 is_region_bc_valid=True,
                                                 is_region_for_us_required=False))

        if legal_type == Business.LegalTypes.BC_ULC_COMPANY.value and is_any_bc_company:
            msg.append({
                'error': (f'{foreign_legal_name} foreign corporation must not amalgamate with '
                          'a BC company to form a BC Unlimited Liability Company.'),
                'path': amalgamating_business_path
            })

        if is_any_ulc:
            msg.append({
                'error': ('A BC Unlimited Liability Company cannot amalgamate with '
                          f'a foreign company {foreign_legal_name}.'),
                'path': amalgamating_business_path
            })

        if amalgamating_business['role'] in [AmalgamatingBusiness.Role.primary.name,
                                             AmalgamatingBusiness.Role.holding.name]:
            msg.append({
                'error': f'A {foreign_legal_name} foreign corporation cannot be marked as Primary or Holding.',
                'path': amalgamating_business_path
            })
    else:
        msg.append({
            'error': (f'{foreign_legal_name} foreign corporation cannot '
                      'be amalgamated except by Registries staff.'),
            'path': amalgamating_business_path
        })

    return msg


def _validate_lear_businesses(  # pylint: disable=too-many-arguments
        identifier,
        amalgamating_business,
        account_id,
        is_staff,
        amalgamating_business_path) -> list:
    msg = []
    if amalgamating_business:
        if amalgamating_business.state == Business.State.HISTORICAL:
            msg.append({
                'error': f'Cannot amalgamate with {identifier} which is in historical state.',
                'path': amalgamating_business_path
            })
        elif _has_pending_filing(amalgamating_business):
            msg.append({
                'error': f'{identifier} has a draft, pending or future effective filing.',
                'path': amalgamating_business_path
            })
        elif Business.is_pending_amalgamating_business(identifier):
            msg.append({
                'error': f'{identifier} is part of a future effective amalgamation filing.',
                'path': amalgamating_business_path
            })

        if not is_staff:
            if not _is_business_affliated(identifier, account_id):
                msg.append({
                    'error': (f'{identifier} is not affiliated with the currently '
                              'selected BC Registries account.'),
                    'path': amalgamating_business_path
                })

            if not amalgamating_business.good_standing:
                msg.append({
                    'error': f'{identifier} is not in good standing.',
                    'path': amalgamating_business_path
                })
    else:
        msg.append({
            'error': f'A business with identifier:{identifier} not found.',
            'path': amalgamating_business_path
        })

    return msg


def _validate_amalgamation_type(  # pylint: disable=too-many-arguments
        amalgamation_type,
        amalgamating_business_roles,
        is_any_foreign,
        is_any_expro_a,
        amalgamating_businesses_path) -> list:
    msg = []
    if (amalgamation_type == Amalgamation.AmalgamationTypes.regular.name and
        not (amalgamating_business_roles[AmalgamatingBusiness.Role.amalgamating.name] >= 2 and
             amalgamating_business_roles[AmalgamatingBusiness.Role.holding.name] == 0 and
             amalgamating_business_roles[AmalgamatingBusiness.Role.primary.name] == 0)):
        msg.append({
            'error': 'Regular amalgamation must have 2 or more amalgamating businesses.',
            'path': amalgamating_businesses_path
        })
    elif amalgamation_type == Amalgamation.AmalgamationTypes.horizontal.name:
        if (is_any_foreign or is_any_expro_a):
            msg.append({
                'error': 'A foreign corporation or extra-Pro cannot be part of a Horizontal amalgamation.',
                'path': amalgamating_businesses_path
            })

        if not (amalgamating_business_roles[AmalgamatingBusiness.Role.primary.name] == 1 and
                amalgamating_business_roles[AmalgamatingBusiness.Role.amalgamating.name] >= 1 and
                amalgamating_business_roles[AmalgamatingBusiness.Role.holding.name] == 0):
            msg.append({
                'error': 'Horizontal amalgamation must have a primary and 1 or more amalgamating businesses.',
                'path': amalgamating_businesses_path
            })
    elif (amalgamation_type == Amalgamation.AmalgamationTypes.vertical.name and
          not (amalgamating_business_roles[AmalgamatingBusiness.Role.holding.name] == 1 and
               amalgamating_business_roles[AmalgamatingBusiness.Role.amalgamating.name] >= 1 and
               amalgamating_business_roles[AmalgamatingBusiness.Role.primary.name] == 0)):
        msg.append({
            'error': 'Vertical amalgamation must have a holding and 1 or more amalgamating businesses.',
            'path': amalgamating_businesses_path
        })

    return msg


def _is_business_affliated(identifier, account_id):
    if ((account_response := AccountService.get_account_by_affiliated_identifier(identifier)) and
        (orgs := account_response.get('orgs')) and
            any(str(org.get('id')) == account_id for org in orgs)):
        return True
    return False


def _has_pending_filing(amalgamating_business: Business):
    if Filing.get_filings_by_status(amalgamating_business.id, [
            Filing.Status.DRAFT.value,
            Filing.Status.PENDING.value,
            Filing.Status.PAID.value]):
        return True
    return False


def validate_party(filing: Dict, amalgamation_type, filing_type) -> list:
    """Validate party."""
    msg = []
    completing_parties = 0
    director_parties = 0
    parties = filing['filing'][filing_type]['parties']
    for party in parties:  # pylint: disable=too-many-nested-blocks;  # noqa: E501
        for role in party.get('roles', []):
            role_type = role.get('roleType').lower().replace(' ', '_')
            if role_type == PartyRole.RoleTypes.COMPLETING_PARTY.value:
                completing_parties += 1
            elif role_type == PartyRole.RoleTypes.DIRECTOR.value:
                director_parties += 1

    party_path = f'/filing/{filing_type}/parties'
    if (amalgamation_type == Amalgamation.AmalgamationTypes.regular.name and
            (completing_parties < 1 or director_parties < 1)):
        msg.append({'error': 'At least one Director and a Completing Party is required.', 'path': party_path})
    elif (amalgamation_type in [Amalgamation.AmalgamationTypes.vertical.name,
                                Amalgamation.AmalgamationTypes.horizontal.name] and
          completing_parties == 0):
        msg.append({'error': 'A Completing Party is required.', 'path': party_path})

    return msg


def validate_amalgamation_court_order(filing: Dict, filing_type) -> list:
    """Validate court order."""
    if court_order := filing.get('filing', {}).get(filing_type, {}).get('courtOrder', None):
        court_order_path: Final = f'/filing/{filing_type}/courtOrder'
        err = validate_court_order(court_order_path, court_order)
        if err:
            return err
    return []
