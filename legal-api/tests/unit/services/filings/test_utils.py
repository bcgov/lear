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
import random
from datetime import date

from hypothesis import example, given
from hypothesis.strategies import text
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from legal_api.services.utils import get_date, get_str

# In-memory store mapping DRS file key -> PDF bytes, used by _upload_file and drs_document_mock.
_drs_store: dict = {}


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


def _upload_file(page_size, invalid):
    """Create a PDF, store it in _drs_store keyed by a DRS file key, and return the key."""
    pdf_data = _create_pdf_file(page_size, invalid).read()
    drs_id = f'DS{random.randint(1000000000, 9999999999)}'
    file_key = f'COOP-{drs_id}'
    _drs_store[file_key] = pdf_data
    return file_key


def mock_drs_get_document(monkeypatch):
    """Monkeypatch doc_service.get_document to serve PDF bytes from _drs_store.

    Call this at the start of any test that uses _upload_file and then calls validate_pdf.
    Works with pytest monkeypatch fixture.
    """
    from unittest.mock import MagicMock

    import legal_api.services.filings.validations.common_validations as cv

    def _side_effect(drs_id, doc_class, doc_binary=True):
        file_key = f'{doc_class}-{drs_id}'
        pdf_bytes = _drs_store.get(file_key, b'')
        return MagicMock(ok=True, content=pdf_bytes)

    monkeypatch.setattr(cv, 'doc_service',
                        MagicMock(get_document=MagicMock(side_effect=_side_effect)))


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
