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

"""Tests to assure the business-tasks end-point.

Test-Suite to ensure that the /tasks endpoint is working as expected.
"""
from datetime import datetime
from http import HTTPStatus

import datedelta

from tests.unit.models import factory_business, factory_filing


AR_FILING_CURRENT_YEAR = {
    'filing': {
        'header': {
            'name': 'annualReport',
            'date': '2019-08-13'
        },
        'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08',
            'identifier': 'CP1234567',
            'legalName': 'legal name - CP1234567'
        },
        'annualReport': {
            'annualGeneralMeetingDate': str(datetime.today()).split()[0],
            'certifiedBy': 'full name',
            'email': 'no_one@never.get'
        }
    }
}

AR_FILING_PREVIOUS_YEAR = {
    'filing': {
        'header': {
            'name': 'annualReport',
            'date': '2001-08-05'
        },
        'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08',
            'identifier': 'CP1234567',
            'legalName': 'legal name - CP1234567'
        },
        'annualReport': {
            'annualGeneralMeetingDate': str(datetime.today() - datedelta.datedelta(years=1)).split()[0],
            'certifiedBy': 'full name',
            'email': 'no_one@never.get'
        }
    }
}


def test_get_tasks_no_filings(session, client):
    """Assert that to-do for the current year is returned when there are no filings."""
    identifier = 'CP7654321'
    factory_business(identifier)

    rv = client.get(f'/api/v1/businesses/{identifier}/tasks')

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json.get('tasks')) == 1  # To-do for the current year

def test_bcorps_get_tasks_no_filings(session, client):
    """Assert that to-do for the current year is returned when there are no filings."""
    identifier = 'CP7654321'
    factory_business(identifier, datetime.now(), None, 'BC')

    rv = client.get(f'/api/v1/businesses/{identifier}/tasks')

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json.get('tasks')) == 0  # To-do for the current year

def test_bcorps_get_tasks_no_filings(session, client):
    """Assert that to-do for the current year is returned when there are no filings."""
    identifier = 'CP7654321'
    factory_business(identifier, datetime.now(), None, 'BC')

    rv = client.get(f'/api/v1/businesses/{identifier}/tasks')

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json.get('tasks')) == 0  # To-do for the current year


def test_get_tasks_current_year_filing_exists(session, client):
    """Assert that only the filing for the current year is returned when only current year filing exists."""
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, AR_FILING_CURRENT_YEAR)

    print('test_get_all_business_filings - filing:', filings)

    rv = client.get(f'/api/v1/businesses/{identifier}/tasks')

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json.get('tasks')) == 1  # Current year incomplete filing only


def test_get_tasks_prev_year_incomplete_filing_exists(session, client):
    """Assert that the one incomplete filing for previous year and a to-do for current year are returned."""
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, AR_FILING_PREVIOUS_YEAR)

    print('test_get_all_business_filings - filing:', filings)

    rv = client.get(f'/api/v1/businesses/{identifier}/tasks')

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json.get('tasks')) == 2  # Previous year filing and a disabled to-do for current year.

def test_bcorp_get_tasks_prev_year_incomplete_filing_exists(session, client):
    """Assert that the one incomplete filing for previous year and a to-do for current year are returned."""
    identifier = 'CP7654321'
    b = factory_business(identifier, datetime.now()-datedelta.datedelta(years=2))
    filings = factory_filing(b, AR_FILING_PREVIOUS_YEAR)

    print('test_get_all_business_filings - filing:', filings)

    rv = client.get(f'/api/v1/businesses/{identifier}/tasks')

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json.get('tasks')) == 2  # Previous year filing and a disabled to-do for current year.

def test_bcorp_get_tasks_prev_year_incomplete_filing_exists(session, client):
    """Assert that the one incomplete filing for previous year and a to-do for current year are returned."""
    identifier = 'CP7654321'
    b = factory_business(identifier, datetime.now()-datedelta.datedelta(years=2))
    filings = factory_filing(b, AR_FILING_PREVIOUS_YEAR)

    print('test_get_all_business_filings - filing:', filings)

    rv = client.get(f'/api/v1/businesses/{identifier}/tasks')

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json.get('tasks')) == 2  # Previous year filing and a disabled to-do for current year.


def test_get_404_filing_with_invalid_business(session, client):
    """Assert that error is returned when business does not exist."""
    identifier = 'CP7654321'

    rv = client.get(f'/api/v1/businesses/{identifier}/tasks')

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{identifier} not found'}


def test_get_tasks_error_filings(session, client, jwt):
    """Assert that to-do list returns the error filings."""
    from legal_api.models import Filing
    from tests.unit.models import AR_FILING, factory_business_mailing_address, factory_error_filing
    # setup
    identifier = 'CP7654321'
    b = factory_business(identifier)
    factory_business_mailing_address(b)
    filing = factory_error_filing(b, AR_FILING)
    filing.save()
    assert filing.status == Filing.Status.ERROR.value

    # test endpoint returned filing in tasks call
    rv = client.get(f'/api/v1/businesses/{identifier}/tasks')
    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json['tasks']) == 1
    assert rv.json['tasks'][0]['task']['filing']['header']['filingId'] == filing.id
