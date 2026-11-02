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
"""Tests for the relationship -> legacy party converter."""

import copy

import pytest

from business_common.utils.relationship_party import (
    COLIN_PARTY_SHAPE_FILING_TYPES,
    PARTY_SHAPE_FILING_TYPES,
    get_parties,
    has_both_party_shapes,
    party_key,
    relationship_to_party,
)

DELIVERY_ADDRESS = {
    "streetAddress": "delivery_address - address line one",
    "addressCity": "delivery_address city",
    "addressCountry": "CA",
    "postalCode": "H0H0H0",
    "addressRegion": "BC",
}
MAILING_ADDRESS = {
    "streetAddress": "mailing_address - address line one",
    "addressCity": "mailing_address city",
    "addressCountry": "CA",
    "postalCode": "H0H0H0",
    "addressRegion": "BC",
}
PERSON_RELATIONSHIP = {
    "entity": {
        "identifier": "1234",
        "givenName": "Joe",
        "middleInitial": "P",
        "familyName": "Swanson",
        "email": "joe@example.com",
    },
    "deliveryAddress": DELIVERY_ADDRESS,
    "mailingAddress": MAILING_ADDRESS,
    "roles": [
        {"appointmentDate": "2018-01-01", "roleType": "Completing Party"},
        {"appointmentDate": "2018-01-01", "cessationDate": None, "roleType": "Director", "roleClass": "DIRECTOR"},
    ],
    "actions": ["ADDED"],
}
ORGANIZATION_RELATIONSHIP = {
    "entity": {
        "businessName": "Xyz Inc.",
        "businessIdentifier": "BC1234567",
        "email": "xyz@example.com",
    },
    "deliveryAddress": DELIVERY_ADDRESS,
    "mailingAddress": MAILING_ADDRESS,
    "roles": [{"appointmentDate": "2018-01-01", "roleType": "Incorporator"}],
}
LEGACY_PARTY = {
    "officer": {"firstName": "Joe", "lastName": "Swanson", "partyType": "person"},
    "mailingAddress": MAILING_ADDRESS,
    "roles": [{"roleType": "Director", "appointmentDate": "2018-01-01"}],
}


def test_relationship_to_party_person():
    """Assert the full person entity -> officer mapping, role passthrough and dropped keys."""
    party = relationship_to_party(copy.deepcopy(PERSON_RELATIONSHIP))

    assert party == {
        "officer": {
            "firstName": "Joe",
            "middleInitial": "P",
            "lastName": "Swanson",
            "partyType": "person",
            "email": "joe@example.com",
            "id": 1234,
        },
        "roles": [
            {"roleType": "Completing Party", "appointmentDate": "2018-01-01", "cessationDate": None},
            {"roleType": "Director", "appointmentDate": "2018-01-01", "cessationDate": None},
        ],
        "deliveryAddress": DELIVERY_ADDRESS,
        "mailingAddress": MAILING_ADDRESS,
    }


def test_relationship_to_party_organization():
    """Assert the organization entity -> officer mapping incl. businessIdentifier -> identifier."""
    party = relationship_to_party(copy.deepcopy(ORGANIZATION_RELATIONSHIP))

    assert party["officer"] == {
        "firstName": "",
        "middleInitial": "",
        "lastName": "",
        "partyType": "organization",
        "organizationName": "Xyz Inc.",
        "identifier": "BC1234567",
        "email": "xyz@example.com",
    }


@pytest.mark.parametrize(
    "identifier, expected",
    [
        ("12", 12),
        (34, 34),
        ("", None),
        (None, None),
        ("3fa85f64-5717-4562-b3fc-2c963f66afa6", "3fa85f64-5717-4562-b3fc-2c963f66afa6"),
    ],
)
def test_relationship_to_party_id_cast(identifier, expected):
    """Assert digit identifiers cast to int, empty identifiers are absent, other strings pass through."""
    relationship = copy.deepcopy(PERSON_RELATIONSHIP)
    relationship["entity"]["identifier"] = identifier

    officer = relationship_to_party(relationship)["officer"]

    if expected is None:
        assert "id" not in officer
    else:
        assert officer["id"] == expected


