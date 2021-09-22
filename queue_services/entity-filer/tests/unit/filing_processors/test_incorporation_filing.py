# Copyright © 2020 Province of British Columbia
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
"""The Unit Tests for the Incorporation filing."""

import copy
import io
import os
from datetime import datetime
from unittest.mock import patch

import pytest
import requests
from _pytest.compat import assert_never
from legal_api.constants import COOPERATIVE_FOLDER_NAME
from legal_api.models import Filing
from legal_api.models.colin_event_id import ColinEventId
from legal_api.models.document import DocumentType
from legal_api.services import PdfService
from legal_api.services.minio import MinioService
from legal_api.services.pdf_service import _write_text
from minio.error import S3Error
from registry_schemas.example_data import (
    COOP_INCORPORATION_FILING_TEMPLATE,
    CORRECTION_INCORPORATION,
    INCORPORATION_FILING_TEMPLATE,
)
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from entity_filer.filing_processors import incorporation_filing
from tests.unit import create_filing


@pytest.mark.parametrize('legal_type,filing', [
    ('BC', copy.deepcopy(INCORPORATION_FILING_TEMPLATE)),
    ('CP', copy.deepcopy(COOP_INCORPORATION_FILING_TEMPLATE)),
])
def test_incorporation_filing_process_with_nr(app, session, minio_server, legal_type, filing):
    """Assert that the incorporation object is correctly populated to model objects."""
    # setup
    next_corp_num = 'BC0001095'
    with patch.object(incorporation_filing, 'get_next_corp_num', return_value=next_corp_num) as mock_get_next_corp_num:
        identifier = 'NR 1234567'
        filing['filing']['incorporationApplication']['nameRequest']['nrNumber'] = identifier
        filing['filing']['incorporationApplication']['nameRequest']['legalName'] = 'Test'
        if legal_type == 'CP':
            rules_file_key_uploaded_by_user = _upload_file()
            memorandum_file_key_uploaded_by_user = _upload_file()
            filing['filing']['incorporationApplication']['cooperative']['rulesFileKey'] = rules_file_key_uploaded_by_user
            filing['filing']['incorporationApplication']['cooperative']['rulesFileName'] = 'Rules_File.pdf'
            filing['filing']['incorporationApplication']['cooperative']['memorandumFileKey'] = \
                memorandum_file_key_uploaded_by_user
            filing['filing']['incorporationApplication']['cooperative']['memorandumFileName'] = 'Memorandum_File.pdf'
        create_filing('123', filing)

        effective_date = datetime.utcnow()
        filing_rec = Filing(effective_date=effective_date, filing_json=filing)

        # test
        business, filing_rec = incorporation_filing.process(None, filing, filing_rec)

        # Assertions
        assert business.identifier == next_corp_num
        assert business.founding_date == effective_date
        assert business.legal_type == filing['filing']['incorporationApplication']['nameRequest']['legalType']
        assert business.legal_name == filing['filing']['incorporationApplication']['nameRequest']['legalName']
        if legal_type == 'BC':
            assert len(business.share_classes.all()) == 2
            assert len(business.offices.all()) == 2  # One office is created in create_business method.
        elif legal_type == 'CP':
            assert len(business.offices.all()) == 1
            documents = business.documents.all()
            assert len(documents) == 2
            for document in documents:
                if document.type == DocumentType.COOP_RULES.value:
                    original_rules_key = filing['filing']['incorporationApplication']['cooperative']['rulesFileKey']
                    assert document.file_key != original_rules_key
                    assert MinioService.get_file(document.file_key)
                elif document.type == DocumentType.COOP_MEMORANDUM.value:
                    original_memorandum_key = filing['filing']['incorporationApplication']['cooperative']['memorandumFileKey']
                    assert document.file_key != original_memorandum_key
                    assert MinioService.get_file(document.file_key)

            # Assert those exist before deletion:
            assert MinioService.get_file(rules_file_key_uploaded_by_user)
            assert MinioService.get_file(memorandum_file_key_uploaded_by_user)

            incorporation_filing.post_process(business, filing_rec)
            try:
                MinioService.get_file(rules_file_key_uploaded_by_user)
                raise AssertionError ("Original Rules file should not exist after post_process.")
            except S3Error:
                pass
            try:
                MinioService.get_file(memorandum_file_key_uploaded_by_user)
                raise AssertionError ("Original Memorandum file should not exist after post_process.")
            except S3Error:
                pass
    mock_get_next_corp_num.assert_called_with(filing['filing']['incorporationApplication']['nameRequest']['legalType'])


