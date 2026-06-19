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

"""Test-Suite to ensure that the Business Report class is working as expected."""
from http import HTTPStatus
from unittest.mock import MagicMock

import pytest

from legal_api.reports.business_document import BusinessDocument
from legal_api.services.authz import STAFF_ROLE
from tests.unit.services.utils import create_header

from tests.unit.models import factory_business, factory_business_mailing_address
from tests.unit.reports import make_amalgamation_filing_mock, make_foreign_amalgamating_business, set_amalgamation_details


@pytest.mark.parametrize(
    'identifier, entity_type, document_name',
    [
        ('CP1234567', 'CP', 'summary'),
        ('BC7654321', 'BEN', 'summary'),
        ('FM0000123', 'SP', 'summary'),
        ('FM1100012', 'GP', 'summary'),
        ('CP1234567', 'CP', 'cogs'),
        ('BC7654321', 'BEN', 'cogs'),
        ('CP1234567', 'CP', 'cstat'),
        ('BC7654321', 'BEN', 'cstat'),
        ('FM0000123', 'SP', 'cstat'),
        ('FM1100012', 'GP', 'cstat'),
        ('CP1234567', 'CP', 'lseal'),
        ('BC7654321', 'BEN', 'lseal'),
        ('FM0000123', 'SP', 'lseal'),
        ('FM1100012', 'GP', 'lseal'),
    ]
)
def test_get_json(session, app, jwt, identifier, entity_type, document_name):
    """Assert business document can be returned as JSON."""
    request_ctx = app.test_request_context(
        headers=create_header(jwt, [STAFF_ROLE], identifier)
    )
    with request_ctx:
        business = factory_business(identifier=identifier, entity_type=entity_type)
        factory_business_mailing_address(business)
        report = BusinessDocument(business, document_name)
        json_resp = report.get_json()
        assert json_resp
        assert json_resp[1] == HTTPStatus.OK
        json = json_resp[0]
        assert json['business']
        assert json['reportType'] == document_name
        assert json['reportDateTime']
        assert json['registrarInfo']
        assert json['entityDescription']
        assert json['entityAct']


@pytest.mark.parametrize(
    'identifier, entity_type, document_name',
    [
        ('CP1234567', 'CP', 'summary'),
        ('BC1234567', 'BC', 'summary'),
        ('BC7654321', 'BEN', 'summary'),
        ('BC1234567', 'CC', 'summary'),
        ('BC7654321', 'ULC', 'summary'),
        ('BC1234567', 'LLC', 'summary'),
        ('FM0000123', 'SP', 'summary'),
        ('FM1100012', 'GP', 'summary'),
        ('CP1234567', 'CP', 'cogs'),
        ('BC7654321', 'BEN', 'cogs'),
        ('CP1234567', 'CP', 'cstat'),
        ('BC7654321', 'BEN', 'cstat'),
        ('FM0000123', 'SP', 'cstat'),
        ('FM1100012', 'GP', 'cstat'),
        ('CP1234567', 'CP', 'lseal'),
        ('BC7654321', 'BEN', 'lseal'),
        ('FM0000123', 'SP', 'lseal'),
        ('FM1100012', 'GP', 'lseal'),
    ]
)
def test_get_pdf(session, app, jwt, identifier, entity_type, document_name):
    """Assert business document can be returned as a PDF."""
    request_ctx = app.test_request_context(
        headers=create_header(jwt, [STAFF_ROLE], identifier)
    )
    with request_ctx:
        business = factory_business(identifier=identifier, entity_type=entity_type)
        factory_business_mailing_address(business)
        report = BusinessDocument(business, document_name)
        filename = report._get_report_filename()
        assert filename
        template = report._get_template()
        assert template
        template_data = report._get_template_data()
        assert template_data
        assert template_data['business']
        assert template_data['formatted_founding_date_time']
        assert template_data['formatted_founding_date']
        assert template_data['registrarInfo']
        assert template_data['entityDescription']
        assert template_data['entityAct']


@pytest.mark.parametrize('foreign_id,foreign_country,foreign_region,colin_jurisdiction,expected_id,expected_jurisdiction,expected_mock_calls',[
    ('A1234567', 'CA', 'BC', 'ON', 'A1234567', 'Ontario', 1),
    ('A1234567', 'CA', 'BC', 'FD', 'A1234567', 'Federal', 1),
    ('A1234567', 'US', 'WA', None, 'N/A', 'United States', 1),
    ('UK1234567', 'GB', None, None, 'N/A', 'United Kingdom', 0),
], ids=[
    'expro province',
    'expro federal',
    'Non expro with expro like identifier',
    'Non expro'
])
def test_set_amalgamation_details(
    session, app, jwt, monkeypatch, foreign_id, foreign_country, foreign_region,
    colin_jurisdiction, expected_id, expected_jurisdiction, expected_mock_calls
):
    """Assert that expros resolve as expected. 
    
    Foreign businesses with identifier starting with 'A' and existing in colin are treated as an expro: 
     - identifier is set to the foreign_identifier
     - region_code is taken from the colin response's business.jurisdiction field.
    """
    foreign_name = 'Foreign Corp'

    ab = make_foreign_amalgamating_business(
        foreign_identifier=foreign_id,
        foreign_name=foreign_name,
        foreign_jurisdiction=foreign_country,
        foreign_jurisdiction_region=foreign_region,  # original region — is overwritten for expros
    )

    colin_call_count = {'count': 0}

    def mock_colin(identifier):
        resp = MagicMock()
        colin_call_count['count'] += 1
        if colin_jurisdiction:
            resp.status_code = HTTPStatus.OK
            resp.json.return_value = {'business': {'jurisdiction': colin_jurisdiction}}
        else:
            resp.status_code = HTTPStatus.NOT_FOUND
        return resp

    business_json = set_amalgamation_details(
        app, jwt, session, monkeypatch,
        amalgamating_businesses_list=[ab],
        colin_query_side_effect=mock_colin,
    )

    entities = business_json.get('amalgamatedEntities', [])
    assert len(entities) == 1
    entity = entities[0]

    assert colin_call_count['count'] == expected_mock_calls
    assert entity['identifier'] == expected_id
    assert entity['jurisdiction'] == expected_jurisdiction
    assert entity['legalName'] == foreign_name
