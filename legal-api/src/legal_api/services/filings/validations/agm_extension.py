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
from legal_api.utils.legislation_datetime import LegislationDatetime
# noqa: I003


def validate(business: Business, filing: Dict) -> Optional[Error]:
    """Validate the Agm Extension filing."""
    if not business or not filing:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid business and filing are required.')}])

    msg = []

    is_first_agm = filing['filing']['agmExtension']['isFirstAgm']

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

    agm_extension_path = '/filing/agmExtension'
    has_ext_req_for_agm_year = filing['filing']['agmExtension']['extReqForAgmYear']
    founding_date = business.founding_date

    if not has_ext_req_for_agm_year:
        # first AGM, first extension
        now = LegislationDatetime.now()
        latest_ext_date = founding_date + relativedelta(months=18, days=5)
        if now > latest_ext_date:
            msg.append({'error': 'Allotted period to request extension has expired.',
                        'path': f'{agm_extension_path}/isFirstAgm'})
    else:
        # first AGM, second extension or more
        curr_ext_expire_date_str = filing['filing']['agmExtension']['expireDateCurrExt']
        curr_ext_expire_date = LegislationDatetime.as_legislation_timezone_from_date_str(curr_ext_expire_date_str)
        allowable_ext_date = founding_date + relativedelta(months=30)
        now = LegislationDatetime.now()
        if curr_ext_expire_date >= allowable_ext_date:
            msg.append({'error': 'Company has received the maximum 12 months of allowable extensions.',
                        'path': f'{agm_extension_path}/expireDateCurrExt'})
        elif now > curr_ext_expire_date + relativedelta(days=5):
            msg.append({'error': 'Allotted period to request extension has expired.',
                        'path': f'{agm_extension_path}/expireDateCurrExt'})

    return msg


def subsequent_agm_validation(filing: Dict) -> list:
    """Validate filing for subsequent AGM Extension."""
    msg = []
    agm_extension_path = '/filing/agmExtension'

    has_ext_req_for_agm_year = filing['filing']['agmExtension']['extReqForAgmYear']
    prev_agm_ref_date_str = filing['filing']['agmExtension']['prevAgmRefDate']
    prev_agm_ref_date = LegislationDatetime.as_legislation_timezone_from_date_str(prev_agm_ref_date_str)

    if not has_ext_req_for_agm_year:
        # subsequent AGM, first extension
        now = LegislationDatetime.now()
        latest_ext_date = prev_agm_ref_date + relativedelta(months=15, days=5)
        if now > latest_ext_date:
            msg.append({'error': 'Allotted period to request extension has expired.',
                        'path': f'{agm_extension_path}/prevAgmRefDate'})
    else:
        # subsequent AGM, second extension or more
        curr_ext_expire_date_str = filing['filing']['agmExtension']['expireDateCurrExt']
        curr_ext_expire_date = LegislationDatetime.as_legislation_timezone_from_date_str(curr_ext_expire_date_str)

        allowable_ext_date = prev_agm_ref_date + relativedelta(months=12)
        now = LegislationDatetime.now()

        if curr_ext_expire_date >= allowable_ext_date:
            msg.append({'error': 'Company has received the maximum 12 months of allowable extensions.',
                        'path': f'{agm_extension_path}/expireDateCurrExt'})
        elif now > curr_ext_expire_date + relativedelta(days=5):
            msg.append({'error': 'Allotted period to request extension has expired.',
                        'path': f'{agm_extension_path}/expireDateCurrExt'})

    return msg
