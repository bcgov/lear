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
"""The Unit Tests for the Court Order filing."""
import uuid
import copy
import random

from business_model.models import DocumentType, Filing
from registry_schemas.example_data import COURT_ORDER_FILING_TEMPLATE

from business_filer.services.filer import process_filing
from tests.unit import create_business, create_filing
from business_filer.common.filing_message import FilingMessage


def tests_filer_court_order(app, session):
    """Assert that the court order object is correctly populated to model objects."""
    identifier = f'BC{random.randint(1000000, 9999999)}'
    business = create_business(identifier, legal_type='BC')

    filing = copy.deepcopy(COURT_ORDER_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing, business_id=business.id)).id

    filing_msg = FilingMessage(filing_identifier=filing_id)

    # Test
    process_filing(filing_msg)

    # Check outcome
    final_filing = Filing.find_by_id(filing_id)
    court_order = final_filing.court_orders[0]
    assert filing['filing']['courtOrder']['fileNumber'] == court_order.file_number
    assert filing['filing']['courtOrder']['effectOfOrder'] == court_order.effect_of_order
    assert filing['filing']['courtOrder']['orderDetails'] == court_order.order_details
    assert final_filing.meta_data.get('courtOrder')['fileNumber'] == court_order.file_number
    assert final_filing.meta_data.get('courtOrder')['effectOfOrder'] == court_order.effect_of_order
    assert final_filing.meta_data.get('courtOrder')['orderDetails'] == court_order.order_details
    assert final_filing.meta_data.get('courtOrder')['files'][0]['fileKey'] == filing['filing']['courtOrder']['fileKey']
    assert final_filing.meta_data.get('courtOrder')['files'][0]['fileName'] == f'Court Order {court_order.file_number}.pdf'
    assert final_filing.meta_data.get('courtOrder')['files'][0]['documentType'] == DocumentType.COURT_ORDER.value

    court_order_file = final_filing.documents.one_or_none()
    assert court_order_file
    assert court_order_file.type == DocumentType.COURT_ORDER.value
    assert court_order_file.file_key == filing['filing']['courtOrder']['fileKey']


def tests_filer_court_order_multiple_files(app, session):
    """Assert that the court order object with multiple files is correctly populated to model objects."""
    identifier = f'BC{random.randint(1000000, 9999999)}'
    business = create_business(identifier, legal_type='BC')

    filing = copy.deepcopy(COURT_ORDER_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier
    file_key_1 = f"{uuid.uuid4()}.pdf"
    file_key_2 = f"{uuid.uuid4()}.pdf"
    file_name_1 = f'Court Order {filing['filing']['courtOrder']['fileNumber']}_01.pdf'
    file_name_2 = f'Court Order {filing['filing']['courtOrder']['fileNumber']}_02.pdf'
    filing['filing']['courtOrder']['files'] = [
        {
            "fileKey": file_key_1,
            "fileName": file_name_1,
            "documentType": DocumentType.COURT_ORDER.value
        },
        {
            "fileKey": file_key_2,
            "fileName": file_name_2,
            "documentType": DocumentType.SUPPORTING_DOCUMENT.value
        }
    ]
    del filing['filing']['courtOrder']['fileKey']
    

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing, business_id=business.id)).id

    filing_msg = FilingMessage(filing_identifier=filing_id)

    # Test
    process_filing(filing_msg)

    # Check outcome
    final_filing = Filing.find_by_id(filing_id)
    court_order = final_filing.court_orders[0]
    assert filing['filing']['courtOrder']['fileNumber'] == court_order.file_number
    assert filing['filing']['courtOrder']['effectOfOrder'] == court_order.effect_of_order
    assert filing['filing']['courtOrder']['orderDetails'] == court_order.order_details
    assert final_filing.meta_data.get('courtOrder')['fileNumber'] == court_order.file_number
    assert final_filing.meta_data.get('courtOrder')['effectOfOrder'] == court_order.effect_of_order

    court_order_files = final_filing.documents.all()
    assert len(court_order_files) == 2
    for court_order_file in court_order_files:
        assert court_order_file.type in [DocumentType.COURT_ORDER.value, DocumentType.SUPPORTING_DOCUMENT.value]
        assert court_order_file.file_key in [file_key_1, file_key_2]
        assert court_order_file.file_name in [file_name_1, file_name_2]

    assert len(final_filing.meta_data.get('courtOrder')['files']) == 2
    for court_order_file in final_filing.meta_data.get('courtOrder')['files']:
        assert court_order_file['fileKey'] in [file_key_1, file_key_2]
        assert court_order_file['fileName'] in [file_name_1, file_name_2]
        assert court_order_file['documentType'] in [DocumentType.COURT_ORDER.value, DocumentType.SUPPORTING_DOCUMENT.value]
