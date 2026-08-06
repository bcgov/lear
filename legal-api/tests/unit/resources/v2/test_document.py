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

"""Tests to assure the documents API end-point.

Test-Suite to ensure that the /documents endpoint is working as expected.
"""

from http import HTTPStatus

import pytest
from flask import current_app

from legal_api.resources.v2 import document
from legal_api.services.authz import STAFF_ROLE

from tests.unit.services.utils import create_header


MOCK_DRS_URL = "https://test.api.connect.gov.bc.ca/mockTarget/doc/api/v1"
TEST_DATAFILE = 'tests/unit/services/test_doc.pdf'
PATCH_VALID_PAYLOAD = {
    "businessIdentifier": "BC9901019",
    "filingId": "1199642",  
    "filingDate": "2024-08-02T19:00:00+00:00"
}
# testdata pattern is ({filekey}, {drs_id})
TEST_DRS_ID_DATA = [
    ("", ""),
    ("DS0100001003", "DS0100001003"),
    ("CORP-DS0100001003", "DS0100001003"),
    ("COOP-DS0100001003", "DS0100001003"),
    ("FIRM-DS0100001003", "DS0100001003"),
]
# testdata pattern is ({filekey}, {doc_class})
TEST_DRS_CLASS_DATA = [
    ("", "CORP"),
    ("DS0100001003", "CORP"),
    ("CORP-DS0100001003", "CORP"),
    ("COOP-DS0100001003", "COOP"),
    ("FIRM-DS0100001003", "FIRM"),
]
# testdata pattern is ({filing_type}, {entity_type}, {doc_type}, {drs_class}, {drs_type})
TEST_CREATE_INFO_DATA = [
    ("JUNK", "JUNK", "JUNK", "CORP", "COSD"),
    ("specialResolution", "CP", "coop_memorandum", "COOP", "COOP_MEMORANDUM"),
    ("specialResolution", "CP", "coop_rules", "COOP", "COOP_RULES"),
    ("incorporationApplication", "CP", "coop_memorandum", "COOP", "COOP_MEMORANDUM"),
    ("incorporationApplication", "CP", "coop_rules", "COOP", "COOP_RULES"),
    ("correction", "CP", "coop_memorandum", "COOP", "COOP_MEMORANDUM"),
    ("correction", "CP", "coop_rules", "COOP", "COOP_RULES"),
    ("dissolution", "CP", "affidavit", "COOP", "COSD"),
    ("courtOrder", "BC", "court_order", "CORP", "CRTO"),
    ("courtOrder", "BEN", "court_order", "CORP", "CRTO"),
    ("courtOrder", "C", "court_order", "CORP", "CRTO"),
    ("courtOrder", "CC", "court_order", "CORP", "CRTO"),
    ("courtOrder", "CUL", "court_order", "CORP", "CRTO"),
    ("courtOrder", "ULC", "court_order", "CORP", "CRTO"),
    ("courtOrder", "CP", "court_order", "COOP", "CRTO"),
    ("courtOrder", "SP", "court_order", "FIRM", "CRTO"),
    ("courtOrder", "GP", "court_order", "FIRM", "CRTO"),
    ("continuationOut", "BC", "continuation_out", "CORP", "CNTO"),
    ("continuationOut", "BEN", "continuation_out", "CORP", "CNTO"),
    ("continuationOut", "C", "continuation_out", "CORP", "CNTO"),
    ("continuationIn", "C", "authorization_file", "CORP", "CNTA"),
    ("continuationIn", "C", "director_affidavit", "CORP", "DIRECTOR_AFFIDAVIT"),
    ("continuationIn", "CBEN", "authorization_file", "CORP", "CNTA"),
    ("continuationIn", "CBEN", "director_affidavit", "CORP", "DIRECTOR_AFFIDAVIT"),
    ("continuationIn", "CCC", "authorization_file", "CORP", "CNTA"),
    ("continuationIn", "CCC", "director_affidavit", "CORP", "DIRECTOR_AFFIDAVIT"),
    ("continuationIn", "CUL", "authorization_file", "CORP", "CNTA"),
    ("continuationIn", "CUL", "director_affidavit", "CORP", "DIRECTOR_AFFIDAVIT"),
]
# testdata pattern is ({filename}, {identifier}, {filedate}, {filing_id})
TEST_CREATE_INFO_DATA_EXTRA = [
    (None, None, None, None),
    ("filename.pdf", "BC1500000", "2024-08-01T23:03:45+00:00", 2000000),
]
# testdata pattern is ({description}, {file_key}, {accept})
TEST_CLIENT_GET_DATA = [
    ("Valid file key binary", "CORP-DS0100001000", None),
    ("Valid file key JSON", "CORP-DS0100001000", "application/json"),
]
# testdata pattern is ({description}, {file_key}, {payload})
TEST_CLIENT_PATCH_DATA = [
    ("Valid Request", "CORP-DS0100001003", PATCH_VALID_PAYLOAD),
]
# testdata pattern is ({description}, {file_key})
TEST_CLIENT_DELETE_DATA = [
    ("Valid Request", "CORP-DS0100001000"),
]
# testdata pattern is ({description}, {file_key})
TEST_CLIENT_PUT_DATA = [
    ("Valid Request", "CORP-DS0100001000"),
]
# testdata pattern is ({description}, {filing_type}, {entity_type}, {doc_type})
TEST_CLIENT_POST_DATA = [
    ("Valid Request", "courtOrder", "BC", "court_order"),
]


