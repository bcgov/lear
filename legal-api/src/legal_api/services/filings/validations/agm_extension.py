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
"""Validation for the Agm Extension filing."""
from http import HTTPStatus
from typing import Dict, Optional

from dateutil.relativedelta import relativedelta
from flask_babel import _ as babel  # noqa: N813, I004, I001; importing camelcase '_' as a name
# noqa: I003
from legal_api.errors import Error
from legal_api.models import Business
from legal_api.services import flags
from legal_api.utils.legislation_datetime import LegislationDatetime
from ...utils import get_bool, get_int, get_str  # noqa: I003
# noqa: I003

AGM_EXTENSION_PATH = '/filing/agmExtension'
EXPIRED_ERROR = 'Allotted period to request extension has expired.'
GRANT_FAILURE = 'Fail to grant extension.'


def validate(business: Business, filing: Dict) -> Optional[Error]:
    """Validate the AGM Extension filing."""
    if not business or not filing:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid business and filing are required.')}])

    enabled_filings = flags.value('support-agm-extension-entities').split()
    if enabled_filings and business.legal_type not in enabled_filings:
        return Error(HTTPStatus.FORBIDDEN,
                     [{'error': babel(f'{business.legal_type} does not support agm extension filing.')}])
    msg = []

    is_first_agm = get_bool(filing, f'{AGM_EXTENSION_PATH}/isFirstAgm')

    if is_first_agm:
        msg.extend(first_agm_validation(business, filing))
    else:
        msg.extend(subsequent_agm_validation(filing))

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)

    return None


def first_agm_validation(business: Business, filing: Dict) -> list:
    """Validate filing for first AGM Extension."""
    msg = []

    has_ext_req_for_agm_year = get_bool(filing, f'{AGM_EXTENSION_PATH}/extReqForAgmYear')
    founding_date = LegislationDatetime.as_legislation_timezone_from_date(business.founding_date).date()

    if not has_ext_req_for_agm_year:
        # first AGM, first extension
        now = LegislationDatetime.datenow()
        latest_ext_date = founding_date + relativedelta(months=18, days=5)
        if now > latest_ext_date:
            msg.append({'error': EXPIRED_ERROR,
                        'path': f'{AGM_EXTENSION_PATH}/isFirstAgm'})
        else:
            total_approved_ext = get_int(filing, f'{AGM_EXTENSION_PATH}/totalApprovedExt')
            extension_duration = get_int(filing, f'{AGM_EXTENSION_PATH}/extensionDuration')
            if total_approved_ext != 6 or extension_duration != 6:
                msg.append({'error': babel(GRANT_FAILURE)})
    else:
        # first AGM, second extension or more
        if not (curr_ext_expire_date_str := get_str(filing, f'{AGM_EXTENSION_PATH}/expireDateCurrExt')):
            return [{'error': 'Expiry date for current extension is required.',
                     'path': f'{AGM_EXTENSION_PATH}/expireDateCurrExt'}]

        curr_ext_expire_date =\
            LegislationDatetime.as_legislation_timezone_from_date_str(curr_ext_expire_date_str).date()
        allowable_ext_date = founding_date + relativedelta(months=30)
        now = LegislationDatetime.datenow()
        if curr_ext_expire_date >= allowable_ext_date:
            msg.append({'error': 'Company has received the maximum 12 months of allowable extensions.',
                        'path': f'{AGM_EXTENSION_PATH}/expireDateCurrExt'})
        elif now > curr_ext_expire_date + relativedelta(days=5):
            msg.append({'error': EXPIRED_ERROR,
                        'path': f'{AGM_EXTENSION_PATH}/expireDateCurrExt'})
        else:
            total_approved_ext = get_int(filing, f'{AGM_EXTENSION_PATH}/totalApprovedExt')
            extension_duration = get_int(filing, f'{AGM_EXTENSION_PATH}/extensionDuration')

            baseline = founding_date + relativedelta(months=18)
            expected_total_approved_ext, expected_extension_duration =\
                _calculate_granted_ext(curr_ext_expire_date, baseline)

            if expected_total_approved_ext != total_approved_ext or\
                    expected_extension_duration != extension_duration:
                msg.append({'error': babel(GRANT_FAILURE)})

    return msg


def subsequent_agm_validation(filing: Dict) -> list:
    """Validate filing for subsequent AGM Extension."""
    msg = []

    has_ext_req_for_agm_year = filing['filing']['agmExtension']['extReqForAgmYear']
    if not (prev_agm_ref_date_str := get_str(filing, f'{AGM_EXTENSION_PATH}/prevAgmRefDate')):
        return [{'error': 'Previous AGM date or a reference date is required.',
                 'path': f'{AGM_EXTENSION_PATH}/prevAgmRefDate'}]

    prev_agm_ref_date =\
        LegislationDatetime.as_legislation_timezone_from_date_str(prev_agm_ref_date_str).date()

    if not has_ext_req_for_agm_year:
        # subsequent AGM, first extension
        now = LegislationDatetime.datenow()
        latest_ext_date = prev_agm_ref_date + relativedelta(months=15, days=5)
        if now > latest_ext_date:
            msg.append({'error': EXPIRED_ERROR,
                        'path': f'{AGM_EXTENSION_PATH}/prevAgmRefDate'})
        else:
            total_approved_ext = get_int(filing, f'{AGM_EXTENSION_PATH}/totalApprovedExt')
            extension_duration = get_int(filing, f'{AGM_EXTENSION_PATH}/extensionDuration')
            if total_approved_ext != 6 or extension_duration != 6:
                msg.append({'error': babel(GRANT_FAILURE)})
    else:
        # subsequent AGM, second extension or more
        if not (curr_ext_expire_date_str := get_str(filing, f'{AGM_EXTENSION_PATH}/expireDateCurrExt')):
            return [{'error': 'Expiry date for current extension is required.',
                     'path': f'{AGM_EXTENSION_PATH}/expireDateCurrExt'}]

        curr_ext_expire_date =\
            LegislationDatetime.as_legislation_timezone_from_date_str(curr_ext_expire_date_str).date()

        allowable_ext_date = prev_agm_ref_date + relativedelta(months=12)
        now = LegislationDatetime.datenow()

        if curr_ext_expire_date >= allowable_ext_date:
            msg.append({'error': 'Company has received the maximum 12 months of allowable extensions.',
                        'path': f'{AGM_EXTENSION_PATH}/expireDateCurrExt'})
        elif now > curr_ext_expire_date + relativedelta(days=5):
            msg.append({'error': EXPIRED_ERROR,
                        'path': f'{AGM_EXTENSION_PATH}/expireDateCurrExt'})
        else:
            total_approved_ext = get_int(filing, f'{AGM_EXTENSION_PATH}/totalApprovedExt')
            extension_duration = get_int(filing, f'{AGM_EXTENSION_PATH}/extensionDuration')

            expected_total_approved_ext, expected_extension_duration =\
                _calculate_granted_ext(curr_ext_expire_date, prev_agm_ref_date)

            if expected_total_approved_ext != total_approved_ext or\
                    expected_extension_duration != extension_duration:
                msg.append({'error': babel(GRANT_FAILURE)})

    return msg


def _calculate_granted_ext(curr_ext_expire_date, baseline_date) -> tuple:
    """Calculate expected total approved extension and extension duration."""
    total_approved_ext = relativedelta(curr_ext_expire_date, baseline_date).months
    extension_duration = min(12-total_approved_ext, 6)
    total_approved_ext += extension_duration

    return total_approved_ext, extension_duration
