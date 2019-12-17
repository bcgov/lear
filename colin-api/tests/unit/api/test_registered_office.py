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

"""Tests to assure the change of address filing end-point."""

import json

from registry_schemas import validate
from registry_schemas.example_data import CHANGE_OF_ADDRESS, FILING_HEADER

from tests import oracle_integration
from tests.unit.api.test_ar import coa_ids as coa_ids


ids = coa_ids


@oracle_integration
def test_get_current(client):
    """Assert that the business info for regular (not xpro) business is correct to spec."""
    rv = client.get('/api/v1/businesses/CP0001965/office')

    assert 200 == rv.status_code

    assert rv.json['registeredOffice']
    assert rv.json['registeredOffice']['deliveryAddress']
    assert rv.json['registeredOffice']['mailingAddress']


@oracle_integration
def test_post_coa(client):
    """Assert that the business info for regular (not xpro) business is correct to spec."""
    headers = {'content-type': 'application/json'}

    fake_filing = FILING_HEADER
    fake_filing['filing']['header']['name'] = 'changeOfAddress'
    fake_filing['filing']['business']['identifier'] = 'CP0001965'
    fake_filing['filing']['changeOfAddress'] = CHANGE_OF_ADDRESS
    fake_filing['filing']['changeOfAddress']['offices']['registeredOffice']['deliveryAddress']['addressCountry'] = \
        'Canada'
    fake_filing['filing']['changeOfAddress']['offices']['registeredOffice']['mailingAddress']['addressCountry'] = \
        'Canada'
    rv = client.post('/api/v1/businesses/CP0001965/filings/changeOfAddress',
                     data=json.dumps(fake_filing), headers=headers)

    assert 201 == rv.status_code
    is_valid, errors = validate(rv.json, 'filing', validate_schema=True)
    if errors:
        for err in errors:
            print('\nERROR MESSAGE:')
            print(err.message)

    assert is_valid
    assert "changeOfAddress" == rv.json['filing']['header']['name']
    ids.append(str(rv.json['filing']['changeOfAddress']['eventId']))
    assert str(rv.json['filing']['changeOfAddress']['eventId']) in ids


@oracle_integration
def test_get_coa(client):
    """Assert that the business info for regular (not xpro) business is correct to spec."""
    rv = client.get('/api/v1/businesses/CP0001965/filings/changeOfAddress')

    assert 200 == rv.status_code
    is_valid, errors = validate(rv.json, 'filing', validate_schema=True)
    if errors:
        for err in errors:
            print('\nERROR MESSAGE:')
            print(err.message)

    assert is_valid
    assert "changeOfAddress" == rv.json['filing']['header']['name']


@oracle_integration
def test_get_coa_by_id(client):
    """Assert that the business info for regular (not xpro) business is correct to spec."""
    for event_id in ids:
        rv = client.get(f'/api/v1/businesses/CP0001965/filings/changeOfAddress?eventId={event_id}')

        assert 200 == rv.status_code
        is_valid, errors = validate(rv.json, 'filing', validate_schema=True)
        if errors:
            for err in errors:
                print('\nERROR MESSAGE:')
                print(err.message)

        assert is_valid
        assert "changeOfAddress" == rv.json['filing']['header']['name']
        assert f'{event_id}' == str(rv.json['filing']['changeOfAddress']['eventId'])


@oracle_integration
def test_get_coa_by_id_wrong_corp(client):
    """Assert that a coop searching for a coa filing associated with a different coop returns a 404."""
    rv = client.get(f'/api/v1/businesses/CP0000005/filings/changeOfAddress?eventId={ids[0]}')
    assert 404 == rv.status_code


@oracle_integration
def test_get_coa_no_results(client):
    """Assert that the business info for regular (not xpro) business is correct to spec."""
    rv = client.get('/api/v1/businesses/CP0000000/filings/changeOfAddress')

    assert 404 == rv.status_code


@oracle_integration
def test_post_coa_with_invalid_data(client):
    """Assert that the AR post validates correct data before proceeding."""
    headers = {'content-type': 'application/json'}

    fake_filing = {
        "filing": {
            "changeOfAddress": {
                "certifiedBy": "Joe Smith",
                "deliveryAddress": {
                    "addressCity": "WILLIAMS LAKE",
                    "addressCountry": "CANADA",
                    "addressRegion": "BC",
                    "postalCode": "V2G 1J6",
                    "streetAddress": "51 4TH AVENUE SOUTH",
                },
                "email": "nobody@nothing.com",
                "mailingAddress": {
                    "addressCity": "WILLIAMS LAKE",
                    "addressCountry": "CANADA",
                    "addressRegion": "BC",
                    "postalCode": "V2G 1J6",
                    "streetAddress": "51 4TH AVENUE SOUTH",
                }
            },
            "business_info": {
            },
            "header": {
                "date": "2017-11-23",
                "name": "changeOfAddress"
            }
        }
    }
    rv = client.post('/api/v1/businesses/CP0001965/filings/changeOfAddress',
                     data=json.dumps(fake_filing), headers=headers)

    assert 400 == rv.status_code
    assert 'Error: Invalid Filing schema' == rv.json['message']


@oracle_integration
def test_post_coa_with_mismatched_identifer(client):
    """Assert that the identifier (corp num) must match between URL and posted data."""
    headers = {'content-type': 'application/json'}

    fake_filing = FILING_HEADER
    fake_filing['filing']['header']['name'] = 'changeOfAddress'
    fake_filing['filing']['business']['identifier'] = 'CP0001965'
    fake_filing['filing']['changeOfAddress'] = CHANGE_OF_ADDRESS
    rv = client.post('/api/v1/businesses/CP0001966/filings/changeOfAddress',
                     data=json.dumps(fake_filing), headers=headers)

    assert 400 == rv.status_code
    assert 'Error: Identifier in URL does not match identifier in filing data' == rv.json['message']
