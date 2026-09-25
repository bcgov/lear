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
"""Test Change of Director validations for the relationships shape."""
import copy
import random
from http import HTTPStatus

import datedelta
import pytest

from business_common.utils import LegislationDatetime, datetime
from business_model.models import Address, Business, PartyRole
from legal_api.services.filings import validate
from registry_schemas.example_data import CHANGE_OF_DIRECTORS, CHANGE_OF_DIRECTORS_RELATIONSHIPS, FILING_HEADER
from tests.unit.models import factory_business, factory_party_role
from tests.unit.services.filings.validations import lists_are_equal

VALID_ADDRESS = {
    'streetAddress': '123 A St',
    'addressCity': 'Vancouver',
    'addressRegion': 'BC',
    'addressCountry': 'CA',
    'postalCode': 'V5K0A1'
}


def _setup_business(identifier: str) -> Business:
    """Create a BC company founded well in the past."""
    founding_date = datetime.utcnow() - datedelta.datedelta(years=10)
    business = factory_business(identifier, founding_date, None, Business.LegalTypes.COMP.value)
    business.last_cod_date = founding_date
    business.save()
    return business


def _setup_existing_director(business: Business) -> int:
    """Create an active director for the business and return the party id."""
    officer = {
        'firstName': 'Joe',
        'lastName': 'Swanson',
        'middleInitial': 'P',
        'partyType': 'person',
        'organizationName': ''
    }
    role = factory_party_role(
        Address.create_address(VALID_ADDRESS),
        Address.create_address(VALID_ADDRESS),
        officer,
        (datetime.utcnow() - datedelta.datedelta(years=5)).date().isoformat(),
        None,
        PartyRole.RoleTypes.DIRECTOR)
    business.party_roles.append(role)
    business.save()
    return role.party_id


def _build_filing(identifier: str, cod: dict) -> dict:
    """Build a changeOfDirectors filing envelope with a valid effective date."""
    now = datetime.utcnow()
    effective_date = LegislationDatetime.as_legislation_timezone(now)
    effective_date = effective_date.replace(hour=0, minute=0, second=0, microsecond=0)
    effective_date = LegislationDatetime.as_utc_timezone(effective_date)

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['date'] = now.date().isoformat()
    filing['filing']['header']['effectiveDate'] = effective_date.isoformat()
    filing['filing']['header']['name'] = 'changeOfDirectors'
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['changeOfDirectors'] = cod
    return filing


def _relationships_cod(party_id: int = None) -> dict:
    """Return the example relationships COD with the existing party id applied."""
    cod = copy.deepcopy(CHANGE_OF_DIRECTORS_RELATIONSHIPS)
    if party_id is not None:
        for relationship in cod['relationships']:
            if relationship['entity'].get('identifier'):
                relationship['entity']['identifier'] = str(party_id)
    return cod


def test_validate_cod_relationships_success(session):
    """Assert a valid relationships COD (added, removed and edited directors) passes."""
    identifier = f'BC{random.randint(1000000, 9999999)}'
    business = _setup_business(identifier)
    party_id = _setup_existing_director(business)

    filing = _build_filing(identifier, _relationships_cod(party_id))

    err = validate(business, filing)
    if err:
        print(err.msg)

    assert err is None


def test_validate_cod_relationships_no_actions_success(session):
    """Assert relationships without actions validate via derivation."""
    identifier = f'BC{random.randint(1000000, 9999999)}'
    business = _setup_business(identifier)
    party_id = _setup_existing_director(business)

    cod = _relationships_cod(party_id)
    for relationship in cod['relationships']:
        del relationship['actions']
    filing = _build_filing(identifier, cod)

    err = validate(business, filing)
    if err:
        print(err.msg)

    assert err is None


def test_validate_cod_relationships_changed_action_success(session):
    """Assert a CHANGED action on an existing director validates as an edit."""
    identifier = f'BC{random.randint(1000000, 9999999)}'
    business = _setup_business(identifier)
    party_id = _setup_existing_director(business)

    cod = _relationships_cod(party_id)
    cod['relationships'][2]['actions'] = ['CHANGED']
    filing = _build_filing(identifier, cod)

    err = validate(business, filing)
    if err:
        print(err.msg)

    assert err is None


