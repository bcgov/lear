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
"""Validation for the Special Resolution filing."""
from http import HTTPStatus
from typing import Dict, Optional

from flask_babel import _

from legal_api.errors import Error
from legal_api.models import Business
from legal_api.services.utils import get_date, get_str
from legal_api.utils.datetime import datetime


def validate(business: Business, filing_json: Dict) -> Error:
    """Validate the Special Resolution filing."""
    if not business or not filing_json:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': _('A valid business and filing are required.')}])
    msg = []

    err = validate_resolution_content(filing_json)
    msg.extend(err)

    err = validate_resolution_date(business, filing_json)
    msg.extend(err)

    err = validate_signing_date(filing_json)
    msg.extend(err)

    err = validate_signatory_name(filing_json)
    msg.extend(err)

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def validate_resolution_content(filing_json, filing_type: str = 'specialResolution'):
    """Validate resolution content."""
    msg = []
    resolution_path = f'/filing/{filing_type}/resolution'
    resolution_content = get_str(filing_json, resolution_path)

    if not resolution_content:
        msg.append({'error': _('Resolution must be provided.'),
                    'path': resolution_path})
        return msg

    if len(resolution_content) > 2097152:
        msg.append({'error': _('Resolution must be 2MB or less.'),
                    'path': resolution_path})
    return msg


def validate_resolution_date(business: Business, filing_json: Dict) -> Optional[list]:
    """Validate resolution date."""
    msg = []
    resolution_date_path = '/filing/specialResolution/resolutionDate'
    resolution_date = get_date(filing_json, resolution_date_path)

    if not resolution_date:
        msg.append({'error': _('Resolution date is required.'), 'path': resolution_date_path})
        return msg

    if resolution_date < business.founding_date.date():
        msg.append({'error': _('Resolution date cannot be earlier than the incorporation date.'),
                    'path': resolution_date_path})
        return msg

    if resolution_date > datetime.utcnow().date():
        msg.append({'error': _('Resolution date cannot be in the future.'),
                    'path': resolution_date_path})
        return msg

    return msg


def validate_signing_date(filing_json: Dict, filing_type: str = 'specialResolution') -> Optional[list]:
    """Validate signing date."""
    msg = []
    signing_date_path = f'/filing/{filing_type}/signingDate'
    signing_date = get_date(filing_json, signing_date_path)
    resolution_date_path = f'/filing/{filing_type}/resolutionDate'
    resolution_date = get_date(filing_json, resolution_date_path)

    if not signing_date:
        msg.append({'error': _('Signing date is required.'), 'path': signing_date_path})
        return msg

    if signing_date > datetime.utcnow().date():
        msg.append({'error': _('Signing date cannot be in the future.'),
                    'path': signing_date_path})
        return msg

    if not resolution_date:
        return msg

    if signing_date < resolution_date:
        msg.append({'error': _('Signing date cannot be before the resolution date.'),
                    'path': signing_date_path})
        return msg

    return msg


def validate_signatory_name(filing_json: Dict, filing_type: str = 'specialResolution') -> Optional[list]:
    """Validate signatory name."""
    msg = []
    signatory_given_name_path = f'/filing/{filing_type}/signatory/givenName'
    signatory_family_name_path = f'/filing/{filing_type}/signatory/familyName'
    signatory_given_name = get_str(filing_json, signatory_given_name_path)
    signatory_family_name = get_str(filing_json, signatory_family_name_path)

    if not signatory_given_name:
        msg.append({'error': _('Signatory given name is required.'), 'path': signatory_given_name_path})

    if not signatory_family_name:
        msg.append({'error': _('Signatory family name is required.'), 'path': signatory_family_name_path})

    return msg
