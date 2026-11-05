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
"""Tests for Review Imported Data filing validation."""
import copy
import random
from http import HTTPStatus

import datedelta
import pytest

from business_common.utils import datetime
from business_model.models import Address, Business, Office, PartyRole
from legal_api.services.filings.validations.validation import validate
from registry_schemas.example_data import FILING_HEADER
from tests.unit.models import factory_business, factory_party_role


VALID_ADDRESS = {
    'streetAddress': '123 A St',
    'addressCity': 'Vancouver',
    'addressRegion': 'BC',
    'addressCountry': 'CA',
    'postalCode': 'V5K0A1',
}


def _build_filing(review_imported_data):
    """Build a Review Imported Data filing envelope."""
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['reviewImportedData'] = review_imported_data
    filing['filing']['header']['name'] = 'reviewImportedData'
    return filing


def _valid_office():
    """Return a valid office with delivery and mailing addresses."""
    return {
        'deliveryAddress': VALID_ADDRESS.copy(),
        'mailingAddress': VALID_ADDRESS.copy(),
    }


def _valid_relationship(identifier):
    """Return a valid director relationship using the supplied party ID."""
    return {
        'entity': {
            'identifier': str(identifier),
            'givenName': '',
            'familyName': '',
        },
        'deliveryAddress': VALID_ADDRESS.copy(),
        'mailingAddress': VALID_ADDRESS.copy(),
        'roles': [
            {'roleType': 'Director'},
        ],
    }


def _setup_business():
    """Create a BC company founded well in the past."""
    identifier = f'BC{random.randint(1000000, 9999999)}'
    founding_date = datetime.utcnow() - datedelta.datedelta(years=10)

    business = factory_business(
        identifier,
        founding_date,
        None,
        Business.LegalTypes.COMP.value,
    )
    business.last_cod_date = founding_date
    business.save()
    return business


def _setup_active_director(business):
    """Create an active director and attach the role to the business."""
    officer = {
        'firstName': 'Joe',
        'lastName': 'Swanson',
        'middleInitial': 'P',
        'partyType': 'person',
        'organizationName': '',
    }
    role = factory_party_role(
        Address.create_address(VALID_ADDRESS),
        Address.create_address(VALID_ADDRESS),
        officer,
        (datetime.utcnow() - datedelta.datedelta(years=5)).date().isoformat(),
        None,
        PartyRole.RoleTypes.DIRECTOR,
    )
    business.party_roles.append(role)
    business.save()
    return role.party_id


def _setup_office(business, office_type, mailing: dict, delivery: dict):
    """Attach an office whose addresses may have fields missing (imported data)."""
    office = Office(office_type=office_type)
    office.addresses.append(Address(**mailing, address_type=Address.MAILING))
    office.addresses.append(Address(**delivery, address_type=Address.DELIVERY))
    business.offices.append(office)
    business.save()


def _setup_director_missing_postal_code(business):
    """Create an active director whose mailing address has no postal code."""
    mailing = Address.create_address({**VALID_ADDRESS, 'postalCode': ''})
    officer = {
        'firstName': 'Joe',
        'lastName': 'Swanson',
        'middleInitial': 'P',
        'partyType': 'person',
        'organizationName': '',
    }
    role = factory_party_role(
        Address.create_address(VALID_ADDRESS),
        mailing,
        officer,
        (datetime.utcnow() - datedelta.datedelta(years=5)).date().isoformat(),
        None,
        PartyRole.RoleTypes.DIRECTOR,
    )
    business.party_roles.append(role)
    business.save()
    return role.party_id


STORED_ADDRESS = {
    'street': '123 A St',
    'city': 'Vancouver',
    'region': 'BC',
    'country': 'CA',
    'postal_code': 'V5K0A1',
}


def test_validate_offices_only(session):
    """Assert a filing containing offices only passes validation."""
    business = _setup_business()
    filing = _build_filing({
        'offices': {
            'registeredOffice': _valid_office(),
        },
    })

    err = validate(business, filing)

    assert err is None


