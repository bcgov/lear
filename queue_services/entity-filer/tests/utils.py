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
"""Util functions for testing."""
import io
from datetime import datetime

import requests
import PyPDF2
from legal_api.services.minio import MinioService
from legal_api.services.pdf_service import _write_text
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def upload_file(file_name: str):
    """Upload a sample file for testing."""
    signed_url = MinioService.create_signed_put_url(file_name)
    key = signed_url.get('key')
    pre_signed_put = signed_url.get('preSignedUrl')
    requests.put(pre_signed_put, data=_create_pdf_file().read(), headers={'Content-Type': 'application/octet-stream'})
    return key


def _create_pdf_file():
    """Create a sample pdf file for testing."""
    buffer = io.BytesIO()
    can = canvas.Canvas(buffer, pagesize=letter)
    doc_height = letter[1]

    for _ in range(3):
        text = 'This is a test document.\nThis is a test document.\nThis is a test document.'
        text_x_margin = 100
        text_y_margin = doc_height - 300
        line_height = 14
        _write_text(can, text, line_height, text_x_margin, text_y_margin)
        can.showPage()

    can.save()
    buffer.seek(0)
    return buffer


def assert_pdf_contains_text(search_text, pdf_raw_bytes: bytes):
    """Assert a text is contained in a pdf file."""
    pdf_obj = PyPDF2.PdfFileReader(io.BytesIO(pdf_raw_bytes))
    pdf_page = pdf_obj.getPage(0)
    text = pdf_page.extractText()
    assert search_text in text

def has_expected_date_str_format(date_str: str, format: str) -> bool:
    "Determine if date string confirms to expected format"
    try:
        datetime.strptime(date_str, format)
    except ValueError:
        return False
    return True
