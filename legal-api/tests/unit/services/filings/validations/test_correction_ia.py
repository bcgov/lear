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
"""Test Correction IA validations."""

import copy
from http import HTTPStatus
from unittest.mock import patch

import pytest
from registry_schemas.example_data import CORRECTION_INCORPORATION, INCORPORATION_FILING_TEMPLATE

from legal_api.services import NameXService
from legal_api.services.filings import validate
from tests.unit import MockResponse
from tests.unit.models import factory_completed_filing, factory_legal_entity
from tests.unit.services.filings.validations import lists_are_equal

INCORPORATION_APPLICATION = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
CORRECTION = copy.deepcopy(CORRECTION_INCORPORATION)


def test_valid_ia_correction(session):
    """Test that a valid IA without NR correction passes validation."""
    # setup
    identifier = "BC1234567"
    legal_entity = factory_legal_entity(identifier)

    corrected_filing = factory_completed_filing(legal_entity, INCORPORATION_APPLICATION)

    f = copy.deepcopy(CORRECTION)
    f["filing"]["header"]["identifier"] = identifier
    f["filing"]["correction"]["correctedFilingId"] = corrected_filing.id

    err = validate(legal_entity, f)

    if err:
        print(err.msg)

    # check that validation passed
    assert None is err


@pytest.mark.parametrize(
    "new_name, entity_type, nr_entity_type, nr_type, err_msg",
    [
        ("legal_name-BC1234568", "CP", "CP", "BECV", None),
        (
            "legal_name-BC1234567_Changed",
            "BEN",
            "CP",
            "BECV",
            "Name Request legal type is not same as the business legal type.",
        ),
        ("nr_not_approved", "BEN", "CP", "BECV", "Name Request is not approved."),
    ],
)
def test_nr_correction(session, new_name, entity_type, nr_entity_type, nr_type, err_msg):
    """Test that a valid NR correction passes validation."""
    # setup
    identifier = "BC1234567"
    legal_entity = factory_legal_entity(identifier)

    INCORPORATION_APPLICATION["filing"]["incorporationApplication"]["nameRequest"]["nrNumber"] = identifier
    INCORPORATION_APPLICATION["filing"]["incorporationApplication"]["nameRequest"]["legalName"] = "Test"

    corrected_filing = factory_completed_filing(legal_entity, INCORPORATION_APPLICATION)

    f = copy.deepcopy(CORRECTION)
    f["filing"]["header"]["identifier"] = identifier
    f["filing"]["correction"]["correctedFilingId"] = corrected_filing.id

    f["filing"]["correction"]["nameRequest"]["nrNumber"] = identifier
    f["filing"]["correction"]["nameRequest"]["legalName"] = new_name
    f["filing"]["correction"]["nameRequest"]["legalType"] = entity_type
    f["filing"]["business"]["legalType"] = entity_type

    nr_response_json = {
        "state": "INPROGRESS" if new_name == "nr_not_approved" else "APPROVED",
        "expirationDate": "",
        "legalType": nr_entity_type,
        "names": [
            {
                "name": new_name,
                "state": "INPROGRESS" if new_name == "nr_not_approved" else "APPROVED",
                "consumptionDate": "",
            }
        ],
    }
    nr_response = MockResponse(nr_response_json)

    with patch.object(NameXService, "query_nr_number", return_value=nr_response):
        err = validate(legal_entity, f)
        if err:
            print(err.msg)

    if not err_msg:
        assert None is err
    else:
        assert err
        assert HTTPStatus.BAD_REQUEST == err.code
        assert err.msg[0]["error"] == err_msg