def test_documents_signature_get_returns_200(client, jwt, session, minio_server):  # pylint:disable=unused-argument
    """Assert get documents/filename/signatures endpoint returns 200."""
    headers = create_header(jwt, [STAFF_ROLE])
    file_name = 'test_file.jpeg'
    rv = client.get(f'/api/v2/documents/{file_name}/signatures', headers=headers, content_type='application/json')

    assert rv.status_code == HTTPStatus.OK
    assert 'key' in rv.json and 'preSignedUrl' in rv.json


@pytest.mark.parametrize('desc,filing_type,entity_type,doc_type', TEST_CLIENT_POST_DATA)
def test_create_client_document(session, client, jwt, desc, filing_type, entity_type, doc_type):
    """Assert that adding/replacing a document by file key returns the expected result."""
    # setup
    current_app.config.update(DOCUMENT_SVC_URL=MOCK_DRS_URL)
    headers = create_header(jwt, [STAFF_ROLE])
    raw_data = None
    with open(TEST_DATAFILE, 'rb') as data_file:
        raw_data = data_file.read()
        data_file.close()

    rv = client.post(
        f"/api/v2/documents/client/{filing_type}/{entity_type}/{doc_type}",
        headers=headers,
        content_type="application/pdf",
        data=raw_data)
    # check
    assert rv.status_code == HTTPStatus.CREATED
    assert rv.json
    assert rv.json.get("key")


@pytest.mark.parametrize('desc,file_key,accept', TEST_CLIENT_GET_DATA)
def test_get_client_document(session, client, jwt, desc, file_key, accept):
    """Assert that get document by file key returns the expected result."""
    # setup
    current_app.config.update(DOCUMENT_SVC_URL=MOCK_DRS_URL)
    headers = create_header(jwt, [STAFF_ROLE])
    if accept:
        headers["Accept"] = accept
    rv = client.get(f"/api/v2/documents/client/{file_key}", headers=headers, content_type="application/json")
    # check
    assert rv
    assert rv.status_code == HTTPStatus.OK


@pytest.mark.parametrize('desc,file_key', TEST_CLIENT_DELETE_DATA)
def test_delete_client_document(session, client, jwt, desc, file_key):
    """Assert that delete document by file key returns the expected result."""
    # setup
    current_app.config.update(DOCUMENT_SVC_URL=MOCK_DRS_URL)
    headers = create_header(jwt, [STAFF_ROLE])

    rv = client.delete(f"/api/v2/documents/client/{file_key}", headers=headers, content_type="application/json")
    # check
    assert rv
    assert rv.status_code == HTTPStatus.OK


