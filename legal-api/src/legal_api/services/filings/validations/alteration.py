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
from legal_api.services import namex
from legal_api.services.utils import get_str

from .common_validations import (
    validate_court_order,
    validate_resolution_date_in_share_structure,
    validate_share_structure,
)


def validate(business: Business, filing: Dict) -> Error:  # pylint: disable=too-many-branches
    """Validate the Alteration filing."""
    if not business or not filing:
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

        if not nr_response['requestTypeCd'] in ('CCR', 'CCP', 'BEC', 'BECV'):
            msg.append({'error': babel('Alteration only available for Change of Name Name requests.'), 'path': nr_path})

        if not validation_result['is_consumable']:
            msg.append({'error': babel('Alteration of Name Request is not approved.'), 'path': nr_path})

        # ensure NR request has the same legal name
        legal_name_path: Final = '/filing/alteration/nameRequest/legalName'
        legal_name = get_str(filing, legal_name_path)
        nr_name = namex.get_approved_name(nr_response)
        if nr_name != legal_name:
            msg.append({'error': babel('Alteration of Name Request has a different legal name.'),
                        'path': legal_name_path})
    else:
        # ensure legalType is valid
        legal_type_path: Final = '/filing/business/legalType'
        if get_str(filing, legal_type_path) not in \
                (Business.LegalTypes.BC_ULC_COMPANY.value,
                 Business.LegalTypes.COMP.value,
                 Business.LegalTypes.BCOMP.value):
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
    # you must alter to a bc benefit company
    if get_str(filing, legal_type_path) != Business.LegalTypes.BCOMP.value:
        msg.append({'error': babel('Your business type has not been updated to a BC Benefit Company.'),
                    'path': legal_type_path})
        return msg
    return []

def rules_change_validation(filing):
    msg = []
    rules_file_key: Final = get_str('/filing/alteration/rulesFileKey')
    rules_file_name: Final = get_str('/filing/alteration/rulesFileName')

    if rules_file_key or rules_file_name:
        if not rules_file_key and rules_file_name:
            msg.append({'error': babel('Both rulesFileKey and rulesFileName should be privided')})
            return msg
    return []        

def memorandum_change_validation(filing):
    msg = []
    memorandum_file_key: Final = get_str('/filing/alteration/memorandumFileKey')
    memorandum_file_name: Final = get_str('/filing/alteration/memorandumFileName')

    if memorandum_file_key or memorandum_file_name:
        if not memorandum_file_key and memorandum_file_name:
            msg.append({'error': babel('Both memorandumFileKey and memorandumFileName should be privided')})
            return msg
    return []