@pytest.mark.parametrize(
    "test_name, entity_type, correction_type, err_msg",
    [
        ("valid_parties", "BEN", "CLIENT", None),
        ("valid_parties", "BC", "CLIENT", None),
        ("valid_parties", "ULC", "CLIENT", None),
        ("valid_parties", "CC", "CLIENT", None),
        ("valid_parties", "BEN", "STAFF", None),
        ("valid_parties", "BC", "STAFF", None),
        ("valid_parties", "ULC", "STAFF", None),
        ("valid_parties", "CC", "STAFF", None),
        (
            "no_roles",
            "BC",
            "CLIENT",
            [
                {"error": "Must have a minimum of one completing party", "path": "/filing/correction/parties/roles"},
                {"error": "Must have a minimum of 1 Director", "path": "/filing/correction/parties/roles"},
            ],
        ),
        (
            "no_roles",
            "ULC",
            "CLIENT",
            [
                {"error": "Must have a minimum of one completing party", "path": "/filing/correction/parties/roles"},
                {"error": "Must have a minimum of 1 Director", "path": "/filing/correction/parties/roles"},
            ],
        ),
        (
            "no_roles",
            "CC",
            "CLIENT",
            [
                {"error": "Must have a minimum of one completing party", "path": "/filing/correction/parties/roles"},
                {"error": "Must have a minimum of 3 Director", "path": "/filing/correction/parties/roles"},
            ],
        ),
        (
            "no_roles",
            "BEN",
            "CLIENT",
            [
                {"error": "Must have a minimum of one completing party", "path": "/filing/correction/parties/roles"},
                {"error": "Must have a minimum of 1 Director", "path": "/filing/correction/parties/roles"},
            ],
        ),
        (
            "no_roles",
            "BEN",
            "STAFF",
            [{"error": "Must have a minimum of 1 Director", "path": "/filing/correction/parties/roles"}],
        ),
        (
            "no_roles",
            "BC",
            "STAFF",
            [{"error": "Must have a minimum of 1 Director", "path": "/filing/correction/parties/roles"}],
        ),
        (
            "no_roles",
            "ULC",
            "STAFF",
            [{"error": "Must have a minimum of 1 Director", "path": "/filing/correction/parties/roles"}],
        ),
        (
            "no_roles",
            "CC",
            "STAFF",
            [{"error": "Must have a minimum of 3 Director", "path": "/filing/correction/parties/roles"}],
        ),
    ],
)
def test_parties_correction(session, test_name, entity_type, correction_type, err_msg):
    """Test that a valid NR correction passes validation."""
    # setup
    identifier = "BC1234567"
    legal_entity = factory_legal_entity(identifier)

    INCORPORATION_APPLICATION["filing"]["incorporationApplication"]["nameRequest"]["nrNumber"] = identifier
    INCORPORATION_APPLICATION["filing"]["incorporationApplication"]["nameRequest"]["legalName"] = "Test"

    corrected_filing = factory_completed_filing(legal_entity, INCORPORATION_APPLICATION)

    f = copy.deepcopy(CORRECTION)
    f["filing"]["header"]["identifier"] = identifier
    f["filing"]["correction"]["correctedFilingId"] = corrected_filing.id
    f["filing"]["correction"]["type"] = correction_type

    f["filing"]["correction"]["nameRequest"]["nrNumber"] = identifier
    f["filing"]["correction"]["nameRequest"]["legalName"] = "test"
    f["filing"]["correction"]["nameRequest"]["legalType"] = entity_type
    f["filing"]["business"]["legalType"] = entity_type

    if test_name == "no_roles":
        f["filing"]["correction"]["parties"][0]["roles"] = []
    elif test_name == "valid_parties":
        if entity_type == "CC":
            director = copy.deepcopy(f["filing"]["correction"]["parties"][0])
            del director["roles"][0]  # completing party
            f["filing"]["correction"]["parties"].append(director)
            f["filing"]["correction"]["parties"].append(director)

        if correction_type == "STAFF":
            del f["filing"]["correction"]["parties"][0]["roles"][0]  # completing party

    nr_response_json = {
        "state": "APPROVED",
        "expirationDate": "",
        "legalType": entity_type,
        "names": [{"name": "test", "state": "APPROVED", "consumptionDate": ""}],
    }
    nr_response = MockResponse(nr_response_json)

    with patch.object(NameXService, "query_nr_number", return_value=nr_response):
        err = validate(legal_entity, f)
        if err:
            print(err.msg)

    if err_msg:
        assert err
        assert HTTPStatus.BAD_REQUEST == err.code
        assert lists_are_equal(err.msg, err_msg)
    else:
        assert None is err


@pytest.mark.parametrize(
    "test_name, json1, json2, expected",
    [
        ("no effective date", {}, {"filing": {"header": {"effectiveDate": "1970-01-01T00:00:00+00:00"}}}, None),
        (
            "same effective date",
            {"filing": {"header": {"effectiveDate": "1970-01-01T00:00:00+00:00"}}},
            {"filing": {"header": {"effectiveDate": "1970-01-01T00:00:00+00:00"}}},
            None,
        ),
        (
            "changed effective date",
            {"filing": {"header": {"effectiveDate": "2020-01-01T00:00:00+00:00"}}},
            {"filing": {"header": {"effectiveDate": "1970-01-01T00:00:00+00:00"}}},
            {"error": "The effective date of a filing cannot be changed in a correction."},
        ),
        # invalid dates should be trapped by the JSONSchema validator
    ],
)
def test_validate_correction_effective_date(test_name, json1, json2, expected):
    """Assert that a corrected effective date."""
    from legal_api.services.filings.validations.incorporation_application import validate_correction_effective_date

    err = validate_correction_effective_date(json1, json2)

    assert err == expected
