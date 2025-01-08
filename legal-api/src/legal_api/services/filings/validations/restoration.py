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
from legal_api.models import Business, Filing, PartyRole
from legal_api.services.filings.validations.common_validations import validate_court_order, validate_name_request
from legal_api.services.filings.validations.incorporation_application import validate_offices
from legal_api.services.utils import get_date, get_str
from legal_api.utils.legislation_datetime import LegislationDatetime
# noqa: I003;

APPROVAL_TYPE_PATH = '/filing/restoration/approvalType'


def validate(business: Business, restoration: Dict) -> Optional[Error]:
    """Validate the Restoration filing."""
    filing_type = 'restoration'
    if not business or not restoration:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid business and filing are required.')}])
    msg = []

    restoration_type = get_str(restoration, '/filing/restoration/type')
    limited_restoration = None
    if restoration_type in ('limitedRestorationExtension', 'limitedRestorationToFull'):
        limited_restoration = Filing.get_most_recent_filing(business.id,
                                                            'restoration',
                                                            'limitedRestoration')
    if restoration_type in ('limitedRestoration', 'limitedRestorationExtension'):
        msg.extend(validate_expiry_date(business, restoration, restoration_type))
    elif restoration_type in ('fullRestoration', 'limitedRestorationToFull'):
        msg.extend(validate_relationship(restoration))

    if restoration_type in ('fullRestoration', 'limitedRestoration', 'limitedRestorationToFull'):
        name_request = restoration.get('filing', {}).get('restoration', {}).get('nameRequest', {})
        if name_request.get('nrNumber', None):
            accepted_request_types = ['RCC', 'RCR', 'BERE', 'RUL']
            msg.extend(validate_name_request(restoration, business.legal_type, filing_type, accepted_request_types))
        else:
            if not name_request.get('legalName', None):
                msg.append({'error': 'Legal name is missing in nameRequest.',
                            'path': '/filing/restoration/nameRequest/legalName'})
    elif restoration_type == 'limitedRestorationExtension' and (
            name_request := restoration.get('filing', {}).get('restoration', {}).get('nameRequest', None)):
        msg.append({'error': 'Cannot change name while extending limited restoration.',
                    'path': '/filing/restoration/nameRequest'})

    msg.extend(validate_party(restoration))
    msg.extend(validate_offices(restoration, filing_type))
    msg.extend(validate_approval_type(restoration, restoration_type, limited_restoration))
    msg.extend(validate_restoration_court_order(restoration, restoration_type, limited_restoration))
    msg.extend(validate_restoration_registrar(restoration, restoration_type))

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def validate_expiry_date(business: Business, filing: Dict, restoration_type: str) -> list:
    """Validate expiry date."""
    msg = []
    expiry_date_path = '/filing/restoration/expiry'

    if expiry_date := get_date(filing, expiry_date_path):
        max_expiry_years = 2
        now = LegislationDatetime.now().date()
        if restoration_type == 'limitedRestorationExtension':
            now = LegislationDatetime.as_legislation_timezone(business.restoration_expiry_date).date()
        greater = now + relativedelta(years=max_expiry_years)
        lesser = now + relativedelta(months=1)
        if expiry_date < lesser or expiry_date > greater:
            msg.append({'error': f'Expiry Date must be between 1 month and {max_expiry_years} years in the future.',
                        'path': expiry_date_path})
    else:
        msg.append({'error': 'Expiry Date is required.', 'path': expiry_date_path})
    return msg


def validate_relationship(filing: dict) -> list:
    """Validate applicant's relationship to the company at the time the company was dissolved."""
    msg = []
    if not filing.get('filing', {}).get('restoration', {}).get('relationships', []):
        msg.append({'error': 'Applicants relationship is required.', 'path': '/filing/restoration/relationships'})

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


def validate_approval_type(filing: dict, restoration_type: str, limited_restoration: Filing) -> list:
    """Validate approval type."""
    msg = []
    approval_type = get_str(filing, APPROVAL_TYPE_PATH)
    if restoration_type in ('limitedRestorationExtension', 'limitedRestorationToFull') and \
            limited_restoration.approval_type == 'courtOrder' and approval_type != 'courtOrder':
        msg.append({'error': 'Must provide approval type with value of courtOrder.',
                    'path': APPROVAL_TYPE_PATH})
    return msg


def validate_restoration_court_order(filing: dict, restoration_type: str, limited_restoration: Filing) -> list:
    """Validate court order."""
    msg = []
    if court_order := filing.get('filing', {}).get('restoration', {}).get('courtOrder', None):
        court_order_path: Final = '/filing/restoration/courtOrder'
        if err := validate_court_order(court_order_path, court_order):
            msg.extend(err)
    elif restoration_type in ('fullRestoration', 'limitedRestoration') and \
            get_str(filing, APPROVAL_TYPE_PATH) == 'courtOrder':
        msg.append({'error': 'Must provide Court Order Number.', 'path': '/filing/restoration/courtOrder/fileNumber'})
    elif restoration_type in ('limitedRestorationExtension', 'limitedRestorationToFull') and \
            limited_restoration.approval_type == 'courtOrder' and \
            not court_order:
        msg.append({'error': 'Must provide Court Order Number.', 'path': '/filing/restoration/courtOrder/fileNumber'})

    return msg


def validate_restoration_registrar(filing: dict, restoration_type: str) -> list:
    """Validate fields for when approval type is 'registrar'.

    Application and notice date validation is only required for fullRestoration & limitedRestoration
    """
    msg = []
    if get_str(filing, APPROVAL_TYPE_PATH) == 'registrar' and \
            restoration_type in ('fullRestoration', 'limitedRestoration'):
        application_date = filing.get('filing', {}).get('restoration', {}).get('applicationDate', None)
        if not application_date:
            msg.append({'error': 'Must provide notice of application mailed date.',
                        'path': '/filing/restoration/applicationDate'})
        notice_date = filing.get('filing', {}).get('restoration', {}).get('noticeDate', None)
        if not notice_date:
            msg.append({'error': 'Must provide BC Gazette published date.', 'path': '/filing/restoration/noticeDate'})

    return msg
