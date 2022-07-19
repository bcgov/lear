# Copyright © 2020 Province of British Columbia
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

"""Tests to assure the name requests end-point.

Test-Suite to ensure that the /nameRequests endpoint is working as expected.
"""
from http import HTTPStatus

import copy
import datedelta
import pytz

from legal_api.services import namex
from legal_api.utils.legislation_datetime import LegislationDatetime

from tests import integration_namerequests


# Mock NR Data

expiration_date = '2099-12-31T07:59:00+00:00'
nr_consumable_approved = {
    'consentFlag': None,
    'expirationDate': expiration_date,
    'names': [
        {
            'choice': 1,
            'consumptionDate': None,
            'name': 'ABC 1234',
            'state': 'APPROVED'
        },
        {
            'choice': 2,
            'consumptionDate': None,
            'name': 'CDE 1234',
            'state': 'NE'
        }
    ],
    'nrNum': 'NR 1234567',
    'state': 'APPROVED'
}

nr_not_consumable_rejected = {
    'consentFlag': None,
    'expirationDate': expiration_date,
    'names': [
        {
            'choice': 1,
            'consumptionDate': None,
            'name': 'ABC 1234',
            'state': 'REJECTED'
        },
        {
            'choice': 2,
            'consumptionDate': None,
            'name': 'CDE 1234',
            'state': 'NE'
        }
    ],
    'nrNum': 'NR 1234567',
    'state': 'REJECTED'
}

nr_not_consumable_expired = {
    'consentFlag': None,
    'expirationDate': '2019-12-31T07:59:00+00:00',
    'names': [
        {
            'choice': 1,
            'consumptionDate': None,
            'name': 'ABC 1234',
            'state': 'REJECTED'
        },
        {
            'choice': 2,
            'consumptionDate': None,
            'name': 'CDE 1234',
            'state': 'NE'
        }
    ],
    'nrNum': 'NR 1234567',
    'state': 'EXPIRED'
}

nr_already_consumed = {
    'consentFlag': None,
    'expirationDate': expiration_date,
    'names': [
        {
            'choice': 1,
            'consumptionDate': 'Thu, 31 Dec 2019 23:59:59 GMT',
            'name': 'ABC 1234',
            'state': 'APPROVED'
        },
        {
            'choice': 2,
            'consumptionDate': None,
            'name': 'CDE 1234',
            'state': 'NE'
        }
    ],
    'nrNum': 'NR 1234567',
    'state': 'CONSUMED'
}

nr_consumable_conditional = {
    'consentFlag': 'R',
    'expirationDate': expiration_date,
    'names': [
        {
            'choice': 1,
            'consumptionDate': None,
            'name': 'ABC 1234',
            'state': 'NE'
        },
        {
            'choice': 2,
            'consumptionDate': None,
            'name': 'CDE 1234',
            'state': 'CONDITION'
        }
    ],
    'nrNum': 'NR 1234567',
    'state': 'CONDITIONAL'
}


@integration_namerequests
def test_name_requests_list_success(client):
    """Assert that a name request can be received."""
    identifiers = ['NR 3252362', 'NR 3252363', 'NR 3252364']
    qs = '&'.join([f'nrNumbers={nr}' for nr in identifiers])
    rv = client.get('/api/v2/nameRequests?'+qs)

    assert rv.status_code == HTTPStatus.OK
    assert rv.json
    assert len(rv.json) == 3


@integration_namerequests
def test_name_requests_success(client):
    """Assert that a name request can be received."""
    rv = client.get('/api/v2/nameRequests/NR 3252362')

    assert rv.status_code == HTTPStatus.OK
    assert 'nrNum' in rv.json
    assert rv.json['nrNum'] == 'NR 3252362'


@integration_namerequests
def test_name_requests_not_found(client):
    """Assert that name request is not found."""
    rv = client.get('/api/v2/nameRequests/NR 1234567')

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': 'NR 1234567 not found.'}


