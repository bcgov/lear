# Copyright © 2023 Province of British Columbia
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
"""Supply version and commit hash info.

When deployed in OKD, it adds the last commit hash onto the version info.
"""
import io
import os
from importlib.metadata import version

# import PyPDF2

# from legal_api.reports.registrar_meta import RegistrarInfo
# from legal_api.services import PdfService
# from legal_api.services.minio import MinioService
# from legal_api.services.pdf_service import RegistrarStampData
# from legal_api.utils.legislation_datetime import LegislationDatetime



def _get_commit_hash():
    """Return the containers ref if present."""
    if (commit_hash := os.getenv("VCS_REF", None)) and commit_hash != "missing":
        return commit_hash
    return None


def get_run_version():
    """Return a formatted version string for this service."""
    ver = version(__name__[: __name__.find(".")])
    if commit_hash := _get_commit_hash():
        return f"{ver}-{commit_hash}"
    return ver


def replace_file_with_certified_copy(
    _bytes: bytes,
    key: str,
    #        data: RegistrarStampData
):
    """Create a certified copy and replace it into Minio server."""

    raise Exception
    # TODO we shouldn't do this anymore

    # open_pdf_file = io.BytesIO(_bytes)
    # pdf_reader = PyPDF2.PdfFileReader(open_pdf_file)
    # pdf_writer = PyPDF2.PdfFileWriter()
    # pdf_writer.appendPagesFromReader(pdf_reader)
    # output_original_pdf = io.BytesIO()
    # pdf_writer.write(output_original_pdf)
    # output_original_pdf.seek(0)
    # pdf_service = PdfService()
    # registrars_stamp = pdf_service.create_registrars_stamp(data)
    # certified_copy = pdf_service.stamp_pdf(output_original_pdf, registrars_stamp, only_first_page=True)

    # MinioService.put_file(key, certified_copy, certified_copy.getbuffer().nbytes)
