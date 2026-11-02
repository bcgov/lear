# Copyright © 2026 Province of British Columbia
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
"""Tests for the relationships -> parties normalization used by the validation entry point."""
import copy
from http import HTTPStatus

import pytest

from legal_api.services.filings.validations.party_shape import (
    normalize_party_shape,
    rewrite_party_error_paths,
    submitted_party_key,
    validate_relationship_items,
)
from registry_schemas.example_data import CONTINUATION_IN, CONTINUATION_IN_RELATIONSHIPS, FILING_HEADER

FILING_TYPE = 'continuationIn'
RELATIONSHIPS_PATH = f'/filing/{FILING_TYPE}/relationships'


def _filing(section: dict) -> dict:
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['name'] = FILING_TYPE
    filing['filing'][FILING_TYPE] = copy.deepcopy(section)
    return filing


def test_normalize_parties_untouched():
    """Assert a parties-shaped filing is returned as is."""
    filing = _filing(CONTINUATION_IN)

    normalized, err = normalize_party_shape(filing, FILING_TYPE)

    assert err is None
    assert normalized is filing
    assert submitted_party_key(filing, FILING_TYPE) == 'parties'


def test_normalize_no_party_shape_untouched():
    """Assert a filing without either party array (authorization stage) is returned as is."""
    section = copy.deepcopy(CONTINUATION_IN)
    del section['parties']
    filing = _filing(section)

    normalized, err = normalize_party_shape(filing, FILING_TYPE)

    assert err is None
    assert normalized is filing
    assert submitted_party_key(filing, FILING_TYPE) is None


def test_normalize_relationships_converted():
    """Assert relationships are converted into a parties copy without mutating the input."""
    filing = _filing(CONTINUATION_IN_RELATIONSHIPS)

    normalized, err = normalize_party_shape(filing, FILING_TYPE)

    assert err is None
    assert normalized is not filing
    assert 'parties' not in filing['filing'][FILING_TYPE]
    assert submitted_party_key(filing, FILING_TYPE) == 'relationships'

    parties = normalized['filing'][FILING_TYPE]['parties']
    assert [p['officer']['lastName'] for p in parties] == ['Swanson', 'Quagmire']
    assert parties[0]['officer']['firstName'] == 'Joe'
    assert parties[0]['officer']['partyType'] == 'person'
    assert parties[0]['officer']['email'] == 'joe@email.com'
    assert [r['roleType'] for r in parties[0]['roles']] == ['Completing Party', 'Director']
    assert parties[0]['roles'][0]['appointmentDate'] == '2018-01-01'
    assert parties[0]['deliveryAddress'] == filing['filing'][FILING_TYPE]['relationships'][0]['deliveryAddress']


def test_normalize_both_shapes_rejected():
    """Assert submitting parties and relationships together is a 400 at the relationships path."""
    section = copy.deepcopy(CONTINUATION_IN_RELATIONSHIPS)
    section['parties'] = copy.deepcopy(CONTINUATION_IN['parties'])
    filing = _filing(section)

    normalized, err = normalize_party_shape(filing, FILING_TYPE)

    assert normalized is filing
    assert err.code == HTTPStatus.BAD_REQUEST
    assert err.msg == [{
        'error': 'Provide either parties or relationships, not both.',
        'path': RELATIONSHIPS_PATH
    }]


def test_validate_relationship_items_valid():
    """Assert the example relationships pass the relationship-only checks."""
    assert validate_relationship_items(_filing(CONTINUATION_IN_RELATIONSHIPS), FILING_TYPE) == []


def test_validate_relationship_items_no_relationships():
    """Assert a filing without relationships has nothing to check."""
    assert validate_relationship_items(_filing(CONTINUATION_IN), FILING_TYPE) == []


