# Copyright © 2025 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""File processing rules and actions for Dissolution and Liquidation filings."""
from contextlib import suppress
from typing import Dict

import dpath

from business_filer.exceptions import QueueException
from flask import current_app
from business_model.models import BatchProcessing, Business, Document, Filing, db
from business_model.models.document import DocumentType
from business_filer.common.filing import DissolutionTypes
# from legal_api.services.minio import MinioService
# from legal_api.services.pdf_service import RegistrarStampData
from business_filer.common.datetime import datetime
from business_filer.common.legislation_datetime import LegislationDatetime

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import create_office, filings
from business_filer.filing_processors.filing_components.parties import update_parties
# from business_filer.utils import replace_file_with_certified_copy


# pylint: disable=too-many-locals
def process(business: Business, filing: Dict, filing_rec: Filing, filing_meta: FilingMeta, flag_on: bool = False):
    """Render the dissolution filing unto the model objects."""
    if not (dissolution_filing := filing.get('dissolution')):
        current_app.logger.error('Could not find Dissolution in: %s', filing)
        raise QueueException(f'legal_filing:Dissolution missing from {filing}')

    current_app.logger.debug('processing dissolution: %s', filing)

    filing_meta.dissolution = {}
    dissolution_type = dpath.util.get(filing, '/dissolution/dissolutionType')

    # hasLiabilities can be derived from dissolutionStatementType
    # FUTURE: remove hasLiabilities from schema
    # has_liabilities = filing['dissolution'].get('hasLiabilities')

    # should we save dissolution_statement_type in businesses table?
    # dissolution_statement_type = filing['dissolution'].get('dissolutionStatementType')
    dissolution_date = filing_rec.effective_date
    if dissolution_type == DissolutionTypes.VOLUNTARY and \
            business.legal_type in (Business.LegalTypes.SOLE_PROP.value,
                                    Business.LegalTypes.PARTNERSHIP.value):
        dissolution_date_str = dissolution_filing.get('dissolutionDate')
        dissolution_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(dissolution_date_str)
    business.dissolution_date = dissolution_date

    if dissolution_type == DissolutionTypes.ADMINISTRATIVE and (amalgamation := business.amalgamation.one_or_none()):
        for amalgamating_business in amalgamation.amalgamating_businesses.all():
            db.session.delete(amalgamating_business)
        db.session.delete(amalgamation)

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
            current_app.logger.error('Could not create custodial office for Dissolution in: %s', filing)
            current_app.logger.info(
                f'Queue Error: Could not create custodial office for Dissolution filing:{filing.id}',
                level='error')

    filing_rec.order_details = dissolution_filing.get('details')

    # update court order, if any is present
    with suppress(IndexError, KeyError, TypeError):
        court_order_json = dpath.util.get(dissolution_filing, '/courtOrder')
        filings.update_filing_court_order(filing_rec, court_order_json)

    with suppress(IndexError, KeyError, TypeError):
        filing_meta.dissolution = {
            **filing_meta.dissolution,
            'dissolutionType': dissolution_type,
            'dissolutionDate': LegislationDatetime.format_as_legislation_date(business.dissolution_date)
        }

    # update batch processing entry, if any is present
    if flag_on:
        batch_processings = BatchProcessing.find_by(filing_id=filing_rec.id)
        for batch_processing in batch_processings:
            if batch_processing.status == BatchProcessing.BatchProcessingStatus.QUEUED:
                batch_processing.status = BatchProcessing.BatchProcessingStatus.COMPLETED
                batch_processing.last_modified = datetime.utcnow()
                batch_processing.save()


def post_process(business: Business, filing: Filing, correction: bool = False):  # pylint: disable=W0613
    """Post processing activities for incorporations.

    THIS SHOULD NOT ALTER THE MODEL
    """
