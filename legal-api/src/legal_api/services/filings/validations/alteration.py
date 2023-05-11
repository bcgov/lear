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
from legal_api.models import LegalEntity
from legal_api.services import namex
from legal_api.services.utils import get_bool, get_str

from .common_validations import (
    validate_court_order,
    validate_pdf,
    validate_resolution_date_in_share_structure,
    validate_share_structure,
)


def validate(legal_entity: LegalEntity, filing: Dict) -> Error:  # pylint: disable=too-many-branches
    """Validate the Alteration filing."""
    if not legal_entity or not filing:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid business and filing are required.')}])
    msg = []

    msg.extend(company_name_validation(filing))
    msg.extend(share_structure_validation(filing))
    msg.extend(court_order_validation(filing))
    msg.extend(type_change_validation(filing))
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


def company_name_validation(filing):
    """Validate company name."""
    msg = []
    nr_path: Final = '/filing/alteration/nameRequest/nrNumber'
    if nr_number := get_str(filing, nr_path):
        # ensure NR is approved or conditionally approved
        nr_response = namex.query_nr_number(nr_number).json()
        validation_result = namex.validate_nr(nr_response)

        error_msg = """The name type associated with the name request number entered cannot be used for this
                       transaction type."""
        if not nr_response['requestTypeCd'] in ('CCR', 'CCP', 'BEC', 'BECV'):
            msg.append({'error': babel(error_msg).replace('\n', '').replace('  ', ''),
                        'path': nr_path})

        if not validation_result['is_consumable']:
            msg.append({'error': babel('Alteration of Name Request is not approved.'), 'path': nr_path})

        # ensure NR request has the same legal name
        nr_legal_name_path: Final = '/filing/alteration/nameRequest/legalName'
        legal_name = get_str(filing, nr_legal_name_path)
        nr_name = namex.get_approved_name(nr_response)
        if nr_name != legal_name:
            msg.append({'error': babel('Alteration of Name Request has a different legal name.'),
                        'path': nr_legal_name_path})

        nr_legal_type_path: Final = '/filing/alteration/nameRequest/legalType'
        legal_type = get_str(filing, nr_legal_type_path)
        nr_legal_type = nr_response.get('legalType')
        if legal_type != nr_legal_type:
            msg.append({'error': babel('Name Request legal type is not same as the business legal type.'),
                        'path': nr_legal_type_path})
    else:
        # ensure legalType is valid
        legal_type_path: Final = '/filing/business/legalType'
        if get_str(filing, legal_type_path) not in \
                (LegalEntity.EntityTypes.BC_ULC_COMPANY.value,
                 LegalEntity.EntityTypes.BC_CCC.value,
                 LegalEntity.EntityTypes.COMP.value,
                 LegalEntity.EntityTypes.BCOMP.value,
                 LegalEntity.EntityTypes.COOP.value):
            msg.append({'error': babel('Alteration not valid for selected Legal Type.'), 'path': legal_type_path})

        # ensure company is named if being altered to numbered
        legal_name_path: Final = '/filing/business/legalName'
        if not get_str(filing, legal_name_path):
            msg.append({'error': babel('Alteration to Numbered Company can only be done for a Named Company.'),
                        'path': legal_name_path})

    return msg


def type_change_validation(filing):
    """Validate type change."""
    msg = []
    legal_type_path: Final = '/filing/alteration/business/legalType'
    # you must alter to a bc benefit company or a COOP
    if get_str(filing, legal_type_path) not in (LegalEntity.EntityTypes.BCOMP.value,
                                                LegalEntity.EntityTypes.COOP.value,
                                                LegalEntity.EntityTypes.BC_ULC_COMPANY.value,
                                                LegalEntity.EntityTypes.COMP.value,
                                                LegalEntity.EntityTypes.BC_CCC.value):
        error_msg = """Your business type has not been updated to a BC Benefit Company,
                       BC Unlimited Liability Company, BC Community Contribution Company,
                       BC Limited Company or BC Cooperative Association."""
        msg.append({'error': babel(error_msg),
                    'path': legal_type_path})
        return msg
    return []


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
        rules_err = validate_pdf(rules_file_key, rules_file_key_path)
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
        memorandum_err = validate_pdf(memorandum_file_key, memorandum_file_key_path)
        if memorandum_err:
            msg.extend(memorandum_err)

    return msg