@integration_namerequests
def test_name_request_update_expiration(app, client):
    """Assert that nr expiration can be updated."""
    with app.app_context():
        nr_original = namex.query_nr_number('NR 2772704')

        effective_date = LegislationDatetime.tomorrow_midnight()
        # expecting a buffer in the date to make sure future effective filings have time to process
        effective_date = (effective_date + datedelta.datedelta(days=1)).astimezone(pytz.timezone('GMT'))
        expected_date_string = effective_date.strftime(namex.DATE_FORMAT)

        nr_response = namex.update_nr_as_future_effective(nr_original.json(), LegislationDatetime.tomorrow_midnight())
        json = nr_response.json()

        # check if expiration is extended
        assert json['expirationDate'] == expected_date_string

        # revert to original json
        nr_response = namex.update_nr(nr_original.json())
        assert nr_response.json()['expirationDate'] == nr_original.json()['expirationDate']


def test_validate_nr_consumable_approved():
    """Assert that nr mock data is consumable."""
    validation_result = namex.validate_nr(nr_consumable_approved)

    assert validation_result['is_consumable']
    assert validation_result['is_approved']
    assert not validation_result['is_expired']
    assert not validation_result['consent_required']
    assert not validation_result['consent_received']


def test_validate_nr_not_consumable_rejected():
    """Assert that nr mock data is not consumable as it has been rejected."""
    validation_result = namex.validate_nr(nr_not_consumable_rejected)

    assert not validation_result['is_consumable']
    assert not validation_result['is_approved']
    assert not validation_result['is_expired']
    assert not validation_result['consent_required']
    assert not validation_result['consent_received']


def test_validate_nr_not_consumable_expired():
    """Assert that nr mock data is not consumable as it has expired."""
    validation_result = namex.validate_nr(nr_not_consumable_expired)

    assert not validation_result['is_consumable']
    assert not validation_result['is_approved']
    assert validation_result['is_expired']
    assert not validation_result['consent_required']
    assert not validation_result['consent_received']


def test_validate_nr_already_consumed():
    """Assert that nr mock data has already been consumed."""
    validation_result = namex.validate_nr(nr_already_consumed)

    assert not validation_result['is_consumable']
    assert not validation_result['is_approved']
    assert not validation_result['is_expired']
    assert not validation_result['consent_required']
    assert not validation_result['consent_received']


def test_validate_nr_consent_required_not_received():
    """Assert that nr mock data is conditionally approved, but consent not received."""
    nr_consent_required = copy.deepcopy(nr_consumable_conditional)
    nr_consent_required['consentFlag'] = 'Y'
    validation_result = namex.validate_nr(nr_consent_required)
    assert not validation_result['is_consumable']
    assert validation_result['is_approved']
    assert not validation_result['is_expired']
    assert validation_result['consent_required']
    assert not validation_result['consent_received']


def test_validate_nr_consent_required_received():
    """Assert that nr mock data is conditionally approved and consent was received."""
    validation_result = namex.validate_nr(nr_consumable_conditional)
    assert validation_result['is_consumable']
    assert validation_result['is_approved']
    assert not validation_result['is_expired']
    assert validation_result['consent_required']
    assert validation_result['consent_received']

    # N = consent waived
    nr_consent_waived = copy.deepcopy(nr_consumable_conditional)
    nr_consent_waived['consentFlag'] = 'N'
    validation_result = namex.validate_nr(nr_consent_waived)
    assert validation_result['is_consumable']
    assert validation_result['is_approved']
    assert not validation_result['is_expired']
    assert not validation_result['consent_required']
    assert not validation_result['consent_received']

    # None = consent not required
    nr_consent_not_required = copy.deepcopy(nr_consumable_conditional)
    nr_consent_not_required['consentFlag'] = None
    validation_result = namex.validate_nr(nr_consent_not_required)
    assert validation_result['is_consumable']
    assert validation_result['is_approved']
    assert not validation_result['is_expired']
    assert not validation_result['consent_required']
    assert not validation_result['consent_received']

    nr_consent_not_required = copy.deepcopy(nr_consumable_conditional)
    nr_consent_not_required['consentFlag'] = ''
    validation_result = namex.validate_nr(nr_consent_not_required)
    assert validation_result['is_consumable']
    assert validation_result['is_approved']
    assert not validation_result['is_expired']
    assert not validation_result['consent_required']
    assert not validation_result['consent_received']


def test_get_approved_name():
    """Get Approved/Conditional Approved name."""
    nr_name = namex.get_approved_name(nr_consumable_approved)
    assert nr_name == nr_consumable_approved['names'][0]['name']
    nr_name = namex.get_approved_name(nr_consumable_conditional)
    assert nr_name == nr_consumable_conditional['names'][1]['name']
