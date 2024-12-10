# Copyright © 2022 Province of British Columbia
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
"""File processing rules and actions for the put back on filing."""

from contextlib import suppress
from typing import Dict

import dpath
from entity_queue_common.service_utils import QueueException, logger
from legal_api.models import Business, Filing, Office, OfficeType, db

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors import restoration
from entity_filer.filing_processors.filing_components import filings


def process(business: Business, filing: Dict, filing_rec: Filing, filing_meta: FilingMeta):
    """Render the put back on filing unto the model objects."""
    if not (put_back_on_filing := filing.get('putBackOn')):
        logger.error('Could not find putBackOn in: %s', filing)
        raise QueueException(f'legal_filing:putBackOn missing from {filing}')

    logger.debug('processing putBackOn: %s', filing)

    # update court order, if any is present
    with suppress(IndexError, KeyError, TypeError):
        court_order_json = dpath.util.get(put_back_on_filing, '/courtOrder')
        filings.update_filing_court_order(filing_rec, court_order_json)

    filing_rec.order_details = put_back_on_filing.get('details')

    restoration.cease_custodian(business)

    custodial_office = (db.session.query(Office).
                        filter(Office.business_id == business.id).
                        filter(Office.office_type == OfficeType.CUSTODIAL).
                        one_or_none())
    if custodial_office:
        business.offices.remove(custodial_office)

    business.state = Business.State.ACTIVE
    business.dissolution_date = None
    business.state_filing_id = filing_rec.id
