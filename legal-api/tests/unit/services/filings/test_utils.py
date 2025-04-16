# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test suite to ensure the Common Utilities are working correctly."""
import io
from datetime import date

import requests
from hypothesis import example, given
from hypothesis.strategies import text
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from legal_api.services import MinioService, DocumentRecordService, flags
from legal_api.services.utils import get_date, get_str


@given(f=text(), p=text())
@example(f={'filing': {'header': {'date': '2001-08-05'}}},
         p='filing/header/date')
def test_get_date(f, p):
    """Assert the get_date extracts the date from the JSON file."""
    d = get_date(f, p)
    if not d:
        assert True
    else:
        assert isinstance(d, date)


@given(f=text(), p=text())
@example(f={'filing': {'header': {'name': 'annualReport'}}},
         p='filing/header/name')
def test_get_str(f, p):
    """Assert the get_date extracts the date from the JSON file."""
    d = get_str(f, p)
    if not d:
        assert True
    else:
        assert isinstance(d, str)


def _upload_file(page_size, invalid, document_class=None, document_type=None):
    print("TYUIUYTYUYTYYUYYTYTYYTYTYYUYTYTYTYTYTYTYTYTYTYTYTYTYTYTYTYTYTYTYTYYYTYTY")
    if flags.is_on('enable-document-records'):
        file_path = "tests/unit/invalid_size.pdf" if invalid else "tests/unit/valid_size.pdf"
        raw_data = None
        with open(file_path, "rb") as data_file:
                raw_data = data_file.read()
                data_file.close()
        response = DocumentRecordService.upload_document(
            document_class, 
            document_type, 
            raw_data
        )
        return response['documentServiceId']
    else:
        signed_url = MinioService.create_signed_put_url('cooperative-test.pdf')
        key = signed_url.get('key')
        pre_signed_put = signed_url.get('preSignedUrl')

        requests.put(pre_signed_put, data=_create_pdf_file(page_size, invalid).read(),
                    headers={'Content-Type': 'application/octet-stream'})
        return key


def _create_pdf_file(page_size, invalid):
    buffer = io.BytesIO()
    can = canvas.Canvas(buffer, pagesize=page_size)
    doc_height = letter[1]

    for _ in range(3):
        # Create invalid page size on last page of pdf
        if(invalid and _ == 2):
            can.setPageSize((500, 500))
        text = 'This is a test document.\nThis is a test document.\nThis is a test document.'
        text_x_margin = 100
        text_y_margin = doc_height - 300
        line_height = 14
        _write_text(can, text, line_height, text_x_margin, text_y_margin)
        can.showPage()

    can.save()
    buffer.seek(0)
    return buffer


def _write_text(can, text, line_height, x_margin, y_margin):
    """Write text lines into a canvas."""
    for line in text.splitlines():
        can.drawString(x_margin, y_margin, line)
        y_margin -= line_height
