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
from http import HTTPStatus
from typing import Dict

from flask_babel import _

from legal_api.errors import Error
from legal_api.models import Business, Filing, PartyRole
from legal_api.services import NaicsService
from legal_api.services.filings.validations.common_validations import validate_name_request, validate_share_structure
from legal_api.services.filings.validations.incorporation_application import validate_offices as validate_corp_offices
from legal_api.services.filings.validations.incorporation_application import (
    validate_parties_mailing_address,
    validate_parties_names,
    validate_roles,
)
from legal_api.services.filings.validations.registration import validate_offices

from ...utils import get_str


def validate(business: Business, filing: Dict) -> Error:
    """Validate the Correction filing."""
    if not business or not filing:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': _('A valid business and filing are required.')}])
    msg = []

    # confirm corrected filing ID is a valid complete filing
    corrected_filing = Filing.find_by_id(filing['filing']['correction']['correctedFilingId'])
    if not corrected_filing or corrected_filing.status != Filing.Status.COMPLETED.value:
        path = '/filing/correction/correctedFilingId'
        msg.append({'error': _('Corrected filing is not a valid filing.'), 'path': path})

    # confirm that this business owns the corrected filing
    elif not business.id == corrected_filing.business_id:
        path = '/filing/correction/correctedFilingId'
        msg.append({'error': _('Corrected filing is not a valid filing for this business.'), 'path': path})

    # validations for firms
    if legal_type := filing.get('filing', {}).get('business', {}).get('legalType'):
        if legal_type in [Business.LegalTypes.SOLE_PROP.value, Business.LegalTypes.PARTNERSHIP.value]:
            _validate_firms_correction(business, filing, legal_type, msg)
        elif legal_type in [Business.LegalTypes.COMP.value, Business.LegalTypes.BCOMP.value,
                            Business.LegalTypes.LIMITED_CO.value, Business.LegalTypes.BC_ULC_COMPANY.value,
                            Business.LegalTypes.BC_CCC.value]:
            _validate_corps_correction(filing, legal_type, msg)

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
    msg.extend(validate_naics(business, filing, filing_type))


def _validate_corps_correction(filing_dict, legal_type, msg):
    filing_type = 'correction'
    if filing_dict.get('filing', {}).get('correction', {}).get('nameRequest', {}).get('nrNumber', None):
        msg.extend(validate_name_request(filing_dict, legal_type, filing_type))
    if filing_dict.get('filing', {}).get('correction', {}).get('offices', None):
        err = validate_corp_offices(filing_dict, filing_type)
        if err:
            msg.extend(err)
    if filing_dict.get('filing', {}).get('correction', {}).get('parties', None):
        err = validate_roles(filing_dict, legal_type, filing_type)
        if err:
            msg.extend(err)
        # FUTURE: this should be removed when COLIN sync back is no longer required.
        err = validate_parties_names(filing_dict, legal_type, filing_type)
        if err:
            msg.extend(err)

        err = validate_parties_mailing_address(filing_dict, legal_type, filing_type)
        if err:
            msg.extend(err)
    if filing_dict.get('filing', {}).get('correction', {}).get('shareStructure', None):
        err = validate_share_structure(filing_dict, filing_type)
        if err:
            msg.extend(err)


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