def test_validate_cod_both_shapes_rejected(session):
    """Assert a filing carrying both directors and relationships is rejected."""
    identifier = f'BC{random.randint(1000000, 9999999)}'
    business = _setup_business(identifier)
    party_id = _setup_existing_director(business)

    cod = _relationships_cod(party_id)
    cod['directors'] = copy.deepcopy(CHANGE_OF_DIRECTORS['directors'])
    filing = _build_filing(identifier, cod)

    err = validate(business, filing)

    assert err is not None
    assert err.code == HTTPStatus.BAD_REQUEST
    assert lists_are_equal(err.msg, [{
        'error': 'Only one of directors or relationships can be provided.',
        'path': '/filing/changeOfDirectors'
    }])


@pytest.mark.parametrize(
    'test_name, item_idx, actions, expected_msg',
    [
        (
            'ADDED with identifier',
            2, ['ADDED'],
            [{'error': 'An added director cannot reference an existing director.',
              'path': '/filing/changeOfDirectors/relationships/2/actions'}]
        ),
        (
            'ADDED combined with edit action',
            2, ['ADDED', 'NAME_CHANGED'],
            [{'error': 'ADDED cannot be combined with other director actions.',
              'path': '/filing/changeOfDirectors/relationships/2/actions'}]
        ),
        (
            'edit action without identifier',
            0, ['NAME_CHANGED'],
            [{'error': 'An entity identifier is required to change or cease a director.',
              'path': '/filing/changeOfDirectors/relationships/0/actions'}]
        ),
        (
            'CHANGED without identifier',
            0, ['CHANGED'],
            [{'error': 'An entity identifier is required to change or cease a director.',
              'path': '/filing/changeOfDirectors/relationships/0/actions'}]
        ),
    ]
)
def test_validate_cod_relationship_actions(session, test_name, item_idx, actions, expected_msg):
    """Assert inconsistent explicit actions are rejected."""
    identifier = f'BC{random.randint(1000000, 9999999)}'
    business = _setup_business(identifier)
    party_id = _setup_existing_director(business)

    cod = _relationships_cod(party_id)
    cod['relationships'][item_idx]['actions'] = actions
    filing = _build_filing(identifier, cod)

    err = validate(business, filing)

    assert err is not None
    assert err.code == HTTPStatus.BAD_REQUEST
    assert lists_are_equal(err.msg, expected_msg)


def test_validate_cod_relationships_unknown_identifier(session):
    """Assert an identifier that is not an active director is rejected."""
    identifier = f'BC{random.randint(1000000, 9999999)}'
    business = _setup_business(identifier)
    party_id = _setup_existing_director(business)

    cod = _relationships_cod(party_id)
    cod['relationships'][2]['entity']['identifier'] = str(party_id + 999)
    filing = _build_filing(identifier, cod)

    err = validate(business, filing)

    assert err is not None
    assert err.code == HTTPStatus.BAD_REQUEST
    assert any(e['error'] == 'Relationship with this identifier is not valid for this filing.'
               and e['path'] == '/filing/changeOfDirectors/relationships/2/entity/identifier'
               for e in err.msg)


@pytest.mark.parametrize(
    'test_name, removed_cessation_date, edited_cessation_date, expected_msg',
    [
        (
            'REMOVED without cessation date',
            None, None,
            [{'error': 'Cessation date is required for ceased directors.',
              'path': '/filing/changeOfDirectors/relationships/1/roles/0/cessationDate'}]
        ),
        (
            'cessation date on a non-ceased director',
            '2023-01-01', '2023-01-01',
            [{'error': 'Cessation date must only be provided for a ceased director.',
              'path': '/filing/changeOfDirectors/relationships/2/roles/0/cessationDate'}]
        ),
        (
            # the future check comes from validate_relationships
            'future cessation date',
            '2999-01-01', None,
            [{'error': 'Cessation date cannot be in the future.',
              'path': '/filing/changeOfDirectors/relationships/1/roles/0/cessationDate'}]
        ),
    ]
)
def test_validate_cod_relationship_cessation_dates(session, test_name, removed_cessation_date,
                                                   edited_cessation_date, expected_msg):
    """Assert cessation date rules apply to the Director role dates."""
    identifier = f'BC{random.randint(1000000, 9999999)}'
    business = _setup_business(identifier)
    party_id = _setup_existing_director(business)

    cod = _relationships_cod(party_id)
    cod['relationships'][1]['roles'][0]['cessationDate'] = removed_cessation_date
    cod['relationships'][2]['roles'][0]['cessationDate'] = edited_cessation_date
    filing = _build_filing(identifier, cod)

    err = validate(business, filing)
    if err:
        print(err.msg)

    assert err is not None
    assert err.code == HTTPStatus.BAD_REQUEST
    assert lists_are_equal(err.msg, expected_msg)


