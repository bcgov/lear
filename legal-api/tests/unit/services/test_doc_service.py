# Copyright © 2019 Province of British Columbia
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

"""Tests to verify the DRS API integration.

Test-Suite to ensure that the client for the DRS API service is working as expected.
"""
import pytest
from flask import current_app

from business_model.models import Document
from legal_api.services import doc_service


MOCK_DRS_URL = "https://test.api.connect.gov.bc.ca/mockTarget/doc/api/v1"
TEST_DATAFILE = 'tests/unit/services/test_doc.pdf'
PATCH_VALID_PAYLOAD = {
    "consumerIdentifier": "BC9901019",
    "consumerReferenceId": "1199642",  
    "consumerFilingDate": "2024-08-02T19:00:00+00:00"
}

# testdata pattern is ({description}, {doc_class}, {drs_id})
TEST_GET_DATA = [
    ("Valid DRS id", "CORP", "DS0100001000"),
]
# testdata pattern is ({description}, {doc_class}, {doc_type})
TEST_POST_DATA = [
    ("Valid Request", "CORP", "CORR"),
]
# testdata pattern is ({description}, {drs_id})
TEST_PUT_DATA = [
    ("Valid Request", "DS0100001000"),
]
# testdata pattern is ({description}, {drs_id}, {payload})
TEST_PATCH_DATA = [
    ("Valid Request", "DS0100001003", PATCH_VALID_PAYLOAD),
]
TEST_DELETE_DATA = [
    ("Valid Request", "DS0100001000"),
]
# testdata pattern is ({filename}, {bus_identifier}, {filing_id}, {filing_date}, {result})
TEST_CREATE_URL_DATA = [
    (None, None, None, None,""),
    ("filename.pdf", "BC2000000", "2999999", "2024-08-01",
     "?consumerFilename=filename.pdf&consumerIdentifier=BC2000000&consumerReferenceId=2999999&consumerFilingDate=2024-08-01"),
    ("filename.pdf", "BC2000000", None, None, "?consumerFilename=filename.pdf&consumerIdentifier=BC2000000"),
    ("filename.pdf", None, None, None, "?consumerFilename=filename.pdf"),
    (None, "BC2000000", None, None, "?consumerIdentifier=BC2000000"),
]
# testdata pattern is ({filekey}, {drs_id})
TEST_DRS_ID_DATA = [
    (None, None),
    ("DS0100001003", "DS0100001003"),
    ("CORP-DS0100001003", "DS0100001003"),
    ("COOP-DS0100001003", "DS0100001003"),
    ("FIRM-DS0100001003", "DS0100001003"),
]

@pytest.mark.parametrize('desc,doc_class,doc_type', TEST_POST_DATA)
def test_create_doc_record(session, jwt, desc, doc_class, doc_type):
    """Assert that doc service create document records works as expected."""
    # setup
    current_app.config.update(DOCUMENT_SVC_URL=MOCK_DRS_URL)
    doc_info: dict = {
        "documentClass": doc_class,
        "documentType": doc_type
    }
    raw_data = None
    with open(TEST_DATAFILE, 'rb') as data_file:
        raw_data = data_file.read()
        data_file.close()

    response = doc_service.create_document(doc_info, raw_data)
    # check
    assert response
    assert response.ok
    assert response.content
    result = doc_service.get_content(response)
    assert result
    assert result.get("documentClass")
    assert result.get("documentType")
    assert result.get("documentServiceId")
    assert result.get("documentURL")


@pytest.mark.parametrize('desc,drs_id', TEST_PUT_DATA)
def test_add_replace_document(session, jwt, desc, drs_id):
    """Assert that doc service add or replace a document works as expected."""
    # setup
    current_app.config.update(DOCUMENT_SVC_URL=MOCK_DRS_URL)
    doc: Document = Document(file_key=drs_id)
    raw_data = None
    with open(TEST_DATAFILE, 'rb') as data_file:
        raw_data = data_file.read()
        data_file.close()

    response = doc_service.add_replace_document(doc, raw_data)
    # check
    assert response
    assert response.ok
    assert response.content
    result = doc_service.get_content(response)
    assert result
    assert result.get("documentClass")
    assert result.get("documentType")
    assert result.get("documentServiceId")
    assert result.get("documentURL")


@pytest.mark.parametrize('desc,drs_id,payload', TEST_PATCH_DATA)
def test_update_doc_record(session, jwt, desc, drs_id, payload):
    """Assert that doc service update a document record works as expected."""
    # setup
    current_app.config.update(DOCUMENT_SVC_URL=MOCK_DRS_URL)
    doc: Document = Document(file_key=drs_id)

    response = doc_service.update_document_record(doc, payload)
    # check
    assert response
    assert response.ok
    assert response.content
    result = doc_service.get_content(response)
    assert result
    assert result.get("documentClass")
    assert result.get("documentType")
    assert result.get("documentServiceId")


@pytest.mark.parametrize('desc,drs_id', TEST_DELETE_DATA)
def test_delete_document(session, jwt, desc, drs_id):
    """Assert that doc service permanently delete a document works as expected."""
    # setup
    current_app.config.update(DOCUMENT_SVC_URL=MOCK_DRS_URL)
    doc: Document = Document(file_key=drs_id)
    response = doc_service.delete_document(doc)
    # check
    assert response
    assert response.ok


@pytest.mark.parametrize('desc,doc_class,drs_id', TEST_GET_DATA)
def test_get_doc(session, jwt, desc, doc_class, drs_id):
    """Assert that doc service DRS id search returns the expected result."""
    # setup
    current_app.config.update(DOCUMENT_SVC_URL=MOCK_DRS_URL)

    response = doc_service.get_document(drs_id, doc_class, False)
    # check
    assert response
    assert response.ok
    assert response.content
    result = doc_service.get_content(response)
    assert result
    assert result[0].get("documentClass")
    assert result[0].get("documentType")
    assert result[0].get("documentServiceId")


@pytest.mark.parametrize('filename,bus_id,filing_id,filing_date,result', TEST_CREATE_URL_DATA)
def test_create_doc_url(session, jwt, filename, bus_id, filing_id, filing_date, result):
    """Assert that doc service build create record url returns the expected result."""
    # setup
    current_app.config.update(DOCUMENT_SVC_URL=MOCK_DRS_URL)
    url = doc_service.POST_DOCUMENT_PATH.format(url=MOCK_DRS_URL,document_class="CORP",document_type="CORR") + result
    doc_info: dict = {
        "documentClass": "CORP",
        "documentType": "CORR"
    }
    if filename:
        doc_info["consumerFilename"] = filename
    if bus_id:
        doc_info["consumerIdentifier"] = bus_id
    if filing_id:
        doc_info["consumerReferenceId"] = filing_id
    if filing_date:
        doc_info["consumerFilingDate"] = filing_date
    result_url = doc_service.build_create_doc_url("CORP", "CORR", doc_info)
    assert url == result_url


@pytest.mark.parametrize('filekey,drs_id', TEST_DRS_ID_DATA)
def test_get_drs_id(session, jwt, filekey, drs_id):
    """Assert that extracting the DRS id from a business documents record filekey produces the expected result."""
    doc: Document = Document(file_key=filekey)
    result = doc_service.get_drs_id(doc)
    assert result == drs_id
