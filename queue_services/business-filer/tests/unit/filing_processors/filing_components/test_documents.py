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
"""The Unit Tests for the documents filing component."""
import copy
import random

import pytest
from business_model.models import DocumentType
from registry_schemas.example_data import ALTERATION_FILING_TEMPLATE

from business_filer.filing_processors.filing_components import documents
from tests.unit import create_business, create_filing


@pytest.mark.parametrize('test_name,files', [
    ('no files', []),
    ('one file', [
        {'fileKey': 'aaaaaaaa-1111-2222-3333-444444444444', 'fileName': 'document-1.pdf', 'documentType': DocumentType.COURT_ORDER.value}
    ]),
    ('multiple files', [
        {'fileKey': 'aaaaaaaa-1111-2222-3333-444444444444', 'fileName': 'document-1.pdf', 'documentType': DocumentType.COURT_ORDER.value},
        {'fileKey': 'bbbbbbbb-5555-6666-7777-888888888888', 'fileName': 'document-2.pdf', 'documentType': DocumentType.COURT_ORDER.value}
    ])
])
def test_create_filing_documents(app, session, test_name, files):
    """Assert that a document record is created per file and the meta list mirrors the files."""
    identifier = f'BC{random.randint(1000000, 9999999)}'
    business = create_business(identifier, legal_type='BC')
    json_filing = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    filing = create_filing(token='123', json_filing=json_filing, business_id=business.id)

    file_list = documents.create_filing_documents(
        files, business, filing)

    business_documents = business.documents.all()
    assert len(business_documents) == len(files)
    assert file_list == [
        {'fileKey': file['fileKey'], 'fileName': file['fileName'], 'documentType': file['documentType']} for file in files
    ]
    for file in files:
        document = next(x for x in business_documents if x.file_key == file['fileKey'])
        assert document.type == file['documentType']
        assert document.file_name == file['fileName']
        assert document.filing_id == filing.id
