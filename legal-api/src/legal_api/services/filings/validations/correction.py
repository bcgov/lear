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
"""Validation for the Correction filing."""
from datetime import timedelta
from http import HTTPStatus
from typing import Dict, Final

from dateutil.relativedelta import relativedelta
from flask_babel import _

from legal_api.core.filing_helper import is_special_resolution_correction_by_filing_json
from legal_api.errors import Error
from legal_api.models import Business, Filing, PartyRole
from legal_api.services import STAFF_ROLE, NaicsService
from legal_api.services.filings.validations.common_validations import (
    validate_court_order,
    validate_name_request,
    validate_parties_names,
    validate_pdf,
    validate_share_structure,
)
from legal_api.services.filings.validations.incorporation_application import validate_offices as validate_corp_offices
from legal_api.services.filings.validations.incorporation_application import (
    validate_parties_mailing_address,
    validate_roles,
)
from legal_api.services.filings.validations.registration import validate_offices
from legal_api.services.filings.validations.special_resolution import (
    validate_resolution_content,
    validate_signatory_name,
    validate_signing_date,
)
from legal_api.utils.auth import jwt

from ...utils import get_date, get_str


def validate(business: Business, filing: Dict) -> Error:
    """Validate the Correction filing."""
    if not business or not filing:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': _('A valid business and filing are required.')}])
    msg = []

    # confirm corrected filing ID is a valid complete filing
    corrected_filing = Filing.find_by_id(filing['filing']['correction']['correctedFilingId'])
    if not corrected_filing or corrected_filing.status not in [Filing.Status.COMPLETED.value,
                                                               Filing.Status.CORRECTED.value]:
        path = '/filing/correction/correctedFilingId'
        msg.append({'error': _('Corrected filing is not a valid filing.'), 'path': path})

    # confirm that this business owns the corrected filing
    elif not business.id == corrected_filing.business_id:
        path = '/filing/correction/correctedFilingId'
        msg.append({'error': _('Corrected filing is not a valid filing for this business.'), 'path': path})

    # validations for firms
    if business.legal_type in [Business.LegalTypes.SOLE_PROP.value, Business.LegalTypes.PARTNERSHIP.value]:
        _validate_firms_correction(business, filing, business.legal_type, msg)
    elif business.legal_type in Business.CORPS:
        _validate_corps_correction(filing, business.legal_type, msg)
    elif business.legal_type in [Business.LegalTypes.COOP.value]:
        _validate_special_resolution_correction(filing, business.legal_type, msg)

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)

    return None


def _validate_firms_correction(business: Business, filing, legal_type, msg):
    filing_type = 'correction'
    if filing.get('filing', {}).get('correction', {}).get('nameRequest', {}).get('nrNumber', None):
        msg.extend(validate_name_request(filing, legal_type, filing_type))
    if filing.get('filing', {}).get('correction', {}).get('parties', None):
        msg.extend(validate_party(filing, legal_type))
    if filing.get('filing', {}).get('correction', {}).get('offices', None):
        msg.extend(validate_offices(filing, filing_type))
    if filing.get('filing', {}).get('correction', {}).get('startDate', None):
        msg.extend(validate_start_date(business, filing))
    msg.extend(validate_naics(business, filing, filing_type))


def _validate_corps_correction(filing_dict, legal_type, msg):
    filing_type = 'correction'
    if filing_dict.get('filing', {}).get('correction', {}).get('nameRequest', {}).get('nrNumber', None):
        msg.extend(validate_name_request(filing_dict, legal_type, filing_type))
    if filing_dict.get('filing', {}).get('correction', {}).get('offices', None):
        msg.extend(validate_corp_offices(filing_dict, legal_type, filing_type))
    if filing_dict.get('filing', {}).get('correction', {}).get('parties', None):
        err = validate_roles(filing_dict, legal_type, filing_type)
        if err:
            msg.extend(err)
        # FUTURE: this should be removed when COLIN sync back is no longer required.
        msg.extend(validate_parties_names(filing_dict, filing_type, legal_type))

        err = validate_parties_mailing_address(filing_dict, legal_type, filing_type)
        if err:
            msg.extend(err)
    if filing_dict.get('filing', {}).get('correction', {}).get('shareStructure', None):
        err = validate_share_structure(filing_dict, filing_type, legal_type)
        if err:
            msg.extend(err)


def _validate_special_resolution_correction(filing_dict, legal_type, msg):
    filing_type = 'correction'
    if filing_dict.get('filing', {}).get(filing_type, {}).get('nameRequest', {}).get('nrNumber', None):
        msg.extend(validate_name_request(filing_dict, legal_type, filing_type))
    if filing_dict.get('filing', {}).get(filing_type, {}).get('correction', {}).get('resolution', None):
        msg.extend(validate_resolution_content(filing_dict, filing_type))
    if filing_dict.get('filing', {}).get(filing_type, {}).get('correction', {}).get('signingDate', None):
        msg.extend(validate_signing_date(filing_dict, filing_type))
    if filing_dict.get('filing', {}).get(filing_type, {}).get('correction', {}).get('signatory', None):
        msg.extend(validate_signatory_name(filing_dict, filing_type))
    if filing_dict.get('filing', {}).get(filing_type, {}).get('correction', {}).get('courtOrder', None):
        msg.extend(court_order_validation(filing_dict))
    if filing_dict.get('filing', {}).get(filing_type, {}).get('correction', {}).get('rulesFileKey', None):
        msg.extend(rules_change_validation(filing_dict))
    if filing_dict.get('filing', {}).get(filing_type, {}).get('correction', {}).get('memorandumFileKey', None):
        msg.extend(memorandum_change_validation(filing_dict))
    if is_special_resolution_correction_by_filing_json(filing_dict.get('filing', {})):
        _validate_roles_parties_correction(filing_dict, legal_type, filing_type, msg)