def _upload_file():
    signed_url = MinioService.create_signed_put_url('cooperative-test.pdf', prefix_key=COOPERATIVE_FOLDER_NAME)
    key = signed_url.get('key')
    pre_signed_put = signed_url.get('preSignedUrl')

    requests.put(pre_signed_put, data=_create_pdf_file().read(), headers={'Content-Type': 'application/octet-stream'})
    return key


def _create_pdf_file():
    buffer = io.BytesIO()
    can = canvas.Canvas(buffer, pagesize=letter)
    doc_height = letter[1]

    for _ in range(3):
        text = 'This is a test document.\nThis is a test document.\nThis is a test document.'
        text_x_margin = 100
        text_y_margin = doc_height - 300
        line_height = 14
        _write_text(can, text, line_height,text_x_margin, text_y_margin)
        can.showPage()

    can.save()
    buffer.seek(0)
    return buffer


def test_incorporation_filing_process_no_nr(app, session):
    """Assert that the incorporation object is correctly populated to model objects."""
    # setup
    next_corp_num = 'BC0001095'
    with patch.object(incorporation_filing, 'get_next_corp_num', return_value=next_corp_num) as mock_get_next_corp_num:
        filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
        create_filing('123', filing)

        effective_date = datetime.utcnow()
        filing_rec = Filing(effective_date=effective_date, filing_json=filing)

        # test
        business, filing_rec = incorporation_filing.process(None, filing, filing_rec)

        # Assertions
        assert business.identifier == next_corp_num
        assert business.founding_date == effective_date
        assert business.legal_type == filing['filing']['incorporationApplication']['nameRequest']['legalType']
        assert business.legal_name == business.identifier[2:] + ' B.C. LTD.'
        assert len(business.share_classes.all()) == 2
        assert len(business.offices.all()) == 2  # One office is created in create_business method.

    mock_get_next_corp_num.assert_called_with(filing['filing']['incorporationApplication']['nameRequest']['legalType'])


def test_incorporation_filing_process_correction(app, session):
    """Assert that the incorporation correction is correctly populated to model objects."""
    # setup
    next_corp_num = 'BC0001095'
    with patch.object(incorporation_filing, 'get_next_corp_num', return_value=next_corp_num) as mock_get_next_corp_num:
        filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
        create_filing('123', filing)

        effective_date = datetime.utcnow()
        filing_rec = Filing(effective_date=effective_date, filing_json=filing)

        # test
        business, filing_rec = incorporation_filing.process(None, filing, filing_rec)

        # Assertions
        assert business.identifier == next_corp_num
        assert business.founding_date == effective_date
        assert business.legal_type == filing['filing']['incorporationApplication']['nameRequest']['legalType']
        assert business.legal_name == business.identifier[2:] + ' B.C. LTD.'
        assert len(business.share_classes.all()) == 2
        assert len(business.offices.all()) == 2  # One office is created in create_business method.

    mock_get_next_corp_num.assert_called_with(filing['filing']['incorporationApplication']['nameRequest']['legalType'])

    correction_filing = copy.deepcopy(CORRECTION_INCORPORATION)
    correction_filing['filing']['incorporationApplication']['nameTranslations'] = [{'name': 'A5 Ltd.'}]
    del correction_filing['filing']['incorporationApplication']['shareStructure']['shareClasses'][1]
    corrected_filing_rec = Filing(effective_date=effective_date, filing_json=correction_filing)
    corrected_business, corrected_filing_rec =\
        incorporation_filing.process(business, correction_filing, corrected_filing_rec)
    assert corrected_business.identifier == next_corp_num
    assert corrected_business.legal_name == \
        correction_filing['filing']['incorporationApplication']['nameRequest']['legalName']
    assert len(corrected_business.share_classes.all()) == 1


