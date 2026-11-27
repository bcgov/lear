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
from requests import exceptions

from business_model.models import Document
from legal_api.resources.v2 import document
from legal_api.services.authz import PUBLIC_USER, STAFF_ROLE

from tests.unit.models import factory_business, factory_completed_filing, factory_filing
from tests.unit.services.utils import create_header, mock_new_feature


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


LINKED_FILE_KEY = 'CORP-DS0100001000'


def _link_client_document(identifier: str, completed: bool = False):
    """Link LINKED_FILE_KEY to a court order filing of a new business."""
    business = factory_business(identifier)
    filing_json = {'filing': {'header': {'name': 'courtOrder'}}}
    filing = factory_completed_filing(business, filing_json) if completed else factory_filing(business, filing_json)
    Document(type='court_order', file_key=LINKED_FILE_KEY, filing_id=filing.id, business_id=business.id).save()


def _mock_drs(mocker):
    """Mock every DRS call the client document routes make, returning the mocks by name."""
    drs_response = mocker.MagicMock(ok=True, status_code=HTTPStatus.OK, content=b'pdf')
    return {drs_call: mocker.patch.object(document.doc_service, drs_call, return_value=drs_response)
            for drs_call in ('get_document', 'add_replace_document', 'delete_document', 'update_document_record')}


@pytest.mark.parametrize('test_name, gate_on, linked, method, url_key, role, auth_roles, expected', [
    ('get_linked', True, True, 'get', LINKED_FILE_KEY, PUBLIC_USER, [], HTTPStatus.FORBIDDEN),
    ('put_linked', True, True, 'put', LINKED_FILE_KEY, PUBLIC_USER, [], HTTPStatus.FORBIDDEN),
    ('delete_linked', True, True, 'delete', LINKED_FILE_KEY, PUBLIC_USER, [], HTTPStatus.FORBIDDEN),
    ('get_linked_other_class', True, True, 'get', 'FIRM-DS0100001000', PUBLIC_USER, [], HTTPStatus.FORBIDDEN),
    ('get_linked_bare_id', True, True, 'get', 'DS0100001000', PUBLIC_USER, [], HTTPStatus.FORBIDDEN),
    ('get_linked_encoded_hyphen', True, True, 'get', 'CORP%2DDS0100001000', PUBLIC_USER, [], HTTPStatus.FORBIDDEN),
    ('get_linked_ds_class', True, True, 'get', 'DSX-DS0100001000', PUBLIC_USER, [], HTTPStatus.FORBIDDEN),
    ('delete_linked_ds_class', True, True, 'delete', 'DSX-DS0100001000', PUBLIC_USER, [], HTTPStatus.FORBIDDEN),
    ('get_linked_view_only', True, True, 'get', LINKED_FILE_KEY, PUBLIC_USER, ['view'], HTTPStatus.OK),
    ('put_linked_view_only', True, True, 'put', LINKED_FILE_KEY, PUBLIC_USER, ['view'], HTTPStatus.FORBIDDEN),
    ('put_linked_affiliated', True, True, 'put', LINKED_FILE_KEY, PUBLIC_USER, ['view', 'edit'], HTTPStatus.OK),
    ('delete_linked_affiliated', True, True, 'delete', LINKED_FILE_KEY, PUBLIC_USER, ['view', 'edit'], HTTPStatus.OK),
    ('get_linked_staff', True, True, 'get', LINKED_FILE_KEY, STAFF_ROLE, [], HTTPStatus.OK),
    ('get_unlinked', True, False, 'get', LINKED_FILE_KEY, PUBLIC_USER, [], HTTPStatus.OK),
    ('patch_public', True, False, 'patch', LINKED_FILE_KEY, PUBLIC_USER, [], HTTPStatus.FORBIDDEN),
    ('patch_staff', True, False, 'patch', LINKED_FILE_KEY, STAFF_ROLE, [], HTTPStatus.OK),
    ('get_linked_gate_off', False, True, 'get', LINKED_FILE_KEY, PUBLIC_USER, [], HTTPStatus.OK),
    ('patch_public_gate_off', False, False, 'patch', LINKED_FILE_KEY, PUBLIC_USER, [], HTTPStatus.OK),
])
def test_client_document_authorization(app, session, client, jwt, requests_mock, monkeypatch, mocker,
                                       test_name, gate_on, linked, method, url_key, role, auth_roles, expected):
    """Assert a linked document needs access to its business under any spelling of its key when the gate is on."""
    identifier = 'BC7654321'
    if linked:
        _link_client_document(identifier)
    mock_new_feature(monkeypatch, 'authV2ClientDocuments', gate_on)
    requests_mock.get(f"{app.config.get('AUTH_SVC_URL')}/entities/{identifier}/authorizations",
                      json={'roles': auth_roles})
    drs_calls = _mock_drs(mocker)

    rv = getattr(client, method)(f'/api/v2/documents/client/{url_key}',
                                 headers=create_header(jwt, [role], identifier),
                                 json={} if method == 'patch' else None)

    assert rv.status_code == expected
    assert any(drs_call.called for drs_call in drs_calls.values()) is (expected == HTTPStatus.OK)