def test_validate_rejects_review_imported_data_when_feature_is_disabled(session, monkeypatch):
    """Reject the filing when reviewImportedData is absent from the feature flag."""
    business = _setup_business()
    filing = _build_filing({
        "offices": {
            "registeredOffice": _valid_office(),
        },
    })
    monkeypatch.setattr("legal_api.services.flags.value", lambda *args, **kwargs: [])

    err = validate(business, filing)

    assert err is not None
    assert err.code == HTTPStatus.FORBIDDEN
    assert err.msg == [{"error": "Review Imported Data filing is not enabled."}]


def test_validate_relationships_only(session):
    """Assert a filing containing relationships only passes validation."""
    business = _setup_business()
    party_id = _setup_active_director(business)
    filing = _build_filing({
        'relationships': [
            _valid_relationship(party_id),
        ],
    })

    err = validate(business, filing)

    assert err is None


def test_validate_offices_and_relationships(session):
    """Assert a filing containing offices and relationships passes validation."""
    business = _setup_business()
    party_id = _setup_active_director(business)
    filing = _build_filing({
        'offices': {
            'registeredOffice': _valid_office(),
            'recordsOffice': _valid_office(),
        },
        'relationships': [
            _valid_relationship(party_id),
        ],
    })

    err = validate(business, filing)

    assert err is None


@pytest.mark.parametrize(
    "office_type,address_type",
    [
        ("registeredOffice", "deliveryAddress"),
        ("registeredOffice", "mailingAddress"),
        ("recordsOffice", "deliveryAddress"),
        ("recordsOffice", "mailingAddress"),
    ],
)
def test_validate_requires_bc_region_for_office_addresses(session, office_type, address_type):
    """Require BC region for delivery addresses, but allow other regions for mailing addresses."""
    business = _setup_business()
    office = _valid_office()
    office[address_type]["addressRegion"] = "AB"
    filing = _build_filing({"offices": {office_type: office}})

    err = validate(business, filing)

    if address_type == "mailingAddress":
        assert err is None
    else:
        expected_path = f"/filing/reviewImportedData/offices/{office_type}"
        assert err is not None
        assert err.code == HTTPStatus.BAD_REQUEST
        assert any(
            item["error"] == "Address Region must be 'BC'." and item["path"] == expected_path
            for item in err.msg
        )


def test_validate_rejects_unknown_director_identifier(session):
    """Assert a relationship identifier that is not an active director is rejected."""
    business = _setup_business()
    party_id = _setup_active_director(business)
    filing = _build_filing({
        'relationships': [
            _valid_relationship(party_id + 999),
        ],
    })

    err = validate(business, filing)

    assert err is not None
    assert err.code == HTTPStatus.BAD_REQUEST
    assert any(
        e['error'] == 'Relationship with this identifier is not valid for this filing.'
        and e['path'] == '/filing/reviewImportedData/relationships/0/entity/identifier'
        for e in err.msg
    )


def test_validate_accepts_active_director_identifier(session):
    """Assert a relationship identifier matching an active director is accepted."""
    business = _setup_business()
    party_id = _setup_active_director(business)
    filing = _build_filing({
        'relationships': [
            _valid_relationship(party_id),
        ],
    })

    err = validate(business, filing)

    assert err is None


