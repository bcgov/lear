# Copyright © 2025 Province of British Columbia
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
"""File processing rules and actions for the put back off filing."""

from contextlib import suppress
from typing import Dict

import dpath
from entity_queue_common.service_utils import QueueException, logger
from legal_api.models import Business, Filing
from legal_api.utils.legislation_datetime import LegislationDatetime

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors.filing_components import filings


def process(business: Business, filing: Dict, filing_rec: Filing, filing_meta: FilingMeta):
    """Render the put back off filing unto the model objects."""
    if not (put_back_off_filing := filing.get('putBackOff')):
        logger.error('Could not find putBackOff in: %s', filing)
        raise QueueException(f'legal_filing:putBackOff missing from {filing}')

    logger.debug('processing putBackOff: %s', filing)

    # update court order, if any is present
    with suppress(IndexError, KeyError, TypeError):
        court_order_json = dpath.util.get(put_back_off_filing, '/courtOrder')
        filings.update_filing_court_order(filing_rec, court_order_json)

    filing_rec.order_details = put_back_off_filing.get('details')

    if business.restoration_expiry_date:
        filing_meta.put_back_off = {
          'reason': 'Limited Restoration Expired',
          'expiryDate': LegislationDatetime.format_as_legislation_date(business.restoration_expiry_date)
        }

    # change business state to historical
    business.state = Business.State.HISTORICAL
    business.state_filing_id = filing_rec.id
    business.restoration_expiry_date = None
