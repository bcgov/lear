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
"""Tests for the PDF service.

"""
import io

from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from legal_api.reports.registrar_meta import RegistrarInfo
from legal_api.services import PdfService
from legal_api.services.pdf_service import RegistrarStampData, _write_text
from legal_api.utils.legislation_datetime import LegislationDatetime


def test_stamp(app):  # pylint:disable=unused-argument
    """Assert that stamp service is working."""
    with app.app_context():
        pdf_input = _create_pdf_file()
        incorp_date = LegislationDatetime.now()
        pdf_service = PdfService()
        registrar_stamp_data = RegistrarStampData(incorp_date, 'CP00000001', file_name='rules.pdf')
        registrars_stamp = pdf_service.create_registrars_stamp(registrar_stamp_data)
        
        certified_copy = pdf_service.stamp_pdf(pdf_input, registrars_stamp, only_first_page=True)
        certified_copy_obj = PdfReader(certified_copy)
        
        certified_copy_page = certified_copy_obj.getPage(0)
        text = certified_copy_page.extractText()
        assert 'Filed on' in text
        assert 'File Name: rules.pdf' in text
        
        certified_copy_page = certified_copy_obj.getPage(1)
        text = certified_copy_page.extractText()
        assert 'Filed on' not in text

        # Uncomment to generate the file:
        # f = open("certified_copy.pdf", "wb")
        # f.write(certified_copy.getbuffer())
        # f.close()


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