@pytest.mark.parametrize(
    'address_field, address_value, expected_message, expected_path',
    [
        (
            'postalCode',
            'INVALID',
            "Postal code must follow Canadian format, e.g. 'A1A 1A1' or 'A1A1A1'.",
            '/filing/reviewImportedData/relationships/0/deliveryAddress/postalCode',
        ),
        (
            'addressCountry',
            'nonsense',
            'Address Country must resolve to a valid ISO-2 country.',
            '/filing/reviewImportedData/relationships/0/deliveryAddress/addressCountry',
        ),
    ],
    ids=['invalid-postal-code', 'invalid-country'],
)
def test_validate_rejects_invalid_relationship_address(
    session, address_field, address_value, expected_message, expected_path
):
    """Assert invalid relationship address fields are rejected."""
    business = _setup_business()
    party_id = _setup_active_director(business)
    relationship = _valid_relationship(party_id)
    relationship['deliveryAddress'][address_field] = address_value
    filing = _build_filing({
        'relationships': [relationship],
    })

    err = validate(business, filing)

    assert err is not None
    assert err.code == HTTPStatus.BAD_REQUEST
    assert any(
        e['error'] == expected_message and e['path'] == expected_path
        for e in err.msg
    )


def test_validate_office_allows_only_flagged_fields(session):
    """Only the office address field flagged as missing may change; the rest must match the record."""
    business = _setup_business()
    _setup_office(business, 'registeredOffice', {**STORED_ADDRESS, 'postal_code': ''}, STORED_ADDRESS)
    office = _valid_office()
    office['mailingAddress']['addressCity'] = 'Victoria'
    filing = _build_filing({'offices': {'registeredOffice': office}})

    err = validate(business, filing)

    assert err is not None
    assert err.msg == [{
        'error': 'Only fields flagged as missing or invalid can be changed.',
        'path': '/filing/reviewImportedData/offices/registeredOffice/mailingAddress/addressCity',
    }]

    office['mailingAddress']['addressCity'] = 'Vancouver'
    assert validate(business, _build_filing({'offices': {'registeredOffice': office}})) is None


def test_validate_office_missing_address_is_fully_editable(session):
    """An office address with no record at all can be entered from scratch."""
    business = _setup_business()
    office = Office(office_type='recordsOffice')
    office.addresses.append(Address(**STORED_ADDRESS, address_type=Address.MAILING))
    business.offices.append(office)
    business.save()
    submitted = _valid_office()
    submitted['deliveryAddress']['streetAddress'] = '999 New St'

    assert validate(business, _build_filing({'offices': {'recordsOffice': submitted}})) is None


def test_validate_director_allows_only_flagged_fields(session):
    """Only the director address field flagged as missing may change; the rest must match the record."""
    business = _setup_business()
    party_id = _setup_director_missing_postal_code(business)
    relationship = _valid_relationship(party_id)
    relationship['mailingAddress']['streetAddress'] = '456 B St'
    filing = _build_filing({'relationships': [relationship]})

    err = validate(business, filing)

    assert err is not None
    assert err.msg == [{
        'error': 'Only fields flagged as missing or invalid can be changed.',
        'path': '/filing/reviewImportedData/relationships/0/mailingAddress/streetAddress',
    }]

    relationship['mailingAddress']['streetAddress'] = '123 A St'
    assert validate(business, _build_filing({'relationships': [relationship]})) is None


def test_validate_ignores_postal_code_formatting(session):
    """The UI reformats an untouched postal code, which must not count as a change."""
    business = _setup_business()
    _setup_office(business, 'registeredOffice', {**STORED_ADDRESS, 'postal_code': 'v5k 0a1', 'city': ''}, STORED_ADDRESS)
    office = _valid_office()
    office['mailingAddress']['postalCode'] = 'V5K0A1'

    assert validate(business, _build_filing({'offices': {'registeredOffice': office}})) is None

    office['mailingAddress']['postalCode'] = 'V5K 0A2'
    err = validate(business, _build_filing({'offices': {'registeredOffice': office}}))
    assert err is not None
    assert err.msg == [{
        'error': 'Only fields flagged as missing or invalid can be changed.',
        'path': '/filing/reviewImportedData/offices/registeredOffice/mailingAddress/postalCode',
    }]