def _validate_roles_parties_correction(filing_dict, legal_type, filing_type, msg):
    if filing_dict.get('filing', {}).get('correction', {}).get('parties', None):
        err = validate_roles(filing_dict, legal_type, filing_type)
        if err:
            msg.extend(err)

        msg.extend(validate_parties_names(filing_dict, filing_type, legal_type))

        err = validate_parties_mailing_address(filing_dict, legal_type, filing_type)
        if err:
            msg.extend(err)
    else:
        err_path = f'/filing/{filing_type}/parties/roles'
        msg.append({'error': 'Parties list cannot be empty or null', 'path': err_path})


def validate_party(filing: Dict, legal_type: str) -> list:
    """Validate party."""
    msg = []
    completing_parties = 0
    proprietor_parties = 0
    partner_parties = 0
    parties = filing['filing']['correction']['parties']
    for party in parties:  # pylint: disable=too-many-nested-blocks;  # noqa: E501
        for role in party.get('roles', []):
            role_type = role.get('roleType').lower().replace(' ', '_')
            if role_type == PartyRole.RoleTypes.COMPLETING_PARTY.value:
                completing_parties += 1
            elif role_type == PartyRole.RoleTypes.PROPRIETOR.value:
                proprietor_parties += 1
            elif role_type == PartyRole.RoleTypes.PARTNER.value:
                partner_parties += 1

    correction_type = filing.get('filing').get('correction').get('type', 'STAFF')
    party_path = '/filing/correction/parties'

    if correction_type == 'STAFF':
        if legal_type == Business.LegalTypes.SOLE_PROP.value and proprietor_parties < 1:
            msg.append({'error': '1 Proprietor is required.', 'path': party_path})
        elif legal_type == Business.LegalTypes.PARTNERSHIP.value and partner_parties < 2:
            msg.append({'error': '2 Partners are required.', 'path': party_path})
    else:
        if legal_type == Business.LegalTypes.SOLE_PROP.value and (completing_parties < 1 or proprietor_parties < 1):
            msg.append({'error': '1 Proprietor and a Completing Party is required.', 'path': party_path})
        elif legal_type == Business.LegalTypes.PARTNERSHIP.value and (completing_parties < 1 or partner_parties < 2):
            msg.append({'error': '2 Partners and a Completing Party is required.', 'path': party_path})

    return msg


def validate_naics(business: Business, filing: Dict, filing_type: str) -> list:
    """Validate naics."""
    msg = []
    naics_code_path = f'/filing/{filing_type}/business/naics/naicsCode'
    naics_code = get_str(filing, naics_code_path)
    naics_desc = get_str(filing, f'/filing/{filing_type}/business/naics/naicsDescription')

    # Note: if existing naics code and description has not changed, no NAICS validation is required
    if naics_code and (business.naics_code != naics_code or business.naics_description != naics_desc):
        naics = NaicsService.find_by_code(naics_code)
        if not naics or naics['classTitle'] != naics_desc:
            msg.append({'error': 'Invalid naics code or description.', 'path': naics_code_path})

    return msg


def validate_start_date(business: Business, filing: Dict) -> list:
    """Validate start date."""
    # Staff can go back with an unlimited period of time, the maximum start date is 90 days after the registration date
    msg = []
    start_date_path = '/filing/correction/startDate'
    start_date = get_date(filing, start_date_path)
    registration_date = business.founding_date.date()
    greater = registration_date + timedelta(days=90)
    lesser = registration_date + relativedelta(years=-10)

    if not jwt.validate_roles([STAFF_ROLE]):
        if start_date < lesser:
            msg.append({'error': 'Start date must be less than or equal to 10 years.',
                        'path': start_date_path})
    if start_date > greater:
        msg.append({'error': 'Start Date must be less than or equal to 90 days in the future.',
                    'path': start_date_path})

    return msg


def court_order_validation(filing):
    """Validate court order."""
    court_order_path: Final = '/filing/correction/courtOrder'
    if get_str(filing, court_order_path):
        err = validate_court_order(court_order_path, filing['filing']['correction']['courtOrder'])
        if err:
            return err
    return []


def rules_change_validation(filing):
    """Validate rules change."""
    msg = []
    rules_file_key_path: Final = '/filing/correction/rulesFileKey'
    rules_file_key: Final = get_str(filing, rules_file_key_path)

    if rules_file_key:
        rules_err = validate_pdf(rules_file_key, rules_file_key_path)
        if rules_err:
            msg.extend(rules_err)
        return msg
    return []


def memorandum_change_validation(filing):
    """Validate memorandum change."""
    msg = []
    memorandum_file_key_path: Final = '/filing/correction/memorandumFileKey'
    memorandum_file_key: Final = get_str(filing, memorandum_file_key_path)

    if memorandum_file_key:
        rules_err = validate_pdf(memorandum_file_key, memorandum_file_key_path)
        if rules_err:
            msg.extend(rules_err)
        return msg
    return []