def test_relationship_to_party_optional_entity_fields():
    """Assert additionalName -> middleName and alternateName passthrough only when present."""
    relationship = copy.deepcopy(PERSON_RELATIONSHIP)
    relationship["entity"]["additionalName"] = "Patrick"
    relationship["entity"]["alternateName"] = "Joey"
    del relationship["entity"]["email"]

    officer = relationship_to_party(relationship)["officer"]

    assert officer["middleName"] == "Patrick"
    assert officer["alternateName"] == "Joey"
    assert "email" not in officer
    assert "organizationName" not in officer


def test_relationship_to_party_roles_always_carry_date_keys():
    """Assert roles keep roleType case and both date keys even when the payload omits them."""
    relationship = copy.deepcopy(PERSON_RELATIONSHIP)
    relationship["roles"] = [{"roleType": "Director"}]

    party = relationship_to_party(relationship)

    assert party["roles"] == [{"roleType": "Director", "appointmentDate": None, "cessationDate": None}]


def test_relationship_to_party_missing_addresses_and_actions_dropped():
    """Assert absent addresses are not emitted and actions never reach the party dict."""
    relationship = copy.deepcopy(PERSON_RELATIONSHIP)
    del relationship["deliveryAddress"]

    party = relationship_to_party(relationship)

    assert "deliveryAddress" not in party
    assert party["mailingAddress"] == MAILING_ADDRESS
    assert "actions" not in party


def test_relationship_to_party_does_not_mutate_or_share_input():
    """Assert the input is untouched and addresses are copied, not shared."""
    relationship = copy.deepcopy(PERSON_RELATIONSHIP)
    original = copy.deepcopy(relationship)

    party = relationship_to_party(relationship)
    party["mailingAddress"]["addressCity"] = "changed"

    assert relationship == original


def test_get_parties_prefers_parties_when_present():
    """Assert parties win over relationships, and an empty parties list is not converted."""
    assert get_parties({"parties": [LEGACY_PARTY], "relationships": [PERSON_RELATIONSHIP]}) == [LEGACY_PARTY]
    assert get_parties({"parties": [], "relationships": [PERSON_RELATIONSHIP]}) == []
    assert get_parties({"parties": None}) == []


def test_get_parties_converts_relationships():
    """Assert relationships are converted when parties is absent."""
    parties = get_parties({"relationships": [PERSON_RELATIONSHIP, ORGANIZATION_RELATIONSHIP]})

    assert [party["officer"]["partyType"] for party in parties] == ["person", "organization"]
    assert parties[0]["roles"][1]["roleType"] == "Director"


def test_get_parties_empty():
    """Assert an empty list when neither shape is present."""
    assert get_parties({}) == []
    assert get_parties({"relationships": None}) == []


@pytest.mark.parametrize(
    "section, expected",
    [
        ({"parties": []}, "parties"),
        ({"parties": [LEGACY_PARTY]}, "parties"),
        ({"relationships": []}, "relationships"),
        ({"parties": [], "relationships": []}, "parties"),
        ({"offices": {}}, None),
    ],
)
def test_party_key(section, expected):
    """Assert party_key reports key presence, not truthiness."""
    assert party_key(section) == expected


def test_has_both_party_shapes():
    """Assert both-present detection."""
    assert has_both_party_shapes({"parties": [], "relationships": []})
    assert not has_both_party_shapes({"parties": []})
    assert not has_both_party_shapes({"relationships": []})


def test_filing_type_sets():
    """Assert the COLIN subset is contained in the party-shape set and both are frozen."""
    assert COLIN_PARTY_SHAPE_FILING_TYPES <= PARTY_SHAPE_FILING_TYPES
    assert isinstance(PARTY_SHAPE_FILING_TYPES, frozenset)
    assert "continuationIn" in PARTY_SHAPE_FILING_TYPES