def test_validate_cod_relationship_cessation_before_last_cod(session):
    """Assert a cessation date before the last COD date is rejected."""
    identifier = f'BC{random.randint(1000000, 9999999)}'
    business = _setup_business(identifier)
    business.last_cod_date = datetime.utcnow() - datedelta.datedelta(days=1)
    business.save()
    party_id = _setup_existing_director(business)

    cod = _relationships_cod(party_id)
    filing = _build_filing(identifier, cod)

    err = validate(business, filing)

    assert err is not None
    assert err.code == HTTPStatus.BAD_REQUEST
    assert any(e['error'] == 'Cessation date cannot be before the business founding date '
                             'or the most recent Change of Directors filing.'
               and e['path'] == '/filing/changeOfDirectors/relationships/1/roles/0/cessationDate'
               for e in err.msg)


def test_validate_cod_relationship_appointment_before_last_cod(session):
    """Assert an appointment date before the last COD date is rejected."""
    identifier = f'BC{random.randint(1000000, 9999999)}'
    business = _setup_business(identifier)
    business.last_cod_date = datetime.utcnow() - datedelta.datedelta(days=1)
    business.save()
    party_id = _setup_existing_director(business)

    cod = _relationships_cod(party_id)
    # keep only the ADDED director so the stale cessation date does not also error
    cod['relationships'] = [cod['relationships'][0]]
    filing = _build_filing(identifier, cod)

    err = validate(business, filing)

    assert err is not None
    assert err.code == HTTPStatus.BAD_REQUEST
    assert lists_are_equal(err.msg, [{
        'error': 'Appointment date cannot be before the business founding date '
                 'or the most recent Change of Directors filing.',
        'path': '/filing/changeOfDirectors/relationships/0/roles/0/appointmentDate'
    }])


def test_validate_cod_relationship_invalid_country(session):
    """Assert a non ISO-2 resolvable country is rejected."""
    identifier = f'BC{random.randint(1000000, 9999999)}'
    business = _setup_business(identifier)
    party_id = _setup_existing_director(business)

    cod = _relationships_cod(party_id)
    cod['relationships'][0]['deliveryAddress']['addressCountry'] = 'nonsense'
    filing = _build_filing(identifier, cod)

    err = validate(business, filing)

    assert err is not None
    assert err.code == HTTPStatus.BAD_REQUEST
    assert any(e['error'] == 'Address Country must resolve to a valid ISO-2 country.'
               and e['path'] == '/filing/changeOfDirectors/relationships/0/deliveryAddress/addressCountry'
               for e in err.msg)


def test_validate_cod_relationship_given_name_too_long(session):
    """Assert the COLIN sync given name length limit applies for corps."""
    identifier = f'BC{random.randint(1000000, 9999999)}'
    business = _setup_business(identifier)
    party_id = _setup_existing_director(business)

    cod = _relationships_cod(party_id)
    cod['relationships'][0]['entity']['givenName'] = 'G' * 21
    filing = _build_filing(identifier, cod)

    err = validate(business, filing)

    assert err is not None
    assert err.code == HTTPStatus.BAD_REQUEST
    assert any('given name cannot be longer than 20 characters' in e['error']
               and e['path'] == '/filing/changeOfDirectors/relationships/0/entity/givenName'
               for e in err.msg)
