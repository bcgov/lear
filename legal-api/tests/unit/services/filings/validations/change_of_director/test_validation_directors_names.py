import copy
import pytest
from http import HTTPStatus

import registry_schemas
from registry_schemas.example_data import CHANGE_OF_DIRECTORS

from legal_api.services.filings.validations.change_of_directors import validate_directors_name

# Minimal valid director structure for reuse
def make_director(**kwargs):
    base = {
        "actions": [],
        "officer": {
            "firstName": "John",
            "middleInitial": "Q",
            "lastName": "Public",
            "prevFirstName": "",
            "prevMiddleInitial": "",
            "prevLastName": ""
        }
    }
    for k, v in kwargs.items():
        if k == "officer":
            base["officer"].update(v)
        else:
            base[k] = v
    return base

@pytest.mark.parametrize(
    "test_name,directors,expected_msgs",
    [
        ("valid_minimal", [make_director()], []),
        # firstName/lastName "is required" moved to the schema; see
        # test_director_name_blank_or_whitespace_rejected_by_schema below.
        ("nameChanged_missing_prevFirstName", [make_director(actions=["nameChanged"], officer={"prevFirstName": "", "prevLastName": "Smith"})], [
            {"error": "Director prevFirstName is required when name has changed.", "path": "/filing/changeOfDirectors/directors/0/officer/prevFirstName"}
        ]),
        ("nameChanged_missing_prevLastName", [make_director(actions=["nameChanged"], officer={"prevFirstName": "Jane", "prevLastName": ""})], [
            {"error": "Director prevLastName is required when name has changed.", "path": "/filing/changeOfDirectors/directors/0/officer/prevLastName"}
        ]),
        ("leading_whitespace", [make_director(officer={"firstName": " John"})], [
            {"error": "Director firstName cannot have leading or trailing whitespace.", "path": "/filing/changeOfDirectors/directors/0/officer/firstName"}
        ]),
        ("trailing_whitespace", [make_director(officer={"lastName": "Public "})], [
            {"error": "Director lastName cannot have leading or trailing whitespace.", "path": "/filing/changeOfDirectors/directors/0/officer/lastName"}
        ]),
        ("over_max_length", [make_director(officer={"firstName": "A"*31})], [
            {"error": "Director firstName cannot be longer than 30 characters.", "path": "/filing/changeOfDirectors/directors/0/officer/firstName"}
        ]),
        ("multiple_directors", [
            make_director(),
            make_director(officer={"firstName": " John", "lastName": "Public "})
        ], [
            {"error": "Director firstName cannot have leading or trailing whitespace.", "path": "/filing/changeOfDirectors/directors/1/officer/firstName"},
            {"error": "Director lastName cannot have leading or trailing whitespace.", "path": "/filing/changeOfDirectors/directors/1/officer/lastName"}
        ]),
    ]
)
def test_validate_directors_name(test_name, directors, expected_msgs):
    cod = {
        "filing": {
            "changeOfDirectors": {
                "directors": directors
            }
        }
    }
    msgs = validate_directors_name(cod)
    msgs_simple = [
        {"error": m["error"].replace("Director ", "Director "), "path": m["path"]} for m in msgs
    ]
    assert msgs_simple == expected_msgs


@pytest.mark.parametrize("field", ["firstName", "lastName"])
@pytest.mark.parametrize("bad_value", ["", "   ", "\t", "\n", " John", "John ", "John\n"])
def test_director_name_blank_or_whitespace_rejected_by_schema(field, bad_value):
    """Blank/whitespace/surrounding-whitespace director firstName/lastName is rejected by the schema.

    The "is required" and "no leading/trailing whitespace" rules for director first/last names
    moved from legal-api into the business-schemas directors person pattern.
    """
    cod = copy.deepcopy(CHANGE_OF_DIRECTORS)
    cod["directors"][0]["officer"][field] = bad_value

    valid, _ = registry_schemas.validate({"changeOfDirectors": cod}, "change_of_directors")

    assert not valid
