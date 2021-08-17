# Copyright © 2021 Province of British Columbia
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
"""File processing rules and actions for Dissolution and Liquidation filings."""
from contextlib import suppress
from typing import Dict

import dpath
import sentry_sdk
from entity_queue_common.service_utils import QueueException, logger
from legal_api.models import Business, Filing
from legal_api.utils.datetime import datetime

from entity_filer.filing_processors.filing_components import create_office
from entity_filer.filing_processors.filing_components.parties import update_parties
from entity_filer.filing_processors.filing_components import (
    filings,
)

def process(business: Business, filing: Dict):
    """Render the dissolution filing unto the model objects."""
    if not (dissolution_filing := filing.get('dissolution')):
        logger.error('Could not find Dissolution in: %s', filing)
        raise QueueException(f'legal_filing:Dissolution missing from {filing}')

    logger.debug('processing dissolution: %s', filing)
    dissolution_date = datetime.fromisoformat(dissolution_filing.get('dissolutionDate'))
    # Currently we don't use this for anything?
    # has_liabilities = filing['dissolution'].get('hasLiabilities')
    business.dissolution_date = dissolution_date

    # remove all directors and add custodial party if in filing
    if parties := dissolution_filing.get('parties'):
        update_parties(business, parties)

    # add custodial office if provided
    if custodial_office := dissolution_filing.get('custodialOffice'):
        if office := create_office(business, 'custodialOffice', custodial_office):
            business.offices.append(office)
        else:
            logger.error('Could not create custodial office for Dissolution in: %s', filing)
            sentry_sdk.capture_message(
                f'Queue Error: Could not create custodial office for Dissolution filing:{filing.id}',
                level='error')

    # update court order, if any is present
    with suppress(IndexError, KeyError, TypeError):
        court_order_json = dpath.util.get(dissolution_filing, '/courtOrder')
        filings.update_filing_court_order(filing, court_order_json)


def post_process(business: Business, filing: Filing, correction: bool = False):  # pylint: disable=W0613
    """Post processing activities for incorporations.

    THIS SHOULD NOT ALTER THE MODEL
    """
