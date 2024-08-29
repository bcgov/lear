# Copyright © 2024 Province of British Columbia
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
"""This provides the service for furnishing documents."""
import io
from typing import Final

import PyPDF2
from flask import current_app

from legal_api.models import Furnishing, db
from legal_api.reports.report_v2 import ReportTypes, ReportV2


COVER_REPORT_DATE_FORMAT: Final = '%B %d, %Y %I:%M:%S %p'


class FurnishingDocumentsService():
    """Provides services to get document(s) for furnishing entry."""

    def __init__(self, document_key=None, variant=None):
        """Create FurnishingDocumentsService instance."""
        self._report = ReportV2(business=None, furnishing=None, document_key=document_key, variant=variant)

    def get_furnishing_document(self, furnishing: Furnishing) -> bytes:
        """Return a single furnishing document."""
        self._report.set_report_data(business=furnishing.business, furnishing=furnishing)
        return self._report.get_pdf()

    def get_merged_furnishing_document(self, furnishings: list) -> bytes:
        """Return a merged batch furnishing document with cover."""
        pdfs = self._get_batch_furnishing_documents(furnishings)
        cover = self._get_batch_cover(pdfs)
        files = {
            'cover': cover,
            'contents': pdfs
        }
        return self._merge_documents(files)

    def _get_batch_furnishing_documents(self, furnishings: list) -> list:
        pdfs = []
        for f in furnishings:
            self._report.set_report_data(business=f.business, furnishing=f)
            pdf = self._report.get_pdf()
            if not pdf:
                current_app.logger.error(
                    f'Error generating PDF for furnishing {f.id}, business {f.business.id}, skip.'
                )
                continue
            pdfs.append(pdf)
        return pdfs

    def _get_batch_cover(self, files: list) -> bytes:
        self._report._document_key = ReportTypes.DISSOLUTION_COVER  # pylint: disable=protected-access
        self._report._report_data = {  # pylint: disable=protected-access
            'letterCount': len(files),
            'reportDate': self._report._report_date_time.strftime(  # pylint: disable=protected-access
                COVER_REPORT_DATE_FORMAT
            ),
            'customBatchId': self._get_batch_custom_identifier(),
            'pageCount': len(files) * 2 + 1,
            'environment': current_app.config.get('ENV')
        }
        cover = self._report.get_pdf()
        if not cover:
            current_app.logger.error('Error generating cover PDF.')
        return cover

    @staticmethod
    def _merge_documents(files: dict) -> bytes:
        try:
            merger = PyPDF2.PdfFileMerger()
            if files['cover']:
                merger.append(io.BytesIO(files['cover']))
            contents = files['contents']
            for _, pdf in enumerate(contents):
                merger.append(io.BytesIO(pdf))
            writer_buffer = io.BytesIO()
            merger.write(writer_buffer)
            merger.close()
            return writer_buffer.getvalue()
        except Exception as e:
            current_app.logger.error(f'Error merging PDF:{e}')
            return None

    @staticmethod
    def _get_batch_custom_identifier() -> int:
        return db.session.execute("SELECT nextval('batch_custom_identifier')").scalar()
