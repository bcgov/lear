# Copyright © 2022 Province of British Columbia
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
"""Validation for the Registration filing."""
from datetime import timedelta
from http import HTTPStatus  # pylint: disable=wrong-import-order
from typing import Dict, Final, Optional

from legal_api.services.permissions import ListActionsPermissionsAllowed, PermissionService
import pycountry
from dateutil.relativedelta import relativedelta
from flask_babel import _ as babel  # noqa: N813, I004, I001, I003

from legal_api.errors import Error
from legal_api.models import Business, PartyRole
from legal_api.services import STAFF_ROLE, NaicsService
from legal_api.services.filings.validations.common_validations import (
    validate_certify_name,
    validate_court_order,
    validate_name_request,
    validate_offices_addresses,
    validate_parties_actions,
    validate_parties_addresses,
)
from legal_api.services.utils import get_date, get_str
from legal_api.utils.auth import jwt
from legal_api.utils.legislation_datetime import LegislationDatetime


def validate(registration_json: Dict) -> Optional[Error]:
    """Validate the Registration filing."""
    if not registration_json:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid filing is required.')}])

    legal_type_path = '/filing/registration/nameRequest/legalType'
    legal_type = get_str(registration_json, legal_type_path)
    filing_type = 'registration'
    if legal_type not in [Business.LegalTypes.SOLE_PROP.value, Business.LegalTypes.PARTNERSHIP.value]:
        return Error(
            HTTPStatus.BAD_REQUEST,
            [{'error': babel('A valid legalType for registration is required.'), 'path': legal_type_path}]
        )
    authorized_permissions = PermissionService.get_authorized_permissions_for_user()
    if validate_certify_name(registration_json):
        allowed_role_comments = ListActionsPermissionsAllowed.EDITABLE_CERTIFY_NAME.value
        if allowed_role_comments not in authorized_permissions:
            return Error(
                HTTPStatus.FORBIDDEN,
                [{ 'message': f'Permission Denied - You do not have permissions to change certified by in this filing.'}]
            )
    actions = validate_parties_actions(registration_json, filing_type )
    if any(actions) not in authorized_permissions:
        return Error(
                HTTPStatus.FORBIDDEN,
                [{ 'message': f'Permission Denied - You do not have permissions to change certified by in this filing.'}]
            )

    msg = []
    msg.extend(validate_name_request(registration_json, legal_type, filing_type))
    msg.extend(validate_tax_id(registration_json))
    msg.extend(validate_naics(registration_json))
    msg.extend(validate_business_type(registration_json, legal_type))
    msg.extend(validate_party(registration_json, legal_type))
    msg.extend(validate_parties_addresses(registration_json, filing_type))
    msg.extend(validate_start_date(registration_json))
    msg.extend(validate_offices(registration_json))
    msg.extend(validate_offices_addresses(registration_json, filing_type))
    msg.extend(validate_registration_court_order(registration_json))

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def validate_business_type(filing: Dict, legal_type: str) -> list:
    """Validate business type."""
    msg = []
    business_type_path = '/filing/registration/businessType'
    if legal_type == Business.LegalTypes.SOLE_PROP.value and get_str(filing, business_type_path) is None:
        msg.append({'error': 'Business Type is required.', 'path': business_type_path})

    return msg


def validate_tax_id(filing: Dict) -> list:
    """Validate tax id."""
    msg = []
    tax_id_path = '/filing/registration/business/taxId'
    if (tax_id := get_str(filing, tax_id_path)) and len(tax_id) == 15:
        msg.append({'error': 'Can only provide BN9 for SP/GP registration.', 'path': tax_id_path})

    return msg


def validate_naics(filing: Dict, filing_type='registration') -> list:
    """Validate naics."""
    msg = []
    naics_code_path = f'/filing/{filing_type}/business/naics/naicsCode'
    naics_desc = get_str(filing, f'/filing/{filing_type}/business/naics/naicsDescription')
    if naics_code := get_str(filing, naics_code_path):
        naics = NaicsService.find_by_code(naics_code)
        if not naics or naics['classTitle'] != naics_desc:
            msg.append({'error': 'Invalid naics code or description.', 'path': naics_code_path})

    return msg


def validate_party(filing: Dict, legal_type: str, filing_type='registration') -> list:
    """Validate party."""
    msg = []
    completing_parties = 0
    proprietor_parties = 0
    partner_parties = 0
    parties = filing['filing'][filing_type]['parties']
    for party in parties:  # pylint: disable=too-many-nested-blocks;  # noqa: E501
        for role in party.get('roles', []):
            role_type = role.get('roleType').lower().replace(' ', '_')
            if role_type == PartyRole.RoleTypes.COMPLETING_PARTY.value:
                completing_parties += 1
            elif role_type == PartyRole.RoleTypes.PROPRIETOR.value:
                proprietor_parties += 1
            elif role_type == PartyRole.RoleTypes.PARTNER.value:
                partner_parties += 1

    party_path = '/filing/registration/parties'
    if legal_type == Business.LegalTypes.SOLE_PROP.value and (completing_parties < 1 or proprietor_parties < 1):
        msg.append({'error': '1 Proprietor and a Completing Party is required.', 'path': party_path})
    elif legal_type == Business.LegalTypes.PARTNERSHIP.value and (completing_parties < 1 or partner_parties < 2):
        msg.append({'error': '2 Partners and a Completing Party is required.', 'path': party_path})

    return msg


def validate_start_date(filing: Dict) -> list:
    """Validate start date."""
    # Non-staff can go less than or equal to 10 years in the past, less than or equal to 90 days in the future
    # Staff can go back with an unlimited period of time
    msg = []
    start_date_path = '/filing/registration/startDate'
    start_date = get_date(filing, start_date_path)
    now = LegislationDatetime.now().date()
    greater = now + timedelta(days=90)
    lesser = now + relativedelta(years=-10)

    if not jwt.validate_roles([STAFF_ROLE]):
        if start_date < lesser:
            msg.append({'error': 'Start date must be less than or equal to 10 years.',
                        'path': start_date_path})
    if start_date > greater:
        msg.append({'error': 'Start Date must be less than or equal to 90 days in the future.',
                    'path': start_date_path})

    return msg


def validate_offices(filing: Dict, filing_type='registration') -> list:
    """Validate the business address of registration filing."""
    offices = filing['filing'][filing_type]['offices']
    msg = []

    if delivery_address := offices.get('businessOffice', {}).get('deliveryAddress'):
        region = delivery_address['addressRegion']
        country = delivery_address['addressCountry']

        if region != 'BC':
            region_path = f'/filing/{filing_type}/offices/businessOffice/deliveryAddress/addressRegion'
            msg.append({'error': "Address Region must be 'BC'.", 'path': region_path})

        try:
            country = pycountry.countries.search_fuzzy(country)[0].alpha_2
            if country != 'CA':
                raise LookupError
        except LookupError:
            country_path = f'/filing/{filing_type}/offices/businessOffice/deliveryAddress/addressCountry'
            msg.append({'error': "Address Country must be 'CA'.", 'path': country_path})

    return msg


def validate_registration_court_order(filing: Dict, filing_type='registration') -> list:
    """Validate court order."""
    if court_order := filing.get('filing', {}).get(filing_type, {}).get('courtOrder', None):
        court_order_path: Final = f'/filing/{filing_type}/courtOrder'
        err = validate_court_order(court_order_path, court_order)
        if err:
            return err
    return []