@pytest.mark.parametrize('appointment_date', [None, ''])
def test_validate_relationship_items_appointment_date_required(appointment_date):
    """Assert every relationship role needs an appointmentDate."""
    section = copy.deepcopy(CONTINUATION_IN_RELATIONSHIPS)
    if appointment_date is None:
        del section['relationships'][1]['roles'][0]['appointmentDate']
    else:
        section['relationships'][1]['roles'][0]['appointmentDate'] = appointment_date

    errs = validate_relationship_items(_filing(section), FILING_TYPE)

    assert errs == [{
        'error': 'appointmentDate is required.',
        'path': f'{RELATIONSHIPS_PATH}/1/roles/0/appointmentDate'
    }]


def test_validate_relationship_items_person_with_business_name():
    """Assert the entity name consistency check reports at the relationships path."""
    section = copy.deepcopy(CONTINUATION_IN_RELATIONSHIPS)
    section['relationships'][0]['entity']['businessName'] = 'ACME Ltd.'

    errs = validate_relationship_items(_filing(section), FILING_TYPE)

    assert len(errs) == 1
    assert errs[0]['path'] == f'{RELATIONSHIPS_PATH}/0/entity/businessName'
    assert 'businessName should not be set' in errs[0]['error']


@pytest.mark.parametrize('length, valid', [(150, True), (151, False)])
def test_validate_relationship_items_business_name_length(length, valid):
    """Assert businessName is capped at the legacy organization name length."""
    section = copy.deepcopy(CONTINUATION_IN_RELATIONSHIPS)
    section['relationships'][1]['entity'] = {'businessName': 'X' * length}

    errs = validate_relationship_items(_filing(section), FILING_TYPE)

    if valid:
        assert errs == []
    else:
        assert errs == [{
            'error': 'businessName cannot be longer than 150 characters.',
            'path': f'{RELATIONSHIPS_PATH}/1/entity/businessName'
        }]


@pytest.mark.parametrize(
    'legacy_path, expected_path',
    [
        ('/filing/continuationIn/parties', RELATIONSHIPS_PATH),
        ('/filing/continuationIn/parties/roles', f'{RELATIONSHIPS_PATH}/roles'),
        ('/filing/continuationIn/parties/1', f'{RELATIONSHIPS_PATH}/1'),
        ('/filing/continuationIn/parties/1/officer/firstName', f'{RELATIONSHIPS_PATH}/1/entity/givenName'),
        ('/filing/continuationIn/parties/0/officer/lastName', f'{RELATIONSHIPS_PATH}/0/entity/familyName'),
        ('/filing/continuationIn/parties/0/officer/organizationName', f'{RELATIONSHIPS_PATH}/0/entity/businessName'),
        ('/filing/continuationIn/parties/0/officer/identifier', f'{RELATIONSHIPS_PATH}/0/entity/businessIdentifier'),
        ('/filing/continuationIn/parties/0/officer/middleName', f'{RELATIONSHIPS_PATH}/0/entity/additionalName'),
        ('/filing/continuationIn/parties/0/officer/middleInitial', f'{RELATIONSHIPS_PATH}/0/entity/middleInitial'),
        ('/filing/continuationIn/parties/0/officer/email', f'{RELATIONSHIPS_PATH}/0/entity/email'),
        ('/filing/continuationIn/parties/0/deliveryAddress/postalCode',
         f'{RELATIONSHIPS_PATH}/0/deliveryAddress/postalCode'),
        ('/filing/continuationIn/offices/registeredOffice', '/filing/continuationIn/offices/registeredOffice'),
        ('/filing/continuationIn/partiesOther', '/filing/continuationIn/partiesOther'),
        ('/filing/incorporationApplication/parties/0', '/filing/incorporationApplication/parties/0'),
    ]
)
def test_rewrite_party_error_paths(legacy_path, expected_path):
    """Assert legacy parties paths are rewritten to the relationships shape and others left alone."""
    msg = [{'error': 'x', 'path': legacy_path}]

    assert rewrite_party_error_paths(msg, FILING_TYPE) is msg
    assert msg[0]['path'] == expected_path


def test_rewrite_party_error_paths_without_path():
    """Assert errors without a path pass through."""
    msg = [{'error': 'x'}, {'error': 'y', 'path': None}]

    assert rewrite_party_error_paths(msg, FILING_TYPE) == [{'error': 'x'}, {'error': 'y', 'path': None}]
