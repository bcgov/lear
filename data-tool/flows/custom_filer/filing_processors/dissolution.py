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
from datetime import datetime
from contextlib import suppress
from typing import Dict

import dpath
import sentry_sdk
from legal_api.models import Business, Document, Filing, Comment
from legal_api.models.document import DocumentType
from legal_api.services.minio import MinioService

from ..filing_meta import FilingMeta
from .filing_components.parties import update_parties
from .filing_components import filings


def process(business: Business,
            filing: Dict,
            filing_rec: Filing,
            filing_meta: FilingMeta,
            filing_event_data: Dict):
    """Render the dissolution filing unto the model objects."""
    if not (dissolution_filing := filing.get('dissolution')):
        print(f'legal_filing:Dissolution missing from {filing}')

    print('processing dissolution: %s', filing)

    filing_meta.dissolution = {}
    dissolution_type = dpath.util.get(filing, '/dissolution/dissolutionType')

    # hasLiabilities can be derived from dissolutionStatementType
    # FUTURE: remove hasLiabilities from schema
    # has_liabilities = filing['dissolution'].get('hasLiabilities')

    # should we save dissolution_statement_type in businesses table?
    # dissolution_statement_type = filing['dissolution'].get('dissolutionStatementType')
    dissolution_date = filing_event_data['e_trigger_dts_pacific']
    business.dissolution_date = dissolution_date if dissolution_date else filing_rec.effective_date
    business.state = Business.State.HISTORICAL
    business.state_filing_id = filing_rec.id

    # add custodial party if in filing
    if parties := dissolution_filing.get('parties'):
        update_parties(business, parties, filing_rec, False)

    # only dealing with voluntary dissolutions for now so commenting this out
    # filings.update_filing_order_details(filing_rec, filing_event_data)

    with suppress(IndexError, KeyError, TypeError):
        filing_meta.dissolution = {**filing_meta.dissolution,
                                   **{'dissolutionType': dissolution_type},
                                   **{'dissolutionDate': datetime.date(business.dissolution_date).isoformat()}}

    if lt_notation := filing_event_data.get('lt_notation'):
        filing_rec.comments.append(
            Comment(
                comment=lt_notation,
                staff_id=filing_rec.submitter_id
            )
        )

    # Note: custodial office, court order and coop specific code and admin dissolution details has been removed as not req'd


def post_process(business: Business, filing: Filing, correction: bool = False):  # pylint: disable=W0613
    """Post processing activities for incorporations.

    THIS SHOULD NOT ALTER THE MODEL
    """