@pytest.mark.parametrize('desc,file_key', TEST_CLIENT_PUT_DATA)
def test_replace_client_document(session, client, jwt, desc, file_key):
    """Assert that adding/replacing a document by file key returns the expected result."""
    # setup
    current_app.config.update(DOCUMENT_SVC_URL=MOCK_DRS_URL)
    headers = create_header(jwt, [STAFF_ROLE])
    raw_data = None
    with open(TEST_DATAFILE, 'rb') as data_file:
        raw_data = data_file.read()
        data_file.close()

    rv = client.put(
        f"/api/v2/documents/client/{file_key}",
        headers=headers,
        content_type="application/pdf",
        data=raw_data)
    # check
    assert rv
    assert rv.status_code in (HTTPStatus.OK, HTTPStatus.ACCEPTED)


@pytest.mark.parametrize('desc,file_key,payload', TEST_CLIENT_PATCH_DATA)
def test_update_client_document_info(session, client, jwt, desc, file_key, payload):
    """Assert that update document record information works as expected."""
    # setup
    current_app.config.update(DOCUMENT_SVC_URL=MOCK_DRS_URL)
    headers = create_header(jwt, [STAFF_ROLE])
    rv = client.patch(
        f"/api/v2/documents/client/{file_key}",
        headers=headers,
        content_type="application/json",
        json=payload
    )
    # check
    assert rv
    assert rv.status_code in (HTTPStatus.OK, HTTPStatus.ACCEPTED)


@pytest.mark.parametrize('filing_type,entity_type,doc_type,drs_class,drs_type', TEST_CREATE_INFO_DATA)
def test_create_info(session, jwt, filing_type, entity_type, doc_type, drs_class, drs_type):
    """Assert that building the DRS info from the created document request produces the expected result."""
    request_params = {}
    info: dict = document.build_create_info(filing_type, entity_type, doc_type, request_params)
    assert drs_class == info.get("documentClass")
    assert drs_type == info.get("documentType")


@pytest.mark.parametrize('filename,identifier,filedate,filing_id', TEST_CREATE_INFO_DATA_EXTRA)
def test_create_info_extra(session, jwt, filename, identifier, filedate, filing_id):
    """Assert that building the DRS info from the created document request produces the expected result."""
    request_params = {}
    if filename:
        request_params[document.PARAM_FILENAME] = filename
    if identifier:
        request_params[document.PARAM_IDENTIFIER] = identifier
    if filedate:
        request_params[document.PARAM_FILEDATE] = filedate
    if filing_id:
        request_params[document.PARAM_FILING_ID] = filing_id
    info: dict = document.build_create_info("specialResolution", "CP", "coop_memorandum", request_params)
    if filename:
        assert info.get("consumerFilename") == filename
    else:
        assert not info.get("consumerFilename")
    if identifier:
        assert info.get("consumerIdentifier") == identifier
    else:
        assert not info.get("consumerIdentifier")
    if filedate:
        assert info.get("consumerFilingDate") == filedate
    else:
        assert not info.get("consumerFilingDate")
    if filing_id:
        assert info.get("consumerReferenceId") == str(filing_id)
    else:
        assert not info.get("consumerReferenceId")


@pytest.mark.parametrize('filekey,drs_id', TEST_DRS_ID_DATA)
def test_get_drs_id(session, jwt, filekey, drs_id):
    """Assert that extracting the DRS id from a business documents record filekey produces the expected result."""
    result = document.get_drs_id_from_key(filekey)
    assert result == drs_id


@pytest.mark.parametrize('filekey,doc_class', TEST_DRS_CLASS_DATA)
def test_get_drs_class(session, jwt, filekey, doc_class):
    """Assert that extracting the DRS doc class from a business documents record filekey produces the expected result."""
    result = document.get_drs_class_from_key(filekey)
    assert result == doc_class
