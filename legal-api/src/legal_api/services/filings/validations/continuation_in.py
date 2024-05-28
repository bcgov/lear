# Copyright © 2024 Province of British Columbia
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
"""Validation for the Continuation In filing."""
from http import HTTPStatus  # pylint: disable=wrong-import-order
from typing import Final, Optional

from flask_babel import _ as babel  # noqa: N813, I004, I001, I003

from legal_api.errors import Error
from legal_api.models import Business, PartyRole
from legal_api.services.filings.validations.common_validations import (
    validate_court_order,
    validate_foreign_jurisdiction,
    validate_name_request,
    validate_parties_names,
    validate_pdf,
    validate_share_structure,
)
from legal_api.services.filings.validations.incorporation_application import (
    validate_incorporation_effective_date,
    validate_offices,
    validate_parties_mailing_address,
)
from legal_api.services.utils import get_date, get_str
from legal_api.utils.legislation_datetime import LegislationDatetime


def validate(filing_json: dict) -> Optional[Error]:  # pylint: disable=too-many-branches;
    """Validate the Continuation In filing."""
    filing_type = 'continuationIn'
    if not filing_json:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid filing is required.')}])
    msg = []

    legal_type_path = '/filing/continuationIn/nameRequest/legalType'
    legal_type = get_str(filing_json, legal_type_path)
    if not legal_type:
        msg.append({'error': babel('Legal type is required.'), 'path': legal_type_path})
        return msg  # Cannot continue validation without legal_type

    msg.extend(validate_name_request(filing_json, legal_type, filing_type))
    msg.extend(validate_offices(filing_json, filing_type))
    msg.extend(validate_roles(filing_json, legal_type, filing_type))
    msg.extend(validate_parties_names(filing_json, filing_type))

    err = validate_parties_mailing_address(filing_json, legal_type, filing_type)
    if err:
        msg.extend(err)

    err = validate_share_structure(filing_json, filing_type)
    if err:
        msg.extend(err)

    msg.extend(validate_continuation_in_authorization(filing_json, filing_type))
    msg.extend(_validate_foreign_jurisdiction(filing_json, filing_type, legal_type))

    err = validate_incorporation_effective_date(filing_json)
    if err:
        msg.extend(err)

    msg.extend(validate_continuation_in_court_order(filing_json, filing_type))

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def validate_roles(filing_dict: dict, legal_type: str, filing_type: str) -> list:
    """Validate the required completing party of the filing."""
    min_director_count_info = {
        Business.LegalTypes.BCOMP_CONTINUE_IN.value: 1,
        Business.LegalTypes.CONTINUE_IN.value: 1,
        Business.LegalTypes.ULC_CONTINUE_IN.value: 1,
        Business.LegalTypes.CCC_CONTINUE_IN.value: 3
    }
    msg = []
    completing_party_count = 0
    director_count = 0

    parties = filing_dict['filing'][filing_type]['parties']
    for party in parties:  # pylint: disable=too-many-nested-blocks;  # noqa: E501
        for role in party.get('roles', []):
            role_type = role.get('roleType').lower().replace(' ', '_')
            if role_type == PartyRole.RoleTypes.COMPLETING_PARTY.value:
                completing_party_count += 1
            elif role_type == PartyRole.RoleTypes.DIRECTOR.value:
                director_count += 1

    if completing_party_count == 0:
        err_path = f'/filing/{filing_type}/parties/roles'
        msg.append({'error': 'Must have a minimum of one completing party.', 'path': err_path})
    elif completing_party_count > 1:
        err_path = f'/filing/{filing_type}/parties/roles'
        msg.append({'error': 'Must have a maximum of one completing party.', 'path': err_path})

    min_director_count = min_director_count_info.get(legal_type, 0)
    if director_count < min_director_count:
        err_path = f'/filing/{filing_type}/parties/roles'
        msg.append({'error': f'Must have a minimum of {min_director_count} Director.', 'path': err_path})

    return msg


def _validate_foreign_jurisdiction(filing_json: dict, filing_type: str, legal_type: str) -> list:
    """Validate continuation in foreign jurisdiction."""
    msg = []
    foreign_jurisdiction = filing_json['filing'][filing_type]['foreignJurisdiction']
    foreign_jurisdiction_path = f'/filing/{filing_type}/foreignJurisdiction'
    if err := validate_foreign_jurisdiction(foreign_jurisdiction, foreign_jurisdiction_path):
        msg.extend(err)
    elif (legal_type == Business.LegalTypes.ULC_CONTINUE_IN.value and
          foreign_jurisdiction['country'] == 'CA' and
          ((region := foreign_jurisdiction.get('region')) and region in ['AB', 'NS'])):
        affidavit_file_key_path = f'{foreign_jurisdiction_path}/affidavitFileKey'
        if file_key := foreign_jurisdiction.get('affidavitFileKey'):
            if err := validate_pdf(file_key, affidavit_file_key_path):
                msg.extend(err)
        else:
            msg.append({'error': 'Affidavit from the directors is required.', 'path': affidavit_file_key_path})

    return msg


def validate_continuation_in_authorization(filing_json: dict, filing_type: str) -> list:
    """Validate continuation in authorization."""
    msg = []
    authorization_path = f'/filing/{filing_type}/authorization'

    expiry_date_path = f'{authorization_path}/expiryDate'
    date_path = f'{authorization_path}/date'
    authorization_date = get_date(filing_json, date_path)
    now = LegislationDatetime.now().date()
    if authorization_date > now:
        msg.append({'error': 'Authorization date cannot be in the future.', 'path': date_path})

    if ((expiry_date := get_date(filing_json, expiry_date_path)) and
            expiry_date < authorization_date):
        msg.append({'error': 'Expiry date should be after Authorization date.', 'path': expiry_date_path})

    for index, file in enumerate(filing_json['filing'][filing_type]['authorization']['files']):
        file_key = file['fileKey']
        file_key_path = f'{authorization_path}/files/{index}/fileKey'
        if err := validate_pdf(file_key, file_key_path):
            msg.extend(err)

    return msg


def validate_continuation_in_court_order(filing: dict, filing_type) -> list:
    """Validate court order."""
    if court_order := filing.get('filing', {}).get(filing_type, {}).get('courtOrder', None):
        court_order_path: Final = f'/filing/{filing_type}/courtOrder'
        err = validate_court_order(court_order_path, court_order)
        if err:
            return err
    return []
