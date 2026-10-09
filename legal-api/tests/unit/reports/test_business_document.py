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

import pytest

from business_model.models import PartyRole
from legal_api.reports.business_document import BusinessDocument
from legal_api.services.authz import STAFF_ROLE
from tests.unit.services.utils import create_header

from tests.unit.models import factory_address, factory_business, factory_business_mailing_address, factory_party_role
from tests.unit.reports import (
    make_amalgamation_filing_mock,
    make_colin_amalgamating_business,
    make_foreign_amalgamating_business,
    set_amalgamation_details,
)


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


@pytest.mark.parametrize(
    'foreign_id,foreign_country,foreign_region,expected_jurisdiction',
    [
        ('A1234567', 'US', 'WA', 'United States'),
        ('UK1234567', 'GB', None, 'United Kingdom'),
        ('7654321', 'CA', 'AB', 'Alberta'),
    ],
    ids=[
        'foreign with A-prefix identifier',
        'foreign GB',
        'foreign CA province',
    ],
)
def test_set_amalgamation_details(
    session, app, jwt, monkeypatch, foreign_id, foreign_country, foreign_region, expected_jurisdiction
):
    """Assert a foreign row renders from its stored columns alone - N/A identifier, COLIN never called."""
    foreign_name = 'Foreign Corp'

    ab = make_foreign_amalgamating_business(
        foreign_identifier=foreign_id,
        foreign_name=foreign_name,
        foreign_jurisdiction=foreign_country,
        foreign_jurisdiction_region=foreign_region,
    )

    colin_call_count = {'count': 0}

    def mock_colin(identifier):
        colin_call_count['count'] += 1
        return None, None

    business_json = set_amalgamation_details(
        app, jwt, session, monkeypatch,
        amalgamating_businesses_list=[ab],
        colin_query_side_effect=mock_colin,
    )

    entities = business_json.get('amalgamatedEntities', [])
    assert len(entities) == 1
    entity = entities[0]

    assert colin_call_count['count'] == 0
    assert entity['identifier'] == 'N/A'
    assert entity['jurisdiction'] == expected_jurisdiction
    assert entity['legalName'] == foreign_name
    assert entity['isBcCompany'] is False
    assert entity['isExtraprovincial'] is False


@pytest.mark.parametrize(
    'colin_jurisdiction, expected_jurisdiction',
    [
        ('ON', 'Ontario'),
        ('FD', 'Federal'),
    ],
    ids=[
        'expro province',
        'expro federal',
    ],
)
def test_set_amalgamation_details_expro(session, app, jwt, monkeypatch, colin_jurisdiction, expected_jurisdiction):
    """Assert an expro row (colin_identifier) resolves its name and home jurisdiction from COLIN."""
    expro_identifier = 'A1234567'
    ab = make_colin_amalgamating_business(expro_identifier)

    def mock_colin(identifier):
        assert identifier == expro_identifier
        return {'business': {'legalName': 'Expro Corp', 'legalType': 'A',
                             'jurisdiction': colin_jurisdiction}}, HTTPStatus.OK

    business_json = set_amalgamation_details(
        app, jwt, session, monkeypatch,
        amalgamating_businesses_list=[ab],
        colin_query_side_effect=mock_colin,
    )

    entities = business_json.get('amalgamatedEntities', [])
    assert len(entities) == 1
    entity = entities[0]

    assert entity['identifier'] == expro_identifier
    assert entity['legalName'] == 'Expro Corp'
    assert entity['jurisdiction'] == expected_jurisdiction
    assert entity['isBcCompany'] is False
    assert entity['isExtraprovincial'] is True


def test_set_amalgamation_details_colin_business(session, app, jwt, monkeypatch):
    """Assert a COLIN amalgamating business renders from the COLIN lookup with BC jurisdiction."""
    colin_identifier = 'BC5556667'
    ab = make_colin_amalgamating_business(colin_identifier)

    def mock_colin(identifier):
        assert identifier == colin_identifier
        return {'business': {'legalName': 'Colin Corp Ltd.', 'legalType': 'BC'}}, HTTPStatus.OK

    business_json = set_amalgamation_details(
        app, jwt, session, monkeypatch,
        amalgamating_businesses_list=[ab],
        colin_query_side_effect=mock_colin,
    )

    entities = business_json.get('amalgamatedEntities', [])
    assert len(entities) == 1
    entity = entities[0]

    assert entity['identifier'] == colin_identifier
    assert entity['legalName'] == 'Colin Corp Ltd.'
    assert entity['jurisdiction'] == 'British Columbia'
    assert entity['isBcCompany'] is True
    assert entity['isExtraprovincial'] is False


@pytest.mark.parametrize('has_receiver, cessation_date, expected_count', [
    (True, None, 1),
    (False, '2026-06-02', 0)
])
def test_summary_includes_receivers(session, app, jwt, has_receiver, cessation_date, expected_count):
    """Assert that the business summary correctly includes receivers."""
    identifier = 'BC7654321'
    request_ctx = app.test_request_context(
        headers=create_header(jwt, [STAFF_ROLE], identifier)
    )
    with request_ctx:
        business = factory_business(identifier=identifier, entity_type='BC')
        factory_business_mailing_address(business)

        receiver = factory_party_role(
            delivery_address=factory_address('delivery street', 'delivery'),
            mailing_address=factory_address('mailing street', 'mailing'),
            appointment_date='2026-01-01',
            cessation_date=cessation_date,
            officer={
                'firstName': 'first',
                'lastName': 'last',
                'middleInitial': 'mid',
                'partyType': 'person',
                'organizationName': ''
            },
            role_type=PartyRole.RoleTypes.RECEIVER
        )

        receiver.business_id = business.id
        session.add(receiver)
        session.commit()

        report = BusinessDocument(business, 'summary')
        filename = report._get_report_filename()
        assert filename
        template = report._get_template()
        assert template
        template_data = report._get_template_data()

        assert 'receivers' in template_data
        assert len(template_data['receivers']) == expected_count

        if expected_count > 0:
            assert template_data['receivers'][0]['role'] == 'receiver'

