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

"""Tests to assure the ops end-point.

Test-Suite to ensure that the /ops endpoint is working as expected.
"""

import json

from registry_schemas import validate
from registry_schemas.example_data import ANNUAL_REPORT, CHANGE_OF_ADDRESS, CHANGE_OF_DIRECTORS

from tests import oracle_integration


ar_ids = []
coa_ids = []
cod_ids = []


@oracle_integration
def test_get_ar_no_results(client):
    """Assert that the business info for regular (not xpro) business is correct to spec."""
    rv = client.get('/api/v1/businesses/CP0000000/filings/annualReport')

    assert 404 == rv.status_code


@oracle_integration
def test_post_ar(client):
    """Assert that business for regular (not xpro) business is correct to spec."""
    headers = {'content-type': 'application/json'}
    fake_filing = ANNUAL_REPORT
    fake_filing['filing']['business']['identifier'] = 'CP0001965'
    fake_filing['filing']['annualReport']['annualGeneralMeetingDate'] = '2018-04-08'
    fake_filing['filing']['annualReport']['annualReportDate'] = '2018-04-08'

    rv = client.post('/api/v1/businesses/CP0001965/filings/annualReport',
                     data=json.dumps(fake_filing), headers=headers)

    assert 201 == rv.status_code
    is_valid, errors = validate(rv.json, 'filing', validate_schema=True)
    if errors:
        for err in errors:
            print('\nERROR MESSAGE:')
            print(err.message)

    assert is_valid
    ar_ids.append(str(rv.json['filing']['annualReport']['eventId']))


@oracle_integration
def test_get_ar(client):
    """Assert that the business info for regular (not xpro) business is correct to spec."""
    rv = client.get('/api/v1/businesses/CP0001965/filings/annualReport')

    assert 200 == rv.status_code
    is_valid, errors = validate(rv.json, 'filing', validate_schema=True)
    if errors:
        for err in errors:
            print('\nERROR MESSAGE:')
            print(err.message)

    assert is_valid


@oracle_integration
def test_post_ar_with_coa_cod(client):
    """Assert that business for regular (not xpro) business is correct to spec."""
    headers = {'content-type': 'application/json'}
    fake_filing = ANNUAL_REPORT
    fake_filing['filing']['changeOfAddress'] = CHANGE_OF_ADDRESS
    fake_filing['filing']['changeOfAddress']['deliveryAddress']['addressCountry'] = 'Canada'
    fake_filing['filing']['changeOfAddress']['mailingAddress']['addressCountry'] = 'Canada'
    fake_filing['filing']['changeOfDirectors'] = CHANGE_OF_DIRECTORS
    for director in fake_filing['filing']['changeOfDirectors']['directors']:
        director['deliveryAddress']['addressCountry'] = 'Canada'
    fake_filing['filing']['business']['identifier'] = 'CP0001965'
    fake_filing['filing']['annualReport']['annualGeneralMeetingDate'] = '2019-04-08'
    fake_filing['filing']['annualReport']['annualReportDate'] = '2019-04-08'

    rv = client.post('/api/v1/businesses/CP0001965/filings/annualReport',
                     data=json.dumps(fake_filing), headers=headers)

    assert 201 == rv.status_code
    is_valid, errors = validate(rv.json, 'filing', validate_schema=True)
    if errors:
        for err in errors:
            print('\nERROR MESSAGE:')
            print(err.message)

    assert is_valid
    ar_ids.append(str(rv.json['filing']['annualReport']['eventId']))
    coa_ids.append(str(rv.json['filing']['changeOfAddress']['eventId']))
    cod_ids.append(str(rv.json['filing']['changeOfDirectors']['eventId']))


@oracle_integration
def test_get_ar_by_id(client):
    """Test getting an AR by year."""
    for event_id in ar_ids:
        rv = client.get(f'/api/v1/businesses/CP0001965/filings/annualReport?eventId={event_id}')

        assert 200 == rv.status_code
        assert event_id == str(rv.json['filing']['annualReport']['eventId'])
        is_valid, errors = validate(rv.json, 'filing', validate_schema=True)
        if errors:
            for err in errors:
                print('\nERROR MESSAGE:')
                print(err.message)

        assert is_valid


@oracle_integration
def test_get_ar_by_id_wrong_corp(client):
    """Assert that a coop searching for an ar filing associated with a different coop returns a 404."""
    rv = client.get(f'/api/v1/businesses/CP0000005/filings/annualReport?eventId={ar_ids[0]}')
    assert 404 == rv.status_code


@oracle_integration
def test_get_ar_by_year(client):
    """Test getting an AR by year."""
    years = ['2018', '2019']

    for year in years:
        rv = client.get(f'/api/v1/businesses/CP0001965/filings/annualReport?year={year}')

        assert 200 == rv.status_code
        assert f'{year}' == rv.json['filing']['annualReport']['annualGeneralMeetingDate'][:4]

        is_valid, errors = validate(rv.json, 'filing', validate_schema=True)
        if errors:
            for err in errors:
                print('\nERROR MESSAGE:')
                print(err.message)

        assert is_valid


@oracle_integration
def test_get_ar_by_year_invalid(client):
    """Assert that the business info for regular (not xpro) business is correct to spec."""
    rv = client.get('/api/v1/businesses/CP0001965/filings/annualReport?year=2020')

    assert 404 == rv.status_code


@oracle_integration
def test_post_ar_with_invalid_data(client):
    """Assert that the AR post validates correct data before proceeding."""
    headers = {'content-type': 'application/json'}

    fake_filing = {
        "filing": {
            "annualReport": {
                "annualGeneralMeetingDate": "2017-11-23",
                "certifiedBy": "Joe Smith",
                "email": "nobody@nothing.com"
            },
            "business_info": {
            },
            "header": {
                "date": "2017-11-23",
                "name": "annualReport"
            }
        }
    }
    rv = client.post('/api/v1/businesses/CP0001965/filings/annualReport',
                     data=json.dumps(fake_filing), headers=headers)

    assert 400 == rv.status_code
    assert 'Error: Invalid Filing schema' == rv.json['message']


@oracle_integration
def test_post_ar_with_mismatched_identifer(client):
    """Assert that the identifier (corp num) must match between URL and posted data."""
    headers = {'content-type': 'application/json'}

    fake_filing = ANNUAL_REPORT
    fake_filing['filing']['business']['identifier'] = 'CP0001965'
    rv = client.post('/api/v1/businesses/CP0001966/filings/annualReport',
                     data=json.dumps(fake_filing), headers=headers)

    assert 400 == rv.status_code
    assert 'Error: Identifier in URL does not match identifier in filing data' == rv.json['message']
