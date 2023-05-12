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

"""Tests to assure the business-filing end-point.

Test-Suite to ensure that the /businesses endpoint is working as expected.
"""
import copy
from http import HTTPStatus

import pytest
from registry_schemas.example_data import (
    ANNUAL_REPORT,
    CHANGE_OF_ADDRESS,
    CHANGE_OF_DIRECTORS,
    FILING_HEADER,
    INCORPORATION_FILING_TEMPLATE,
)

from legal_api.services.authz import BASIC_USER, STAFF_ROLE
from tests import integration_reports
from tests.unit.models import factory_legal_entity, factory_filing, factory_incorporation_filing  # noqa:E501,I001
from tests.unit.services.utils import create_header

from .gold_files import matches_sent_snapshot, retrieve_name


CONTENT_TYPE_APPLICATION_JSON = 'application/json'


@integration_reports
@pytest.mark.parametrize('role', [(BASIC_USER), (STAFF_ROLE)])
def test_get_annual_report_pdf_error_on_multiple(session, client, jwt, role):
    """Assert that the businesses AR can be returned as a PDF."""
    identifier = 'CP7654321'
    b = factory_legal_entity(identifier)
    factory_filing(b, ANNUAL_REPORT)

    rv = client.get(f'/api/v1/businesses/{identifier}/filings',
                    headers=create_header(jwt,
                                          [role],
                                          identifier,
                                          **{'accept': 'application/pdf'})
                    )

    assert rv.status_code == HTTPStatus.NOT_ACCEPTABLE
    assert rv.content_type == CONTENT_TYPE_APPLICATION_JSON
    assert rv.json == {'message': 'Cannot return a single PDF of multiple filing submissions.'}


@integration_reports
def test_get_pdf_error_missing_template(session, client, jwt):
    """Assert that the businesses AR can be returned as a PDF."""
    identifier = 'CP7654321'
    b = factory_legal_entity(identifier)

    unknown_filing = copy.deepcopy(ANNUAL_REPORT)
    unknown_filing['filing']['header']['name'] = 'unknownFiling'

    filing = factory_filing(b, unknown_filing)

    rv = client.get(f'/api/v1/businesses/{identifier}/filings/{filing.id}',
                    headers=create_header(jwt,
                                          [STAFF_ROLE],
                                          identifier,
                                          **{'accept': 'application/pdf'})
                    )

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': 'Available on paper only.'}


ANNUAL_REPORT['filing']['annualReport']['directors'][0]['deliveryAddress']['addressCountry'] = 'CA'
ANNUAL_REPORT['filing']['annualReport']['offices']['registeredOffice']['deliveryAddress']['addressCountry'] = 'CA'
ANNUAL_REPORT['filing']['annualReport']['offices']['registeredOffice']['mailingAddress']['addressCountry'] = 'CA'

COD = copy.deepcopy(FILING_HEADER)
COD['filing']['header']['name'] = 'changeOfDirectors'
COD['filing']['changeOfDirectors'] = CHANGE_OF_DIRECTORS
CHANGE_OF_DIRECTORS['directors'][0]['deliveryAddress']['addressCountry'] = 'CA'

COA = copy.deepcopy(FILING_HEADER)
COA['filing']['header']['name'] = 'changeOfAddress'
COA['filing']['changeOfDirectors'] = CHANGE_OF_ADDRESS


@integration_reports
@pytest.mark.parametrize('role', [(BASIC_USER), (STAFF_ROLE)])
@pytest.mark.parametrize('filing_submission', [(ANNUAL_REPORT), (COA), (COD)])
def test_get_filing_submission_pdf(requests_mock, session, client, jwt, role, filing_submission):
    """Assert that the businesses AR can be returned as a PDF."""
    from flask import current_app
    identifier = 'CP7654321'
    b = factory_legal_entity(identifier)
    filings = factory_filing(b, filing_submission)

    print('test_get_all_business_filings - filing:', filings)

    requests_mock.post(current_app.config.get('REPORT_SVC_URL'), json={'foo': 'bar'})

    rv = client.get(f'/api/v1/businesses/{identifier}/filings/{filings.id}',
                    headers=create_header(jwt,
                                          [role],
                                          identifier,
                                          **{'accept': 'application/pdf'})
                    )

    ignore_vars = {'templateVars': {'environment': 'ignored'}}

    assert rv.status_code == HTTPStatus.OK
    assert requests_mock.called_once
    assert requests_mock.last_request._request.headers.get('Content-Type') == CONTENT_TYPE_APPLICATION_JSON

    assert matches_sent_snapshot(filing_submission, requests_mock.last_request.json(), retrieve_name(filing_submission),
                                 **ignore_vars)


INCORPORATION_APPLICATION = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
INCORPORATION_APPLICATION['filing']['incorporationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'
INCORPORATION_APPLICATION['filing']['incorporationApplication']['nameRequest']['legalName'] = 'legal_name-CP1234567'


@integration_reports
@pytest.mark.parametrize('role', [(BASIC_USER), (STAFF_ROLE)])
@pytest.mark.parametrize('report_details', [
    ({'type': 'noa', 'name': 'noticeOfArticles'}),
    ({'type': None, 'name': 'incorporationApplication'}),
    ({'type': 'certificate', 'name': 'certificateOfIncorporation'})])
def test_get_incorporation_reports(requests_mock, session, client, jwt, role, report_details):
    """Assert that the businesses AR can be returned as a PDF."""
    from flask import current_app
    identifier = 'CP7654321'
    b = factory_legal_entity(identifier)

    effective_date = INCORPORATION_APPLICATION['filing']['header']['effectiveDate']
    filings = factory_incorporation_filing(b, INCORPORATION_APPLICATION, effective_date, effective_date)

    print('test_get_all_business_filings - filing:', filings)

    requests_mock.post(current_app.config.get('REPORT_SVC_URL'), json={'foo': 'bar'})

    report_type = report_details['type']
    report_name = report_details['name']
    report_url = f'/api/v1/businesses/{identifier}/filings/{filings.id}'
    if report_type:
        report_url = f'{report_url}?type={report_type}'
    print(report_url)
    rv = client.get(report_url,
                    headers=create_header(jwt,
                                          [role],
                                          identifier,
                                          **{'accept': 'application/pdf'})
                    )

    ignore_vars = {'templateVars': {'environment': 'ignored'}}

    assert rv.status_code == HTTPStatus.OK
    assert requests_mock.called_once
    assert requests_mock.last_request._request.headers.get('Content-Type') == CONTENT_TYPE_APPLICATION_JSON

    assert matches_sent_snapshot(INCORPORATION_APPLICATION, requests_mock.last_request.json(), report_name,
                                 **ignore_vars)
