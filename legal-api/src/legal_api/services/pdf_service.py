# Copyright © 2023 Province of British Columbia
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
"""This module is a wrapper for Pdf Services."""

import io
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import PyPDF2
from flask import current_app
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from legal_api.reports.registrar_meta import RegistrarInfo
from legal_api.utils.legislation_datetime import LegislationDatetime


@dataclass
class RegistrarStampData:
    """Data class for Registrar's stamp."""

    certify_date: datetime
    identifier: str
    file_name: Optional[str] = None
    is_correction: bool = False


class PdfService:
    """Pdf Services."""

    def __init__(self):
        """Create a PDF Service Instance."""
        fonts_path = current_app.config.get("FONTS_PATH")
        bcsans_path = f"{fonts_path}/BCSans-Regular.ttf"
        pdfmetrics.registerFont(TTFont("BCSans", bcsans_path))

    @staticmethod
    def stamp_pdf(input_pdf, watermark, only_first_page=True):
        """Merge two PDFs."""
        watermark_obj = PyPDF2.PdfFileReader(watermark)
        watermark_page = watermark_obj.getPage(0)

        pdf_reader = PyPDF2.PdfFileReader(input_pdf)
        pdf_writer = PyPDF2.PdfFileWriter()

        for page_num in range(pdf_reader.getNumPages()):
            page = pdf_reader.getPage(page_num)

            if (only_first_page and page_num == 0) or not only_first_page:
                page.mergePage(watermark_page)

            pdf_writer.addPage(page)

        output = io.BytesIO()
        pdf_writer.write(output)
        output.seek(0)
        return output

    @classmethod
    def create_registrars_stamp(cls, data: RegistrarStampData):
        """Create a Registrar's stamp to certify documents."""
        registrar_info = RegistrarInfo.get_registrar_info(data.certify_date)
        buffer = io.BytesIO()
        can = canvas.Canvas(buffer, pagesize=letter)
        doc_width = letter[0]
        doc_height = letter[1]

        image_x_margin = doc_width - 130
        image_y_margin = doc_height - 150
        can.drawImage(
            registrar_info["signatureAndText"],
            image_x_margin,
            image_y_margin,
            width=100,
            preserveAspectRatio=True,
            mask="auto",
        )

        certify_date = LegislationDatetime.as_legislation_timezone(data.certify_date)
        text = "Filed on " + LegislationDatetime.format_as_report_string(certify_date)
        if data.is_correction:
            text += " (Corrected)"
        if data.file_name:
            text += "\nFile Name: " + data.file_name
        text += "\nIncorporation Number: " + data.identifier

        text_x_margin = 32
        text_y_margin = doc_height - 42
        line_height = 14
        can.setFont("BCSans", 10)
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
