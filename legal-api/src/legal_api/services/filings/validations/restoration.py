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
"""Validation for the Restoration filing."""
from http import HTTPStatus
from typing import Dict, Final, Optional

from dateutil.relativedelta import relativedelta
from flask_babel import _ as babel  # noqa: N813, I004, I001; importing camelcase '_' as a name

from legal_api.errors import Error
from legal_api.models import Business, PartyRole
from legal_api.services.filings.validations.common_validations import validate_court_order, validate_name_request
from legal_api.services.filings.validations.incorporation_application import validate_offices
from legal_api.services.utils import get_date, get_str
from legal_api.utils.legislation_datetime import LegislationDatetime
# noqa: I003;


def validate(business: Business, restoration: Dict) -> Optional[Error]:
    """Validate the Restoration filing."""
    filing_type = 'restoration'
    if not business or not restoration:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid business and filing are required.')}])
    msg = []

    restoration_type = get_str(restoration, '/filing/restoration/type')
    if restoration_type in ('limitedRestoration', 'limitedRestorationExtension'):
        msg.extend(validate_expiry_date(restoration))

    msg.extend(validate_name_request(restoration, business.legal_type, filing_type))
    msg.extend(validate_party(restoration))
    msg.extend(validate_offices(restoration, filing_type))

    msg.extend(validate_restoration_court_order(restoration, restoration_type))

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def validate_expiry_date(filing: Dict) -> list:
    """Validate expiry date."""
    # Between 1 month and 2 years in the future
    msg = []
    expiry_date_path = '/filing/restoration/expiryDate'
    expiry_date = get_date(filing, expiry_date_path)
    now = LegislationDatetime.now().date()
    greater = now + relativedelta(years=2)
    lesser = now + relativedelta(months=1)
    if expiry_date < lesser or expiry_date > greater:
        msg.append({'error': 'Expiry Date must be between 1 month and 2 years in the future.',
                    'path': expiry_date_path})

    return msg


def validate_party(filing: Dict) -> list:
    """Validate party."""
    msg = []
    roles = []
    parties = filing['filing']['restoration']['parties']
    for party in parties:  # pylint: disable=too-many-nested-blocks;  # noqa: E501
        for role in party.get('roles', []):
            role_type = role.get('roleType').lower().replace(' ', '_')
            roles.append(role_type)
            if role_type != PartyRole.RoleTypes.APPLICANT.value:
                msg.append({'error': 'Role can only be Applicant.', 'path': '/filing/restoration/parties/roles'})

    if len(roles) == 0:
        msg.append({'error': 'Must have an Applicant.', 'path': '/filing/restoration/parties'})

    return msg


def validate_restoration_court_order(filing: dict, restoration_type: str) -> list:
    """Validate court order."""
    msg = []
    if court_order := filing.get('filing', {}).get('restoration', {}).get('courtOrder', None):
        court_order_path: Final = '/filing/restoration/courtOrder'
        if err := validate_court_order(court_order_path, court_order):
            msg.extend(err)
    elif restoration_type in ('fullRestoration', 'limitedRestoration') and \
            get_str(filing, '/filing/restoration/approvalType') == 'courtOrder':
        msg.append({'error': 'Must provide Court Order Number.', 'path': '/filing/restoration/courtOrder/fileNumber'})

    return msg
