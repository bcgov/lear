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

"""Tests to assure the change of directors filing end-point."""

import json

from registry_schemas import validate

from tests import oracle_integration
from tests.unit.api.test_ar import cod_ids as cod_ids


ids = cod_ids


@oracle_integration
def test_get_current(client):
    """Assert that the business info for regular (not xpro) business is correct to spec."""
    rv = client.get('/api/v1/businesses/CP0001965/directors')

    assert 200 == rv.status_code
    is_valid, errors = validate(rv.json, 'directors', validate_schema=True)
    if errors:
        for err in errors:
            print('\nERROR MESSAGE:')
            print(err.message)

    assert is_valid


@oracle_integration
def test_post_cod(client):
    """Assert that business for regular (not xpro) business is correct to spec."""
    headers = {'content-type': 'application/json'}

    fake_filing = {
        "filing": {
            "changeOfDirectors": {
                "certifiedBy": "Joe Smith",
                "email": "nobody@nothing.com",
                "directors": [
                    {
                        "actions": ["ceased"],
                        "appointmentDate": "2012-05-08",
                        "cessationDate": "2019-05-14",
                        "deliveryAddress": {
                            "addressCity": "BURNS LAKE",
                            "addressCountry": "CANADA",
                            "addressId": 102604824,
                            "addressRegion": "BC",
                            "deliveryInstructions": "",
                            "postalCode": "",
                            "streetAddress": "1723 SIDAR ROAD",
                            "streetAddressAdditional": ""
                        },
                        "officer": {
                            "firstName": "LORNA",
                            "lastName": "HANNETT",
                            "middleInitial": ""
                        },
                        "title": ""
                    },
                    {
                        "actions": [],
                        "appointmentDate": "2015-10-14",
                        "cessationDate": None,
                        "deliveryAddress": {
                            "addressCity": "BURNS LAKE",
                            "addressCountry": "CANADA",
                            "addressRegion": "BC",
                            "deliveryInstructions": "",
                            "postalCode": "",
                            "streetAddress": "173 8TH AVE",
                            "streetAddressAdditional": ""
                        },
                        "officer": {
                            "firstName": "PAULA",
                            "lastName": "LAURIE",
                            "middleInitial": ""
                        },
                        "title": ""
                    },
                    {
                        "actions": [],
                        "appointmentDate": "2017-12-21",
                        "cessationDate": None,
                        "deliveryAddress": {
                            "addressCity": "BURNS LAKE",
                            "addressCountry": "CANADA",
                            "addressRegion": "BC",
                            "deliveryInstructions": "",
                            "postalCode": "",
                            "streetAddress": "10816 TINTAGEL ROAD",
                            "streetAddressAdditional": ""
                        },
                        "officer": {
                            "firstName": "KELLY",
                            "lastName": "TURFORD",
                            "middleInitial": ""
                        },
                        "title": ""
                    },
                    {
                        "actions": [],
                        "appointmentDate": "2019-07-15",
                        "cessationDate": None,
                        "deliveryAddress": {
                            "addressCity": "TEST CITY",
                            "addressCountry": "CANADA",
                            "addressRegion": "BC",
                            "deliveryInstructions": "",
                            "postalCode": "",
                            "streetAddress": "TESTING TESTS STREET",
                            "streetAddressAdditional": ""
                        },
                        "officer": {
                            "firstName": "TESTER",
                            "lastName": "TESTING",
                            "middleInitial": ""
                        },
                        "title": ""
                    }
                ]
            },
            "business": {
                "cacheId": 0,
                "lastLedgerTimestamp": "2019-05-08T21:21:01-00:00",
                "foundingDate": "2004-04-28",
                "identifier": "CP0001965",
                "legalName": "CENTRAL INTERIOR COMMUNITY SERVICES CO-OP",
                "businessNumber": None,
                "jurisdiction": "BC",
                "lastAgmDate": "2019-02-02",
                "lastArFiledDate": "2019-04-21",
                "status": "Active",
                "type": "CP"
            },
            "header": {
                "date": "2019-05-21",
                "name": "changeOfDirectors"
            }
        }
    }
    rv = client.post('/api/v1/businesses/CP0001965/filings/changeOfDirectors',
                     data=json.dumps(fake_filing), headers=headers)

    assert 201 == rv.status_code
    is_valid, errors = validate(rv.json, 'filing', validate_schema=True)
    if errors:
        for err in errors:
            print('\nERROR MESSAGE:')
            print(err.message)

    assert is_valid
    assert "changeOfDirectors" == rv.json['filing']['header']['name']
    ids.append(str(rv.json['filing']['changeOfDirectors']['eventId']))
    assert str(rv.json['filing']['changeOfDirectors']['eventId']) in ids


@oracle_integration
def test_get_cod(client):
    """Assert that the business info for regular (not xpro) business is correct to spec."""
    rv = client.get('/api/v1/businesses/CP0001965/filings/changeOfDirectors')

    assert 200 == rv.status_code
    is_valid, errors = validate(rv.json, 'filing', validate_schema=True)
    if errors:
        for err in errors:
            print('\nERROR MESSAGE:')
            print(err.message)

    assert is_valid
    assert "changeOfDirectors" == rv.json['filing']['header']['name']
    assert str(rv.json['filing']['changeOfDirectors']['eventId']) in ids


@oracle_integration
def test_get_cod_by_id(client):
    """Assert that the business info for regular (not xpro) business is correct to spec."""
    for event_id in ids:
        rv = client.get(f'/api/v1/businesses/CP0001965/filings/changeOfDirectors?eventId={event_id}')

        assert 200 == rv.status_code
        is_valid, errors = validate(rv.json, 'filing', validate_schema=True)
        if errors:
            for err in errors:
                print('\nERROR MESSAGE:')
                print(err.message)

        assert is_valid
        assert "changeOfDirectors" == rv.json['filing']['header']['name']
        assert f'{event_id}' == str(rv.json['filing']['changeOfDirectors']['eventId'])


@oracle_integration
def test_get_cod_by_id_wrong_corp(client):
    """Assert that a coop searching for a cod filing associated with a different coop returns a 404."""
    rv = client.get(f'/api/v1/businesses/CP0000005/filings/changeOfDirectors?eventId={ids[0]}')
    assert 404 == rv.status_code


@oracle_integration
def test_get_cod_no_results(client):
    """Assert that the business info for regular (not xpro) business is correct to spec."""
    rv = client.get('/api/v1/businesses/CP0000000/filings/changeOfDirectors')

    assert 404 == rv.status_code
