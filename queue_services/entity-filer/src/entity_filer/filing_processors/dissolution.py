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
from datetime import datetime
from typing import Dict

import dpath
import sentry_sdk
from entity_queue_common.service_utils import QueueException, logger
from legal_api.models import Business, Document, Filing
from legal_api.models.document import DocumentType
from legal_api.services.filings.validations.dissolution import DissolutionTypes
from legal_api.services.minio import MinioService

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors.filing_components import create_office, filings
from entity_filer.filing_processors.filing_components.parties import update_parties
from entity_filer.utils import replace_file_with_certified_copy


def process(business: Business, filing: Dict, filing_rec: Filing, filing_meta: FilingMeta):
    """Render the dissolution filing unto the model objects."""
    if not (dissolution_filing := filing.get('dissolution')):
        logger.error('Could not find Dissolution in: %s', filing)
        raise QueueException(f'legal_filing:Dissolution missing from {filing}')

    logger.debug('processing dissolution: %s', filing)

    filing_meta.dissolution = {}
    dissolution_type = dpath.util.get(filing, '/dissolution/dissolutionType')

    # hasLiabilities can be derived from dissolutionStatementType
    # FUTURE: remove hasLiabilities from schema
    # has_liabilities = filing['dissolution'].get('hasLiabilities')

    # should we save dissolution_statement_type in businesses table?
    # dissolution_statement_type = filing['dissolution'].get('dissolutionStatementType')
    business.dissolution_date = filing_rec.effective_date
    business.state = Business.State.HISTORICAL
    business.state_filing_id = filing_rec.id

    # add custodial party if in filing
    if parties := dissolution_filing.get('parties'):
        update_parties(business, parties, filing_rec, False)

    # add custodial office if provided
    if custodial_office := dissolution_filing.get('custodialOffice'):
        if office := create_office(business, 'custodialOffice', custodial_office):
            business.offices.append(office)
        else:
            logger.error('Could not create custodial office for Dissolution in: %s', filing)
            sentry_sdk.capture_message(
                f'Queue Error: Could not create custodial office for Dissolution filing:{filing.id}',
                level='error')

    filing_rec.order_details = dissolution_filing.get('details')

    # update court order, if any is present
    with suppress(IndexError, KeyError, TypeError):
        court_order_json = dpath.util.get(dissolution_filing, '/courtOrder')
        filings.update_filing_court_order(filing_rec, court_order_json)

    if business.legal_type == Business.LegalTypes.COOP:
        _update_cooperative(dissolution_filing, business, filing_rec, dissolution_type)

    with suppress(IndexError, KeyError, TypeError):
        filing_meta.dissolution = {**filing_meta.dissolution,
                                   **{'dissolutionType': dissolution_type},
                                   **{'dissolutionDate': datetime.date(filing_rec.effective_date).isoformat()}}


def _update_cooperative(dissolution_filing: Dict, business: Business, filing: Filing, dissolution_type):
    """Update COOP data.

    This should not be updated for administrative dissolution
    """
    if dissolution_type == DissolutionTypes.ADMINISTRATIVE:
        return

    # create certified copy for affidavit document
    affidavit_file_key = dissolution_filing.get('affidavitFileKey')
    affidavit_file = MinioService.get_file(affidavit_file_key)
    affidavit_file_name = dissolution_filing.get('affidavitFileName')
    replace_file_with_certified_copy(affidavit_file.data, business, affidavit_file_key, filing.effective_date)

    document = Document()
    document.type = DocumentType.AFFIDAVIT.value
    document.file_key = affidavit_file_key
    document.file_name = affidavit_file_name
    document.content_type = document.file_name.split('.')[-1]
    document.business_id = business.id
    document.filing_id = filing.id
    business.documents.append(document)


def post_process(business: Business, filing: Filing, correction: bool = False):  # pylint: disable=W0613
    """Post processing activities for incorporations.

    THIS SHOULD NOT ALTER THE MODEL
    """
