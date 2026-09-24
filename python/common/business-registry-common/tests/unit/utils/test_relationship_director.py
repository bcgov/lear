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
"""Tests for the changeOfDirectors relationship -> legacy director converter."""
import copy

import pytest

from business_common.utils.relationship_director import (
    cod_directors,
    is_change_free,
    map_relationship_actions,
    relationship_to_director,
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
        {
            "appointmentDate": "2018-01-01",
            "cessationDate": None,
            "roleType": "Director",
            "roleClass": "DIRECTOR",
        }
    ],
    "actions": ["NAME_CHANGED"],
}


def test_relationship_to_director_person():
    """Assert the full person entity -> officer field mapping."""
    director = relationship_to_director(copy.deepcopy(PERSON_RELATIONSHIP))

    assert director["officer"] == {
        "firstName": "Joe",
        "middleInitial": "P",
        "lastName": "Swanson",
        "partyType": "person",
        "email": "joe@example.com",
        "id": 1234,
    }
    assert director["appointmentDate"] == "2018-01-01"
    assert director["cessationDate"] is None
    assert director["deliveryAddress"] == DELIVERY_ADDRESS
    assert director["mailingAddress"] == MAILING_ADDRESS
    assert director["actions"] == ["nameChanged"]


def test_relationship_to_director_organization():
    """Assert an organization entity maps to organizationName and partyType."""
    relationship = copy.deepcopy(PERSON_RELATIONSHIP)
    relationship["entity"] = {"identifier": "99", "businessName": "ACME Holdings Ltd."}

    director = relationship_to_director(relationship)

    assert director["officer"]["organizationName"] == "ACME Holdings Ltd."
    assert director["officer"]["partyType"] == "organization"
    assert director["officer"]["firstName"] == ""
    assert director["officer"]["lastName"] == ""


def test_relationship_to_director_id_cast():
    """Assert digit-string identifiers cast to int and others pass through."""
    relationship = copy.deepcopy(PERSON_RELATIONSHIP)

    relationship["entity"]["identifier"] = "007"
    assert relationship_to_director(relationship)["officer"]["id"] == 7

    relationship["entity"]["identifier"] = "BC1234567"
    assert relationship_to_director(relationship)["officer"]["id"] == "BC1234567"

    del relationship["entity"]["identifier"]
    assert "id" not in relationship_to_director(relationship)["officer"]


def test_relationship_to_director_multi_role_lifts_director_dates():
    """Assert the Director role's dates are lifted when other roles are present."""
    relationship = copy.deepcopy(PERSON_RELATIONSHIP)
    relationship["roles"] = [
        {"roleType": "Officer", "appointmentDate": "2010-05-05", "cessationDate": "2011-06-06"},
        {"roleType": "Director", "appointmentDate": "2020-02-02", "cessationDate": "2023-03-03"},
    ]

    director = relationship_to_director(relationship)

    assert director["appointmentDate"] == "2020-02-02"
    assert director["cessationDate"] == "2023-03-03"


def test_relationship_to_director_no_director_role():
    """Assert missing Director role leaves dates unset without raising."""
    relationship = copy.deepcopy(PERSON_RELATIONSHIP)
    relationship["roles"] = [{"roleType": "Officer", "appointmentDate": "2010-05-05"}]

    director = relationship_to_director(relationship)

    assert director["appointmentDate"] is None
    assert director["cessationDate"] is None


def test_relationship_to_director_missing_addresses():
    """Assert absent addresses are not emitted as keys."""
    relationship = copy.deepcopy(PERSON_RELATIONSHIP)
    del relationship["deliveryAddress"]
    del relationship["mailingAddress"]

    director = relationship_to_director(relationship)

    assert "deliveryAddress" not in director
    assert "mailingAddress" not in director


@pytest.mark.parametrize(
    "test_name, actions, identifier, cessation_date, expected",
    [
        ("added", ["ADDED"], None, None, ["appointed"]),
        ("removed", ["REMOVED"], "1234", "2023-01-01", ["ceased"]),
        ("name_changed", ["NAME_CHANGED"], "1234", None, ["nameChanged"]),
        ("address_changed", ["ADDRESS_CHANGED"], "1234", None, ["addressChanged"]),
        ("multiple", ["NAME_CHANGED", "ADDRESS_CHANGED"], "1234", None, ["nameChanged", "addressChanged"]),
        ("changed_derives_edit", ["CHANGED"], "1234", None, []),
        ("changed_derives_ceased", ["CHANGED"], "1234", "2023-01-01", ["ceased"]),
        ("changed_derives_appointed", ["CHANGED"], None, None, ["appointed"]),
        ("unknown_ignored", ["ROLES_CHANGED"], "1234", None, []),
        ("absent_derives_edit", None, "1234", None, []),
        ("absent_derives_ceased", None, "1234", "2023-01-01", ["ceased"]),
        ("absent_derives_appointed", None, None, None, ["appointed"]),
        ("empty_derives_edit", [], "1234", None, []),
    ],
)
def test_map_relationship_actions(test_name, actions, identifier, cessation_date, expected):
    """Assert explicit action mapping and the derivation fallback."""
    relationship = copy.deepcopy(PERSON_RELATIONSHIP)
    relationship["roles"][0]["cessationDate"] = cessation_date
    if identifier is None:
        del relationship["entity"]["identifier"]
    else:
        relationship["entity"]["identifier"] = identifier
    if actions is None:
        del relationship["actions"]
    else:
        relationship["actions"] = actions

    assert map_relationship_actions(relationship) == expected


def test_actions_key_always_present():
    """Assert converted directors always carry an actions key."""
    relationship = copy.deepcopy(PERSON_RELATIONSHIP)
    del relationship["actions"]

    assert relationship_to_director(relationship)["actions"] == []


def test_cod_directors_legacy_passthrough():
    """Assert a legacy directors array is returned untouched."""
    directors = [{"officer": {"lastName": "Griffin"}, "actions": ["appointed"]}]

    assert cod_directors({"directors": directors}) is directors


def test_cod_directors_converts_relationships():
    """Assert relationships convert to legacy directors."""
    result = cod_directors({"relationships": [copy.deepcopy(PERSON_RELATIONSHIP)]})

    assert len(result) == 1
    assert result[0]["officer"]["lastName"] == "Swanson"
    assert result[0]["actions"] == ["nameChanged"]


def test_cod_directors_empty():
    """Assert an empty body yields an empty list."""
    assert cod_directors({}) == []


@pytest.mark.parametrize(
    "actions, expected",
    [
        (["nameChanged"], True),
        (["addressChanged"], True),
        (["nameChanged", "addressChanged"], True),
        ([], True),
        (None, True),
        (["appointed"], False),
        (["ceased"], False),
        (["appointed", "nameChanged"], False),
    ],
)
def test_is_change_free(actions, expected):
    """Assert the free filing determination matches the legacy fee rules."""
    director = {"officer": {"lastName": "Swanson"}}
    if actions is not None:
        director["actions"] = actions

    assert is_change_free(director) is expected
