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
"""Validation for the Annual Report filing."""
from datetime import datetime
from http import HTTPStatus
from typing import Dict, List, Tuple

import datedelta
from flask_babel import _

from legal_api.errors import Error
from legal_api.models import Business

from ..utils import get_date


def requires_agm(business: Business) -> bool:
    """Determine if AGM validation is required for AR."""
    # FUTURE: This is not dynamic enough
    agm_arr = ['CP', 'XP']
    return business.legal_type in agm_arr


def validate(business: Business, annual_report: Dict) -> Error:
    """Validate the annual report JSON."""
    if not business or not annual_report:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': _('A valid business and filing are required.')}])

    err = validate_ar_year(business=business,
                           current_annual_report=annual_report)
    if err:
        return err

    if requires_agm(business):
        err = validate_agm_year(business=business,
                                annual_report=annual_report)

    if err:
        return err

    return None


def validate_ar_year(*, business: Business, current_annual_report: Dict) -> Error:
    """Validate that the annual report year is valid."""
    ar_date = get_date(current_annual_report,
                       'filing/annualReport/annualReportDate')
    if not ar_date:
        return Error(HTTPStatus.BAD_REQUEST,
                     [{'error': _('Annual Report Date must be a valid date.'),
                       'path': 'filing/annualReport/annualReportDate'}])

    # The AR Date cannot be in the future (eg. before now() )
    if ar_date > datetime.utcnow().date():
        return Error(HTTPStatus.BAD_REQUEST,
                     [{'error': _('Annual Report Date cannot be in the future.'),
                       'path': 'filing/annualReport/annualReportDate'}])

    # The AR Date cannot be before the last AR Filed
    # or in or before the foundingDate
    expected_date = business.founding_date + datedelta.YEAR

    if business.last_ar_date:
        expected_date = business.last_ar_date + datedelta.YEAR

    if ar_date.year < expected_date.year:
        return Error(HTTPStatus.BAD_REQUEST,
                     [{'error': _('Annual Report Date cannot be before a previous Annual Report or the Founding Date.'),
                       'path': 'filing/annualReport/annualReportDate'}])

    # AR Date must be the next contiguous year, from either the last AR or foundingDate
    if ar_date.year > expected_date.year:
        return Error(HTTPStatus.BAD_REQUEST,
                     [{'error': _('Annual Report Date must be the next Annual Report in contiguous order.'),
                       'path': 'filing/annualReport/annualReportDate'}])

    return None


# pylint: disable=too-many-return-statements,unused-argument; lots of rules to individually return from
def validate_agm_year(*, business: Business, annual_report: Dict) -> Tuple[int, List[Dict]]:
    """Validate the AGM year."""
    ar_date = get_date(annual_report,
                       'filing/annualReport/annualReportDate')
    if not ar_date:
        return Error(HTTPStatus.BAD_REQUEST,
                     [{'error': _('Annual Report Date must be a valid date.'),
                       'path': 'filing/annualReport/annualReportDate'}])

    submission_date = get_date(annual_report,
                               'filing/header/date')
    if not submission_date:
        return Error(HTTPStatus.BAD_REQUEST,
                     [{'error': _('Submission date must be a valid date.'),
                       'path': 'filing/header/date'}])

    agm_date = get_date(annual_report,
                        'filing/annualReport/annualGeneralMeetingDate')

    if ar_date.year == submission_date.year \
            and agm_date is None:
        return Error(HTTPStatus.BAD_REQUEST,
                     [{'error': _('Annual General Meeting Date must be a valid date when '
                                  'submitting an Annual Report in the current year.'),
                       'path': 'filing/annualReport/annualGeneralMeetingDate'}])

    # # ar filed for previous year, agm skipped, warn of pending dissolution
    # if agm_date is None and business.last_agm_date.year == (ar_date - datedelta.datedelta(years=1)).year:
    #     return Error(HTTPStatus.OK,
    #                  [{'warning': _('Annual General Meeting Date (AGM) is being skipped. '
    #                                 'If another AGM is skipped, the business will be dissolved.'),
    #                    'path': 'filing/annualReport/annualGeneralMeetingDate'}])
    #
    # # ar filed for previous year, agm skipped, warn of pending dissolution
    # if agm_date is None and business.last_agm_date.year <= (ar_date - datedelta.datedelta(years=2)).year:
    #     return Error(HTTPStatus.OK,
    #                  [{'warning': _('Annual General Meeting Date (AGM) is being skipped. '
    #                                 'The business will be dissolved, unless an extension and an AGM are held.'),
    #                    'path': 'filing/annualReport/annualGeneralMeetingDate'}])
    #
    return None