@pytest.mark.parametrize('test_name,response,expected', [
    ('short number', '1234', 'BC0001234'),
    ('full 9 number', '1234567', 'BC1234567'),
    ('too big number', '12345678', None),
])
def test_get_next_corp_num(requests_mock, app, test_name, response, expected):
    """Assert that the corpnum is the correct format."""
    from flask import current_app

    from entity_filer.filing_processors.incorporation_filing import get_next_corp_num

    with app.app_context():
        requests_mock.post(f'{current_app.config["COLIN_API"]}/BC', json={'corpNum': response})

        corp_num = get_next_corp_num('BEN')

    assert corp_num == expected


def test_incorporation_filing_coop_from_colin(app, session):
    """Assert that an existing coop incorporation is loaded corrrectly."""
    # setup
    corp_num = 'CP0000001'
    colind_id = 1
    filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)

    # Change the template to be a CP == Cooperative
    filing['filing']['business']['legalType'] = 'CP'
    filing['filing']['business']['identifier'] = corp_num
    filing['filing']['incorporationApplication']['nameRequest']['legalType'] = 'CP'
    filing['filing']['incorporationApplication'].pop('shareStructure')
    effective_date = datetime.utcnow()
    # Create the Filing obeject in the DB
    filing_rec = Filing(effective_date=effective_date,
                        filing_json=filing)
    colin_event = ColinEventId()
    colin_event.colin_event_id = colind_id
    filing_rec.colin_event_ids.append(colin_event)
    # Override the state setting mechanism
    filing_rec.skip_status_listener = True
    filing_rec._status = 'PENDING'
    filing_rec.save()

    # test
    business, filing_rec = incorporation_filing.process(None, filing, filing_rec)

    # Assertions
    assert business.identifier == corp_num
    assert business.founding_date.replace(tzinfo=None) == effective_date
    assert business.legal_type == filing['filing']['incorporationApplication']['nameRequest']['legalType']
    assert business.legal_name == business.identifier[2:] + ' B.C. LTD.'
    assert len(business.offices.all()) == 2  # One office is created in create_business method.


@pytest.mark.parametrize('legal_type', [
    ('BC'),
    ('ULC'),
    ('CC'),
])
def test_incorporation_filing_bc_company_from_colin(app, session, legal_type):
    """Assert that an existing bc company(LTD, ULC, CCC) incorporation is loaded corrrectly."""
    # setup
    corp_num = 'BC0000001'
    colind_id = 1
    filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)

    # Change the template to be LTD, ULC or CCC
    filing['filing']['business']['legalType'] = legal_type
    filing['filing']['business']['identifier'] = corp_num
    filing['filing']['incorporationApplication']['nameRequest']['legalType'] = legal_type
    effective_date = datetime.utcnow()
    # Create the Filing object in the DB
    filing_rec = Filing(effective_date=effective_date,
                        filing_json=filing)
    colin_event = ColinEventId()
    colin_event.colin_event_id = colind_id
    filing_rec.colin_event_ids.append(colin_event)
    # Override the state setting mechanism
    filing_rec.skip_status_listener = True
    filing_rec._status = 'PENDING'
    filing_rec.save()

    # test
    business, filing_rec = incorporation_filing.process(None, filing, filing_rec)

    # Assertions
    assert business.identifier == corp_num
    assert business.founding_date.replace(tzinfo=None) == effective_date
    assert business.legal_type == filing['filing']['incorporationApplication']['nameRequest']['legalType']
    assert business.legal_name == business.identifier[2:] + ' B.C. LTD.'
    assert len(business.offices.all()) == 2  # One office is created in create_business method.
    assert len(business.share_classes.all()) == 2
    assert len(business.party_roles.all()) == 3