def test_validate_flagged_country_unlocks_region_and_postal_code(session):
    """A missing country also lets the region and postal code change, since they depend on it."""
    business = _setup_business()
    _setup_office(
        business, 'registeredOffice',
        {**STORED_ADDRESS, 'country': '', 'region': 'WA', 'postal_code': '98101'}, STORED_ADDRESS)
    office = _valid_office()

    assert validate(business, _build_filing({'offices': {'registeredOffice': office}})) is None

    office['mailingAddress']['addressCity'] = 'Victoria'
    err = validate(business, _build_filing({'offices': {'registeredOffice': office}}))
    assert err is not None
    assert [e['path'] for e in err.msg] == [
        '/filing/reviewImportedData/offices/registeredOffice/mailingAddress/addressCity',
    ]


def test_validate_invalid_fields_are_editable(session):
    """A field on record that the filing would reject (bad postal code, non BC office region) may be changed."""
    business = _setup_business()
    _setup_office(
        business, 'registeredOffice',
        {**STORED_ADDRESS, 'postal_code': '12345'}, {**STORED_ADDRESS, 'region': 'AB'})
    office = _valid_office()

    assert validate(business, _build_filing({'offices': {'registeredOffice': office}})) is None

    office['deliveryAddress']['addressCity'] = 'Victoria'
    err = validate(business, _build_filing({'offices': {'registeredOffice': office}}))
    assert err is not None
    assert [e['path'] for e in err.msg] == [
        '/filing/reviewImportedData/offices/registeredOffice/deliveryAddress/addressCity',
    ]


def test_validate_skips_po_box_rule_on_locked_street(session):
    """A PO Box already on record in a street that is not flagged cannot be fixed here, so it is not rejected."""
    business = _setup_business()
    _setup_office(
        business, 'registeredOffice',
        STORED_ADDRESS, {**STORED_ADDRESS, 'street': 'PO Box 123', 'postal_code': ''})
    office = _valid_office()
    office['deliveryAddress']['streetAddress'] = 'PO Box 123'

    assert validate(business, _build_filing({'offices': {'registeredOffice': office}})) is None


@pytest.mark.parametrize('street', ['PO Box 123', 'P.O. Box 123', 'Post Office Box 9', '123 Main St, PO Box 4'])
def test_validate_rejects_po_box_delivery_address(session, street):
    """An editable delivery address street cannot be a PO Box, for offices and directors alike."""
    business = _setup_business()
    # the office has no record and the director has no delivery street, so both streets are editable
    role = factory_party_role(
        Address.create_address({**VALID_ADDRESS, 'streetAddress': ''}),
        Address.create_address(VALID_ADDRESS),
        {'firstName': 'Joe', 'lastName': 'Swanson', 'middleInitial': 'P', 'partyType': 'person',
         'organizationName': ''},
        (datetime.utcnow() - datedelta.datedelta(years=5)).date().isoformat(),
        None,
        PartyRole.RoleTypes.DIRECTOR,
    )
    business.party_roles.append(role)
    business.save()
    party_id = role.party_id
    office = _valid_office()
    office['deliveryAddress']['streetAddress'] = street
    relationship = _valid_relationship(party_id)
    relationship['deliveryAddress']['streetAddress'] = street
    filing = _build_filing({'offices': {'registeredOffice': office}, 'relationships': [relationship]})

    err = validate(business, filing)

    assert err is not None
    paths = [e['path'] for e in err.msg if e['error'] == 'Address cannot be a PO Box.']
    assert paths == [
        '/filing/reviewImportedData/offices/registeredOffice/deliveryAddress/streetAddress',
        '/filing/reviewImportedData/relationships/0/deliveryAddress/streetAddress',
    ]


def test_validate_allows_po_box_mailing_address(session):
    """A mailing address may be a PO Box."""
    business = _setup_business()
    office = _valid_office()
    office['mailingAddress']['streetAddress'] = 'PO Box 123'

    assert validate(business, _build_filing({'offices': {'registeredOffice': office}})) is None
