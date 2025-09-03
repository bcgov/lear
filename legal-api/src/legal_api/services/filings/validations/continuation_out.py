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
"""Validation for the Continuation Out filing."""
from http import HTTPStatus
from typing import Dict, Final, Optional

from flask_babel import _ as babel  # noqa: N813, I004, I001; importing camelcase '_' as a name
# noqa: I003
from legal_api.errors import Error
from legal_api.models import Business, ConsentContinuationOut
from legal_api.services import flags
from legal_api.services.filings.validations.common_validations import (
    validate_court_order,
    validate_foreign_jurisdiction,
)
from legal_api.services.utils import get_date
from legal_api.utils.legislation_datetime import LegislationDatetime
# noqa: I003;


def validate(business: Business, filing: Dict) -> Optional[Error]:
    """Validate the Continuation Out filing."""
    if not business or not filing:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid business and filing are required.')}])

    enabled_filings = flags.value('supported-continuation-out-entities').split()
    if business.legal_type not in enabled_filings:
        return Error(HTTPStatus.FORBIDDEN,
                     [{'error': babel(f'{business.legal_type} does not support continuation out filing.')}])

    msg = []
    filing_type = 'continuationOut'

    is_valid_co_date = True
    is_valid_foreign_jurisdiction = True

    if err := validate_continuation_out_date(filing, filing_type):
        msg.extend(err)
        is_valid_co_date = False

    if err := validate_foreign_jurisdiction(filing['filing'][filing_type]['foreignJurisdiction'],
                                            f'/filing/{filing_type}/foreignJurisdiction'):
        msg.extend(err)
        is_valid_foreign_jurisdiction = False

    if is_valid_co_date and is_valid_foreign_jurisdiction:
        msg.extend(validate_active_cco(business, filing, filing_type))

    if court_order := filing.get('filing', {}).get(filing_type, {}).get('courtOrder', None):
        court_order_path: Final = f'/filing/{filing_type}/courtOrder'
        err = validate_court_order(court_order_path, court_order)
        if err:
            msg.extend(err)

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def validate_active_cco(business: Business, filing: Dict, filing_type: str) -> list:
    """Validate active consent continuation out."""
    msg = []
    continuation_out_date_str = filing['filing'][filing_type]['continuationOutDate']
    continuation_out_date = LegislationDatetime.as_legislation_timezone_from_date_str(continuation_out_date_str)

    foreign_jurisdiction = filing['filing'][filing_type]['foreignJurisdiction']
    country_code = foreign_jurisdiction.get('country')
    region = foreign_jurisdiction.get('region')

    continuation_out_date_utc = LegislationDatetime.as_utc_timezone(continuation_out_date)
    ccos = ConsentContinuationOut.get_active_cco(business.id, continuation_out_date_utc, country_code, region)

    active_consent = False
    # Make sure continuation_out_date is on or after consent filing effective date
    for consent in ccos:
        if continuation_out_date.date() >= \
                LegislationDatetime.as_legislation_timezone(consent.filing.effective_date).date():
            active_consent = True
            break

    if not active_consent:
        msg.extend([{'error': 'No active consent continuation out for this date and/or jurisdiction.',
                    'path': f'/filing/{filing_type}/continuationOutDate'}])

    return msg


def validate_continuation_out_date(filing: Dict, filing_type: str) -> list:
    """Validate continuation out date."""
    msg = []
    continuation_out_date_path = f'/filing/{filing_type}/continuationOutDate'
    continuation_out_date = get_date(filing, continuation_out_date_path)

    now = LegislationDatetime.now().date()
    if continuation_out_date > now:
        msg.append({'error': 'Continuation out date must be today or past.',
                    'path': continuation_out_date_path})

    return msg
