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
"""The Unit Tests for the Continuation Out filing."""
import copy
import random

from datetime import datetime, timezone
from business_model.models import Business, Document, Filing

from registry_schemas.example_data import CONTINUATION_OUT, FILING_TEMPLATE
from business_filer.common.legislation_datetime import LegislationDatetime

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import continuation_out
from business_filer.filing_processors.continuation_out import CONTINUATION_OUT_DOCUMENT_TYPE
from tests.unit import create_business, create_filing


def tests_filer_continuation_out(app, session):
    """Assert that the continuation out object is correctly populated to model objects."""
    identifier = f'BC{random.randint(1000000, 9999999)}'
    business = create_business(identifier, legal_type='CP')

    filing_json = copy.deepcopy(FILING_TEMPLATE)
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['header']['name'] = 'continuationOut'
    filing_json['filing']['continuationOut'] = CONTINUATION_OUT

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    continuation_out_filing = create_filing(payment_id, filing_json, business_id=business.id)

    filing_meta = FilingMeta()

    # Test
    continuation_out.process(business, continuation_out_filing, filing_json['filing'], filing_meta)
    business.save()

    # Check outcome
    final_filing = Filing.find_by_id(continuation_out_filing.id)
    foreign_jurisdiction_json = filing_json['filing']['continuationOut']['foreignJurisdiction']
    continuation_out_date_str = filing_json['filing']['continuationOut']['continuationOutDate']
    continuation_out_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(continuation_out_date_str)

    assert filing_json['filing']['continuationOut']['courtOrder']['fileNumber'] == final_filing.court_order_file_number
    assert filing_json['filing']['continuationOut']['courtOrder']['effectOfOrder'] == final_filing.court_order_effect_of_order

    assert business.state == Business.State.HISTORICAL
    assert business.state_filing_id == final_filing.id
    assert business.jurisdiction == foreign_jurisdiction_json['country'].upper()
    assert business.foreign_jurisdiction_region == foreign_jurisdiction_json['region'].upper()
    assert business.foreign_legal_name == filing_json['filing']['continuationOut']['legalName']
    assert business.continuation_out_date == continuation_out_date

    assert filing_meta.continuation_out['country'] == foreign_jurisdiction_json['country']
    assert filing_meta.continuation_out['region'] == foreign_jurisdiction_json['region']
    assert filing_meta.continuation_out['continuationOutDate'] == continuation_out_date_str
    assert filing_meta.continuation_out['legalName'] == filing_json['filing']['continuationOut']['legalName']


def tests_filer_continuation_out_uploaded_documents(app, session):
    """Assert that uploaded supporting documents are persisted as Document records and filing meta data."""
    identifier = f'BC{random.SystemRandom().randint(1000000, 9999999)}'
    business = create_business(identifier, legal_type='CP')

    uploaded_documents = [
        {'fileKey': 'aaaaaaaa-1111-2222-3333-444444444444', 'fileName': 'supporting-document-1.pdf'},
        {'fileKey': 'bbbbbbbb-5555-6666-7777-888888888888', 'fileName': 'supporting-document-2.pdf'}
    ]

    filing_json = copy.deepcopy(FILING_TEMPLATE)
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['header']['name'] = 'continuationOut'
    filing_json['filing']['continuationOut'] = copy.deepcopy(CONTINUATION_OUT)
    filing_json['filing']['continuationOut']['documents'] = uploaded_documents

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    continuation_out_filing = create_filing(payment_id, filing_json, business_id=business.id)

    filing_meta = FilingMeta()

    # Test
    continuation_out.process(business, continuation_out_filing, filing_json['filing'], filing_meta)
    business.save()

    # Check outcome
    final_filing = Filing.find_by_id(continuation_out_filing.id)

    documents = Document.find_all_by(final_filing.id, CONTINUATION_OUT_DOCUMENT_TYPE)
    assert len(documents) == len(uploaded_documents)
    for document in documents:
        file = next(x for x in uploaded_documents if x.get('fileKey') == document.file_key)
        assert document.file_name == file.get('fileName')
        assert document.filing_id == final_filing.id

    meta_documents = filing_meta.continuation_out['uploadedDocuments']
    assert len(meta_documents) == len(uploaded_documents)
    for file in uploaded_documents:
        assert file in meta_documents


def tests_filer_continuation_out_no_uploaded_documents(app, session):
    """Assert that no uploadedDocuments meta data is set when no documents are uploaded."""
    identifier = f'BC{random.SystemRandom().randint(1000000, 9999999)}'
    business = create_business(identifier, legal_type='CP')

    filing_json = copy.deepcopy(FILING_TEMPLATE)
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['header']['name'] = 'continuationOut'
    filing_json['filing']['continuationOut'] = copy.deepcopy(CONTINUATION_OUT)
    filing_json['filing']['continuationOut'].pop('documents', None)

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    continuation_out_filing = create_filing(payment_id, filing_json, business_id=business.id)

    filing_meta = FilingMeta()

    # Test
    continuation_out.process(business, continuation_out_filing, filing_json['filing'], filing_meta)
    business.save()

    # Check outcome
    final_filing = Filing.find_by_id(continuation_out_filing.id)
    assert Document.find_all_by(final_filing.id, CONTINUATION_OUT_DOCUMENT_TYPE) == []
    assert 'uploadedDocuments' not in filing_meta.continuation_out
