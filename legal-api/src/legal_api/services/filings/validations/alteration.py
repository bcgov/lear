# Copyright © 2021 Province of British Columbia
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
"""Validation for the Alteration filing."""
from http import HTTPStatus
from typing import Dict, Final

from flask_babel import _ as babel  # noqa: N81

from legal_api.core.filing import Filing
from legal_api.errors import Error
from legal_api.models import Business
from legal_api.services.utils import get_bool, get_str
from legal_api.constants import DocumentClasses

from .common_validations import (
    validate_court_order,
    validate_name_request,
    validate_pdf,
    validate_resolution_date_in_share_structure,
    validate_share_structure
)


def validate(business: Business, filing: Dict) -> Error:  # pylint: disable=too-many-branches
    """Validate the Alteration filing."""
    if not business or not filing:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid business and filing are required.')}])
    msg = []

    msg.extend(type_change_validation(filing, business))
    msg.extend(company_name_validation(filing, business))
    msg.extend(share_structure_validation(filing))
    msg.extend(court_order_validation(filing))
    msg.extend(rules_change_validation(filing))
    msg.extend(memorandum_change_validation(filing))

    if err := validate_resolution_date_in_share_structure(filing, 'alteration'):
        msg.append(err)

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)

    return None


def court_order_validation(filing):
    """Validate court order."""
    court_order_path: Final = '/filing/alteration/courtOrder'
    if get_str(filing, court_order_path):
        err = validate_court_order(court_order_path, filing['filing']['alteration']['courtOrder'])
        if err:
            return err
    return []


def share_structure_validation(filing):
    """Validate share structure."""
    share_structure_path: Final = '/filing/alteration/shareStructure'
    if get_str(filing, share_structure_path):
        err = validate_share_structure(filing, Filing.FilingTypes.ALTERATION.value)
        if err:
            return err
    return []


def company_name_validation(filing, business: Business):
    """Validate company name."""
    msg = []

    new_legal_type = get_str(filing, '/filing/alteration/business/legalType')
    if get_str(filing, '/filing/alteration/nameRequest/nrNumber'):
        accepted_request_types = [
            'BEC', 'CCC', 'CCP', 'CCR', 'CUL',  # name change types
            'BECV', 'CCV', 'UC', 'BECR', 'BECC', 'ULCB', 'ULBE'  # conversion types
        ]
        msg.extend(validate_name_request(filing,
                                         new_legal_type or business.legal_type,
                                         'alteration',
                                         accepted_request_types))
    else:
        valid_names = [business.legal_name]
        if (new_legal_type and
                (new_numbered_name := Business.generate_numbered_legal_name(new_legal_type, business.identifier))):
            # if existing legal_name is a numbered name and if type has changed
            # then the legal name get updated according to the new legal type
            valid_names.append(new_numbered_name)

        nr_legal_name_path: Final = '/filing/alteration/nameRequest/legalName'
        new_legal_name = get_str(filing, nr_legal_name_path)
        if new_legal_name and new_legal_name not in valid_names:
            msg.append({'error': babel('Unexpected legal name.'), 'path': nr_legal_name_path})
    return msg


