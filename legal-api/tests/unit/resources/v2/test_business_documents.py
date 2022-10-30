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

"""Tests to assure the business-summary end-point.

Test-Suite to ensure that the /businesses../summary endpoint works as expected.
"""
import copy
from flask import current_app
from http import HTTPStatus


from legal_api.services.authz import STAFF_ROLE
from legal_api.models.document import Document, DocumentType
from tests import integration_reports
from tests.unit.models import Address, PartyRole, factory_business, factory_party_role, factory_incorporation_filing
from tests.unit.services.utils import create_header
from registry_schemas.example_data import INCORPORATION_FILING_TEMPLATE


@integration_reports
def test_get_document(requests_mock, session, client, jwt):
    """Assert that business summary is returned."""
    # setup
    identifier = 'CP7654321'
    factory_business(identifier)
    requests_mock.post(current_app.config.get('REPORT_SVC_URL'), json={'foo': 'bar'})
    headers = create_header(jwt, [STAFF_ROLE], identifier, **{'accept': 'application/pdf'})
    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/documents/summary', headers=headers)
    # check
    assert rv.status_code == HTTPStatus.OK
    assert requests_mock.called_once
    assert requests_mock.last_request._request.headers.get('Content-Type') == 'application/json'


def test_get_document_invalid_business(session, client, jwt):
    """Assert that business summary is not returned."""
    # setup
    identifier = 'CP7654321'
    factory_business(identifier)

    # test
    rv = client.get(f'/api/v2/businesses/test/documents/summary',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.NOT_FOUND


def test_get_business_documents(session, client, jwt):
    """Assert that business summary is not returned."""
    # setup
    identifier = 'CP7654321'
    factory_business(identifier)
    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/documents',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.OK
    docs_json = rv.json
    assert docs_json['documents']
    assert docs_json['documents']['summary']


def test_get_document_invalid_authorization(session, client, jwt):
    """Assert that business summary is not returned."""
    # setup
    identifier = 'CP7654321'
    factory_business(identifier)
    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/documents/summary')
    # check
    assert rv.status_code == HTTPStatus.UNAUTHORIZED

def test_get_coop_business_documents(session, client, jwt):
    """Assert that business documents have rules and memorandum."""
        # setup
    identifier = 'CP1234567'
    business = factory_business(identifier)

    INCORPORATION_APPLICATION = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    INCORPORATION_APPLICATION['filing']['incorporationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'
    INCORPORATION_APPLICATION['filing']['incorporationApplication']['nameRequest']['legalName'] = 'legal_name-CP1234567'

    effective_date = INCORPORATION_APPLICATION['filing']['header']['effectiveDate']
    filing = factory_incorporation_filing(business, INCORPORATION_APPLICATION, effective_date, effective_date)

    document_rules = Document()
    document_rules.type = DocumentType.COOP_RULES.value
    document_rules.file_key = 'cooperative_rules.pdf'
    document_rules.file_name = 'coops_rules.pdf'
    document_rules.content_type = 'pdf'
    document_rules.business_id = business.id
    document_rules.filing_id = filing.id
    document_rules.save()
    assert document_rules.id

    doccument_memorandum = Document()
    doccument_memorandum.type = DocumentType.COOP_MEMORANDUM.value
    doccument_memorandum.file_key = 'cooperative_memorandum.pdf'
    doccument_memorandum.file_name = 'coops_memorandum.pdf'
    doccument_memorandum.content_type = 'pdf'
    doccument_memorandum.business_id = business.id
    doccument_memorandum.filing_id = filing.id
    doccument_memorandum.save()
    assert doccument_memorandum.id

    rv = client.get(f'/api/v2/businesses/{identifier}/documents',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    assert rv.status_code == HTTPStatus.OK
    docs_json = rv.json
    assert docs_json['documents']
    assert docs_json['documents']['certifiedRules']
    assert docs_json['documents']['certifiedMemorandum']