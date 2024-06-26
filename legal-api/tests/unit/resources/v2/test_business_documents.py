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
from legal_api.models.business import Business
import pycountry


from legal_api.services.authz import STAFF_ROLE
from legal_api.models.document import Document, DocumentType
from tests import integration_reports
from tests.unit.models import factory_business, factory_completed_filing, factory_incorporation_filing
from tests.unit.services.utils import create_header
from registry_schemas.example_data import ALTERATION, FILING_HEADER, INCORPORATION_FILING_TEMPLATE
from unittest.mock import patch, PropertyMock


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

    document_memorandum = Document()
    document_memorandum.type = DocumentType.COOP_MEMORANDUM.value
    document_memorandum.file_key = 'cooperative_memorandum.pdf'
    document_memorandum.file_name = 'coops_memorandum.pdf'
    document_memorandum.content_type = 'pdf'
    document_memorandum.business_id = business.id
    document_memorandum.filing_id = filing.id
    document_memorandum.save()
    assert document_memorandum.id

    rv = client.get(f'/api/v2/businesses/{identifier}/documents',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    assert rv.status_code == HTTPStatus.OK
    docs_json = rv.json
    assert docs_json['documents']
    assert docs_json['documents']['certifiedRules']
    assert docs_json['documents']['certifiedMemorandum']
    assert docs_json['documentsInfo']['certifiedRules']['uploaded']
    assert docs_json['documentsInfo']['certifiedRules']['key']
    assert docs_json['documentsInfo']['certifiedRules']['name']
    assert docs_json['documentsInfo']['certifiedMemorandum']['uploaded']
    assert docs_json['documentsInfo']['certifiedMemorandum']['key']
    assert docs_json['documentsInfo']['certifiedMemorandum']['name']

    # Testing scenario where we have a special resolution with the memorandum included in the resolution.
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['name'] = 'specialResolution'
    filing['filing']['alteration'] = copy.deepcopy(ALTERATION)
    filing['filing']['alteration']['memorandumInResolution'] = True
    filing['filing']['alteration']['rulesInResolution'] = True
    factory_completed_filing(business, filing)

    rv = client.get(f'/api/v2/businesses/{identifier}/documents',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    assert rv.status_code == HTTPStatus.OK
    docs_json = rv.json
    assert docs_json['documents']
    assert docs_json['documents']['certifiedMemorandum']
    assert docs_json['documents']['certifiedRules']
    assert docs_json['documentsInfo']['certifiedRules']['uploaded']
    assert docs_json['documentsInfo']['certifiedMemorandum']['uploaded']
    assert docs_json['documentsInfo']['certifiedRules']['includedInResolutionDate']
    assert docs_json['documentsInfo']['certifiedMemorandum']['includedInResolutionDate']
    assert docs_json['documentsInfo']['certifiedRules']['includedInResolution']
    assert docs_json['documentsInfo']['certifiedMemorandum']['includedInResolution']
    assert docs_json['documentsInfo']['certifiedRules']['key']
    assert docs_json['documentsInfo']['certifiedMemorandum']['key']
    assert docs_json['documentsInfo']['certifiedRules']['name']
    assert docs_json['documentsInfo']['certifiedMemorandum']['name']


def test_get_business_summary_involuntary_dissolution(requests_mock, session, client, jwt):
    """Assert that business summary returns correct information for Involuntary Dissolution."""
    # setup
    identifier = 'CP7654321'
    business = factory_business(identifier, entity_type='BEN', state='HISTORICAL')

    # create a dissolution filing with involuntary dissolution
    INVOLUNTARY_DISSOLUTION = {
        'filing': {
            'header': {
                'name': 'dissolution',
                'date': '2023-01-19T19:08:53.733202+00:00',
                'certifiedBy': 'full name',
                'filingId': 1,
                'effectiveDate': '2023-01-19T19:08:53.733202+00:00'
            },
            'business': {
                'identifier': 'CP7654321',
                'legalName': 'CP7654321 B.C. LTD.',
                'legalType': 'BEN'
            },
            'dissolution': {
                'dissolutionDate': '2023-01-19',
                'dissolutionType': 'involuntary',
            }
        }
    }

    # create and save the filing
    factory_completed_filing(business, INVOLUNTARY_DISSOLUTION, filing_type='dissolution',
                                      filing_sub_type='involuntary')
    # mock the meta_data property
    with patch('legal_api.models.Filing.meta_data', new_callable=PropertyMock) as mock_meta_data:
        mock_meta_data.return_value = {
            'dissolution': {
                'dissolutionType': 'involuntary',
                'dissolutionDate': '2023-01-19'
            },
            "legalFilings": [
                "dissolution"
            ],
        }

        # mock the external report service
        requests_mock.post(current_app.config.get('REPORT_SVC_URL'), json={'foo': 'bar'})
        headers = create_header(jwt, [STAFF_ROLE], identifier, **{'accept': 'application/json'})

        # test
        rv = client.get(f'/api/v2/businesses/{identifier}/documents/summary', headers=headers)

        # check
        assert rv.status_code == HTTPStatus.OK
        response_json = rv.json

        # check response content
        assert 'business' in response_json
        assert response_json['business']['identifier'] == identifier
        assert response_json['business']['state'] == 'HISTORICAL'
        assert response_json['reportType'] == 'summary'

        # ensure the dissolution filing is included in stateFilings
        assert 'stateFilings' in response_json
        assert len(response_json['stateFilings']) > 0
        state_filing = response_json['stateFilings'][0]
        assert state_filing['filingType'] == 'dissolution'
        assert state_filing['filingName'] == 'Involuntary Dissolution'

def test_set_continuation_in_details(requests_mock, session, client, jwt):
    """Assert that the _set_continuation_in_details method processes and sets the correct continuation in details."""

    # setup
    identifier = 'C1234567'
    business = factory_business(identifier)
    print(business.identifier)

    # Create mock continuation in filing
    CONTINUATION_IN = {
        'filing': {
            'header': {
                'name': 'continuationIn',
                'filingId': 1,
                'certifiedBy': 'full name',
                'isFutureEffective': False
            },
            'business': {
                'legalType': 'CUL',
                'identifier': identifier,
                'foundingDate': '2024-01-01T18:00:00.162470+00:00'
            },
            'continuationIn': {
                'mode': 'MANUAL',
                'offices': {
                    'registeredOffice': {
                        'mailingAddress': {
                            'postalCode': '123 456',
                            'addressCity': 'Victoria',
                            'addressRegion': 'BC',
                            'streetAddress': '123 Main St',
                            'addressCountry': 'CA'
                        },
                        'deliveryAddress': {
                            'postalCode': '123 456',
                            'addressCity': 'Victoria',
                            'addressRegion': 'BC',
                            'streetAddress': '123 Main St',
                            'addressCountry': 'CA'
                        }
                    }
                },
                'parties': [
                    {
                        'officer': {
                            'id': 'officer1',
                            'firstName': 'John',
                            'lastName': 'Doe',
                            'partyType': 'person'
                        },
                        'mailingAddress': {
                            'postalCode': '123 456',
                            'addressCity': 'Victoria',
                            'addressRegion': 'BC',
                            'streetAddress': '456 Elm St',
                            'addressCountry': 'CA'
                        },
                        'deliveryAddress': {
                            'postalCode': '123 456',
                            'addressCity': 'Victoria',
                            'addressRegion': 'BC',
                            'streetAddress': '456 Elm St',
                            'addressCountry': 'CA'
                        }
                    }
                ],
                'foreignJurisdiction': {
                    'region': 'MB',
                    'country': 'CA',
                    'incorporationDate': '2024-01-01'
                }
            }
        }
    }

    # Create and save the filing
    factory_completed_filing(business, CONTINUATION_IN, filing_type='continuationIn')

    # Mock the meta_data property
    with patch('legal_api.models.Filing.meta_data', new_callable=PropertyMock) as mock_meta_data:
        mock_meta_data.return_value = {
            'continuationIn': {
                'mode': 'MANUAL',
                'offices': CONTINUATION_IN['filing']['continuationIn']['offices'],
                'parties': CONTINUATION_IN['filing']['continuationIn']['parties'],
                'foreignJurisdiction': CONTINUATION_IN['filing']['continuationIn']['foreignJurisdiction'],
            }
        }

        # Mock the external report service
        requests_mock.post(current_app.config.get('REPORT_SVC_URL'), json={'foo': 'bar'})
        headers = create_header(jwt, [STAFF_ROLE], identifier, **{'accept': 'application/json'})

        # Test
        rv = client.get(f'/api/v2/businesses/{identifier}/documents/summary', headers=headers)

        assert rv.status_code == HTTPStatus.OK
        response_json = rv.json

        # Verify the continuation in details are set correctly in the business dictionary
        assert 'business' in response_json
        assert 'continuationIn' in response_json
        continuation_in_info = response_json['continuationIn']
        assert continuation_in_info['mode'] == 'MANUAL'
        assert 'offices' in continuation_in_info
        assert 'parties' in continuation_in_info
        assert 'foreignJurisdiction' in continuation_in_info

        foreign_jurisdiction = continuation_in_info['foreignJurisdiction']
        assert foreign_jurisdiction['region'] == pycountry.subdivisions.get(code='CA-MB').name.upper()
        assert foreign_jurisdiction['country'] == pycountry.countries.get(alpha_2='CA').name.upper()
        assert foreign_jurisdiction['incorporationDate'] == 'January 1, 2024'