def type_change_validation(filing, business: Business):
    """Validate type change."""
    msg = []
    legal_type_path: Final = '/filing/alteration/business/legalType'
    new_legal_type = get_str(filing, legal_type_path)

    # Valid type changes
    # BEN -> BC (BECR)
    # BEN -> CCC (BECC)
    # BC -> BEN (BECV)
    # BC -> ULC (UC)
    # BC -> CCC (CCV)
    # ULC -> BEN (ULBE)
    # ULC -> BC (ULCB)

    valid_type_changes = {
        Business.LegalTypes.COOP.value: [Business.LegalTypes.COOP.value],
        Business.LegalTypes.BCOMP.value: [Business.LegalTypes.BCOMP.value,
                                          Business.LegalTypes.COMP.value,
                                          Business.LegalTypes.BC_CCC.value],
        Business.LegalTypes.COMP.value: [Business.LegalTypes.COMP.value,
                                         Business.LegalTypes.BCOMP.value,
                                         Business.LegalTypes.BC_ULC_COMPANY.value,
                                         Business.LegalTypes.BC_CCC.value],
        Business.LegalTypes.BC_CCC.value: [Business.LegalTypes.BC_CCC.value],
        Business.LegalTypes.BC_ULC_COMPANY.value: [Business.LegalTypes.BC_ULC_COMPANY.value,
                                                   Business.LegalTypes.BCOMP.value,
                                                   Business.LegalTypes.COMP.value],
        Business.LegalTypes.BCOMP_CONTINUE_IN.value: [Business.LegalTypes.BCOMP_CONTINUE_IN.value,
                                                      Business.LegalTypes.CONTINUE_IN.value,
                                                      Business.LegalTypes.CCC_CONTINUE_IN.value],
        Business.LegalTypes.CONTINUE_IN.value: [Business.LegalTypes.CONTINUE_IN.value,
                                                Business.LegalTypes.BCOMP_CONTINUE_IN.value,
                                                Business.LegalTypes.ULC_CONTINUE_IN.value,
                                                Business.LegalTypes.CCC_CONTINUE_IN.value],
        Business.LegalTypes.CCC_CONTINUE_IN.value: [Business.LegalTypes.CCC_CONTINUE_IN.value],
        Business.LegalTypes.ULC_CONTINUE_IN.value: [Business.LegalTypes.ULC_CONTINUE_IN.value,
                                                    Business.LegalTypes.BCOMP_CONTINUE_IN.value,
                                                    Business.LegalTypes.CONTINUE_IN.value]
    }

    errors = {
        Business.LegalTypes.COOP.value: 'Cannot change the business type of a Cooperative Association.',
        Business.LegalTypes.BCOMP.value: ("""BC Benefit Company can only change to BC Limited Company or
                                          BC Community Contribution Company."""),
        Business.LegalTypes.COMP.value: ("""BC Limited Company can only change to BC Benefit Company or
                                         BC Unlimited Liability Company or BC Community Contribution Company."""),
        Business.LegalTypes.BC_CCC.value: 'Cannot change the business type of a BC Community Contribution Company.',
        Business.LegalTypes.BC_ULC_COMPANY.value: ("""BC Unlimited Liability Company can only change to
                                                   BC Benefit Company or BC Limited Company.""")
    }
    errors[Business.LegalTypes.BCOMP_CONTINUE_IN.value] = errors[Business.LegalTypes.BCOMP.value]
    errors[Business.LegalTypes.CONTINUE_IN.value] = errors[Business.LegalTypes.COMP.value]
    errors[Business.LegalTypes.CCC_CONTINUE_IN.value] = errors[Business.LegalTypes.BC_CCC.value]
    errors[Business.LegalTypes.ULC_CONTINUE_IN.value] = errors[Business.LegalTypes.BC_ULC_COMPANY.value]

    if new_legal_type and new_legal_type not in valid_type_changes.get(business.legal_type, []):
        msg.append({'error': babel(errors.get(business.legal_type, '')), 'path': legal_type_path})
    return msg


def rules_change_validation(filing):
    """Validate rules change."""
    msg = []
    rules_file_key_path: Final = '/filing/alteration/rulesFileKey'
    rules_file_key: Final = get_str(filing, rules_file_key_path)

    rules_change_in_sr_path: Final = '/filing/alteration/rulesInResolution'
    rules_change_in_sr: Final = get_bool(filing, rules_change_in_sr_path)

    if rules_file_key and rules_change_in_sr:
        error_msg = 'Cannot provide both file upload and rules change in SR'
        msg.append({'error': babel(error_msg),
                    'path': rules_file_key_path + ' and ' + rules_change_in_sr_path})
        return msg

    if rules_file_key:
        rules_err = validate_pdf(
            file_key=rules_file_key,
            file_key_path=rules_file_key_path,
            document_class=DocumentClasses.COOP.value
        )
        
        if rules_err:
            msg.extend(rules_err)
        return msg

    return []


def memorandum_change_validation(filing):
    """Validate memorandum change."""
    msg = []
    memorandum_file_key_path: Final = '/filing/alteration/memorandumFileKey'
    memorandum_file_key: Final = get_str(filing, memorandum_file_key_path)

    memorandum_change_in_sr_path: Final = '/filing/alteration/memorandumInResolution'
    memorandum_change_in_sr: Final = get_bool(filing, memorandum_change_in_sr_path)

    if memorandum_file_key and memorandum_change_in_sr:
        error_msg = 'Cannot provide both file upload and memorandum change in SR'
        msg.append({'error': babel(error_msg),
                    'path': memorandum_file_key + ' and ' + memorandum_change_in_sr_path})
        return msg

    if memorandum_file_key:
        memorandum_err = validate_pdf(
            file_key=memorandum_file_key,
            file_key_path=memorandum_file_key_path,
            document_class=DocumentClasses.COOP.value
        )
        if memorandum_err:
            msg.extend(memorandum_err)

    return msg
