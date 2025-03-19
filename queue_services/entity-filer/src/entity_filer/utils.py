# Copyright © 2023 Province of British Columbia
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
"""Supply version and commit hash info.

When deployed in OKD, it adds the last commit hash onto the version info.
"""
import io
import os

import PyPDF2
from legal_api.services import PdfService, Flags
from legal_api.services.minio import MinioService
from legal_api.services.document_record import DocumentRecordService
from legal_api.services.pdf_service import RegistrarStampData

from entity_filer.version import __version__

flags = Flags()  # pylint: disable=invalid-name

def _get_build_openshift_commit_hash():
    return os.getenv('OPENSHIFT_BUILD_COMMIT', None)


def get_run_version():
    """Return a formatted version string for this service."""
    commit_hash = _get_build_openshift_commit_hash()
    if commit_hash:
        return f'{__version__}-{commit_hash}'
    return __version__


def replace_file_with_certified_copy(_bytes: bytes, key: str, data: RegistrarStampData, file_name: str):
    """Create a certified copy and replace it into Minio server."""
    open_pdf_file = io.BytesIO(_bytes)
    pdf_reader = PyPDF2.PdfFileReader(open_pdf_file)
    pdf_writer = PyPDF2.PdfFileWriter()
    pdf_writer.appendPagesFromReader(pdf_reader)
    output_original_pdf = io.BytesIO()
    pdf_writer.write(output_original_pdf)
    output_original_pdf.seek(0)
    pdf_service = PdfService()
    registrars_stamp = pdf_service.create_registrars_stamp(data)
    certified_copy = pdf_service.stamp_pdf(output_original_pdf, registrars_stamp, only_first_page=True)
    if(flags.is_on('enable-document-records')):
        DocumentRecordService.update_document(certified_copy, key, file_name)
    else:
        MinioService.put_file(key, certified_copy, certified_copy.getbuffer().nbytes)
