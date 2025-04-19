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
"""Util functions for testing."""
import io
from datetime import datetime

import requests
# import PyPDF2
# from legal_api.services.minio import MinioService
# from legal_api.services.pdf_service import _write_text
# from reportlab.lib.pagesizes import letter
# from reportlab.pdfgen import canvas

# def upload_file(file_name: str):
#     """Upload a sample file for testing."""
#     signed_url = MinioService.create_signed_put_url(file_name)
#     key = signed_url.get('key')
#     pre_signed_put = signed_url.get('preSignedUrl')
#     requests.put(pre_signed_put, data=_create_pdf_file().read(), headers={'Content-Type': 'application/octet-stream'})
#     return key


# def _create_pdf_file():
#     """Create a sample pdf file for testing."""
#     buffer = io.BytesIO()
#     can = canvas.Canvas(buffer, pagesize=letter)
#     doc_height = letter[1]

#     for _ in range(3):
#         text = 'This is a test document.\nThis is a test document.\nThis is a test document.'
#         text_x_margin = 100
#         text_y_margin = doc_height - 300
#         line_height = 14
#         _write_text(can, text, line_height, text_x_margin, text_y_margin)
#         can.showPage()

#     can.save()
#     buffer.seek(0)
#     return buffer


# def assert_pdf_contains_text(search_text, pdf_raw_bytes: bytes):
#     """Assert a text is contained in a pdf file."""
#     pdf_obj = PyPDF2.PdfFileReader(io.BytesIO(pdf_raw_bytes))
#     pdf_page = pdf_obj.getPage(0)
#     text = pdf_page.extractText()
#     assert search_text in text

def has_expected_date_str_format(date_str: str, format: str) -> bool:
    "Determine if date string confirms to expected format"
    try:
        datetime.strptime(date_str, format)
    except ValueError:
        return False
    return True