@pytest.mark.parametrize('test_name, method, url_key', [
    ('delete_exact_key', 'delete', LINKED_FILE_KEY),
    ('put_bare_id', 'put', 'DS0100001000'),
])
def test_client_document_completed_filing_not_draft(app, session, client, jwt, monkeypatch, mocker,
                                                    test_name, method, url_key):
    """Assert a document of a completed filing cannot be replaced or deleted under any spelling of its key."""
    identifier = 'BC7654321'
    _link_client_document(identifier, completed=True)
    mock_new_feature(monkeypatch, 'authV2ClientDocuments', False)
    drs_calls = _mock_drs(mocker)

    rv = getattr(client, method)(f'/api/v2/documents/client/{url_key}',
                                 headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.FORBIDDEN
    assert not any(drs_call.called for drs_call in drs_calls.values())


@pytest.mark.parametrize('test_name, method, url_key', [
    ('get_fragment', 'get', f'{LINKED_FILE_KEY}%23x'),
    ('get_query_separator', 'get', f'{LINKED_FILE_KEY}&x'),
    ('get_lowercase', 'get', LINKED_FILE_KEY.lower()),
    ('get_wildcard', 'get', 'CORP-DS010000100%25'),
    ('get_suffix', 'get', f'{LINKED_FILE_KEY}-x'),
    ('delete_suffix', 'delete', f'{LINKED_FILE_KEY}-x'),
    ('delete_fragment', 'delete', f'{LINKED_FILE_KEY}%23x'),
    ('delete_query', 'delete', 'DS0100001000%3Fx'),
    ('put_fragment', 'put', 'DS0100001000%23x'),
    ('patch_fragment', 'patch', f'{LINKED_FILE_KEY}%23x'),
    ('get_trailing_newline', 'get', f'{LINKED_FILE_KEY}%0A'),
    ('get_trailing_space', 'get', f'{LINKED_FILE_KEY}%20'),
    ('get_double_encoded', 'get', f'{LINKED_FILE_KEY}%2523x'),
    ('get_fullwidth_digit', 'get', 'CORP-DS%EF%BC%91'),
])
def test_client_document_malformed_key(app, session, client, jwt, monkeypatch, mocker, test_name, method, url_key):
    """Assert a key DRS could read as another document's id is rejected before any check or DRS call."""
    identifier = 'BC7654321'
    _link_client_document(identifier)
    mock_new_feature(monkeypatch, 'authV2ClientDocuments', False)
    drs_calls = _mock_drs(mocker)

    rv = getattr(client, method)(f'/api/v2/documents/client/{url_key}',
                                 headers=create_header(jwt, [STAFF_ROLE], identifier),
                                 json={} if method == 'patch' else None)

    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert not any(drs_call.called for drs_call in drs_calls.values())


@pytest.mark.parametrize('test_name, url_key', [
    ('longer_id', 'CORP-DS01000010001'),
    ('shorter_id', 'CORP-DS010000100'),
])
def test_client_document_similar_key_is_unlinked(app, session, client, jwt, requests_mock, monkeypatch, mocker,
                                                 test_name, url_key):
    """Assert a key whose id only resembles a linked document's is treated as its own, unlinked document."""
    identifier = 'BC7654321'
    _link_client_document(identifier)
    mock_new_feature(monkeypatch, 'authV2ClientDocuments', True)
    requests_mock.get(f"{app.config.get('AUTH_SVC_URL')}/entities/{identifier}/authorizations", json={'roles': []})
    drs_calls = _mock_drs(mocker)

    rv = client.get(f'/api/v2/documents/client/{url_key}', headers=create_header(jwt, [PUBLIC_USER], identifier))

    assert rv.status_code == HTTPStatus.OK
    assert drs_calls['get_document'].called


def test_client_document_auth_unavailable(app, session, client, jwt, requests_mock, mocker):
    """Assert an auth outage on a linked document is a 503, not the route's generic 500."""
    identifier = 'BC7654321'
    _link_client_document(identifier)
    requests_mock.get(f"{app.config.get('AUTH_SVC_URL')}/entities/{identifier}/authorizations",
                      exc=exceptions.ConnectionError)
    _mock_drs(mocker)

    rv = client.get(f'/api/v2/documents/client/{LINKED_FILE_KEY}',
                    headers=create_header(jwt, [PUBLIC_USER], identifier))

    assert rv.status_code == HTTPStatus.SERVICE_UNAVAILABLE
