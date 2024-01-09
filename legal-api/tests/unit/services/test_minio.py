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
"""Tests for the Minio service.

Test suite to ensure that the Minio service routines are working as expected.
"""
import os

import requests
from minio.error import S3Error

from legal_api.services import MinioService

from .test_pdf_service import _create_pdf_file


def test_create_signed_put_url(session, minio_server):  # pylint:disable=unused-argument
    """Assert that the a PUT url can be pre-signed."""
    file_name = "cooperative-test.pdf"
    signed_url = MinioService.create_signed_put_url(file_name)
    assert signed_url
    assert signed_url.get("key").endswith(".pdf")


def test_create_signed_get_url(session, minio_server, tmpdir):  # pylint:disable=unused-argument
    """Assert that a GET url can be pre-signed."""
    key = _upload_file(tmpdir)
    pre_signed_get = MinioService.create_signed_get_url(key)
    assert pre_signed_get
    get_response = requests.get(pre_signed_get)
    assert get_response


def test_get_file_info(session, minio_server, tmpdir):  # pylint:disable=unused-argument
    """Assert that we can retrieve a file info."""
    key = _upload_file(tmpdir)
    file_info = MinioService.get_file_info(key)
    assert file_info


def test_get_file(session, minio_server, tmpdir):  # pylint:disable=unused-argument
    """Assert that we can retrieve a file."""
    key = _upload_file(tmpdir)
    get_response = MinioService.get_file(key)
    assert get_response


def test_delete_file(session, minio_server, tmpdir):  # pylint:disable=unused-argument
    """Assert that a file can be deleted."""
    key = _upload_file(tmpdir)
    MinioService.delete_file(key)

    try:
        MinioService.get_file_info(key)
    except S3Error as ex:
        assert ex.code == "NoSuchKey"


def _upload_file(tmpdir):
    d = tmpdir.mkdir("subdir")
    fh = d.join("cooperative-test.pdf")
    fh.write("Test File")
    filename = os.path.join(fh.dirname, fh.basename)

    test_file = open(filename, "rb")
    files = {"upload_file": test_file}
    file_name = fh.basename
    signed_url = MinioService.create_signed_put_url(file_name)
    key = signed_url.get("key")
    pre_signed_put = signed_url.get("preSignedUrl")
    requests.put(pre_signed_put, files=files)
    return key


def test_put_file(session, minio_server, tmpdir):  # pylint:disable=unused-argument
    """Assert that a file can be replaced."""
    key = _upload_file(tmpdir)

    pdf_file = _create_pdf_file()
    # Replace previous file with this pdf file
    MinioService.put_file(key, pdf_file, pdf_file.getbuffer().nbytes)

    try:
        file = MinioService.get_file(key)
        pdf_file.seek(0)
        assert file.data == pdf_file.read()
    except S3Error as ex:
        assert ex.code == "NoSuchKey"
