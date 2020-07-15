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

import copy
import json

from registry_schemas import validate
from registry_schemas.example_data import CHANGE_OF_DIRECTORS, FILING_HEADER

from tests import oracle_integration
from tests.unit.api.test_ar import cod_ids as cod_ids


ids = cod_ids


@oracle_integration
def test_get_current(client):
    """Assert that the business info for regular (not xpro) business is correct to spec."""
    rv = client.get('/api/v1/businesses/CP/CP0001965/parties')

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

    fake_filing = FILING_HEADER
    fake_filing['filing']['header']['learEffectiveDate'] = \
        f'{fake_filing["filing"]["header"]["date"]}T15:22:39.868757+00:00'
    fake_filing['filing']['header']['name'] = 'changeOfDirectors'
    fake_filing['filing']['business']['identifier'] = 'CP0001965'
    fake_filing['filing']['changeOfDirectors'] = CHANGE_OF_DIRECTORS
    # set actions to nothing because it contains directors that don't exist for this coop
    for director in fake_filing['filing']['changeOfDirectors']['directors']:
        director['actions'] = []

    # add director action for director that exists for CP0001965
    fake_filing['filing']['changeOfDirectors']['directors'].append(
        {
            'actions': ['addressChanged'],
            'appointmentDate': '2009-09-21',
            'cessationDate': None,
            'deliveryAddress': {
                'actions': [],
                'addressCity': 'TEST CHANGE 2',
                'addressCountry': 'CANADA',
                'addressId': 102554860,
                'addressRegion': 'BC',
                'deliveryInstructions': '',
                'postalCode': '',
                'streetAddress': '1038 DAIRY RD',
                'streetAddressAdditional': ''
            },
            'mailingAddress': {
                'actions': [],
                'addressCity': 'WILLIAMS LAKE',
                'addressCountry': 'CANADA',
                'addressId': 102554860,
                'addressRegion': 'BC',
                'deliveryInstructions': '',
                'postalCode': '',
                'streetAddress': '1038 DAIRY RD',
                'streetAddressAdditional': ''
            },
            'officer': {
                'firstName': 'NANCY',
                'lastName': 'GALE',
                'middleInitial': ''
            },
            'title': ''
        }
    )

    rv = client.post('/api/v1/businesses/CP/CP0001965/filings/changeOfDirectors',
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
def test_post_invalid_cod_fail(client):
    """Assert that business for regular (not xpro) business is correct to spec."""
    headers = {'content-type': 'application/json'}

    fake_filing = FILING_HEADER
    fake_filing['filing']['header']['name'] = 'changeOfDirectors'
    fake_filing['filing']['business']['identifier'] = 'CP0001965'
    fake_filing['filing']['changeOfDirectors'] = {}

    rv = client.post('/api/v1/businesses/CP/CP0001965/filings/changeOfDirectors',
                     data=json.dumps(fake_filing), headers=headers)

    assert 201 != rv.status_code


@oracle_integration
def test_get_cod(client):
    """Assert that the business info for regular (not xpro) business is correct to spec."""
    rv = client.get('/api/v1/businesses/CP/CP0001965/filings/changeOfDirectors')

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
        rv = client.get(f'/api/v1/businesses/CP/CP0001965/filings/changeOfDirectors?eventId={event_id}')

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
    rv = client.get(f'/api/v1/businesses/CP/CP0000005/filings/changeOfDirectors?eventId={ids[0]}')
    assert 404 == rv.status_code


@oracle_integration
def test_get_cod_no_results(client):
    """Assert that the business info for regular (not xpro) business is correct to spec."""
    rv = client.get('/api/v1/businesses/CP/CP0000000/filings/changeOfDirectors')

    assert 404 == rv.status_code


@oracle_integration
def test_special_characters(client):
    """Assert unicode characters are inserted correctly."""
    headers = {'content-type': 'application/json'}

    # Create a director entry with special characters in the name
    new_director = {
            'actions': ['appointed'],
            'appointmentDate': '2009-09-21',
            'cessationDate': None,
            'deliveryAddress': {
                'actions': [],
                'addressCity': 'TEST CHANGE 2',
                'addressCountry': 'CANADA',
                'addressId': 102554860,
                'addressRegion': 'BC',
                'deliveryInstructions': '',
                'postalCode': '',
                'streetAddress': '1038 DAIRY RD',
                'streetAddressAdditional': ''
            },
            'mailingAddress': {
                'actions': [],
                'addressCity': 'WILLIAMS LAKE',
                'addressCountry': 'CANADA',
                'addressId': 102554860,
                'addressRegion': 'BC',
                'deliveryInstructions': '',
                'postalCode': '',
                'streetAddress': '1038 DAIRY RD',
                'streetAddressAdditional': ''
            },
            'officer': {
                'firstName': 'Tést',
                'lastName': 'Nãme',
                'middleInitial': ''
            },
            'title': ''
        }

    fake_filing = copy.deepcopy(FILING_HEADER)
    fake_filing['filing']['header']['name'] = 'changeOfDirectors'
    # Use special characters in the certified by field
    fake_filing['filing']['header']['certifiedBy'] = 'Cërtifîer'
    fake_filing['filing']['business']['identifier'] = 'CP0001965'

    fake_filing['filing']['changeOfDirectors']['directors'] = [new_director]

    rv = client.post('/api/v1/businesses/CP/CP0001965/filings/changeOfDirectors',
                     data=json.dumps(fake_filing), headers=headers)

    assert rv.json
    assert 201 == rv.status_code

    event_id = rv.json['filing']['header']['colinIds'][0]
    dirs = rv.json['filing']['changeOfDirectors']['directors']
    new_director = list(filter(lambda x: x['startEventId'] == (event_id), dirs))

    assert new_director
    assert rv.json['filing']['header']['certifiedBy'] == 'Cërtifîer'
    assert new_director[0]['officer']['firstName'] == 'Tést'
    assert new_director[0]['officer']['lastName'] == 'Nãme'
