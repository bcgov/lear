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
"""Test Correction validations."""
import copy
from http import HTTPStatus

from registry_schemas.example_data import ANNUAL_REPORT, CORRECTION_AR

from legal_api.services.filings import validate
from tests.unit.models import (
    factory_completed_filing,
    factory_filing,
    factory_legal_entity,
)


def test_valid_correction(session):
    """Test that a valid correction passes validation."""
    # setup
    identifier = "CP1234567"
    legal_entity = factory_legal_entity(identifier)
    corrected_filing = factory_completed_filing(legal_entity, ANNUAL_REPORT)

    f = copy.deepcopy(CORRECTION_AR)
    f["filing"]["header"]["identifier"] = identifier
    f["filing"]["correction"]["correctedFilingId"] = corrected_filing.id

    err = validate(legal_entity, f)
    if err:
        print(err.msg)

    # check that validation passed
    assert None is err


def test_correction__does_not_own_corrected_filing(session):
    """Check that a business cannot correct a different business' filing."""
    # setup
    identifier = "CP1234567"
    legal_entity = factory_legal_entity(identifier)
    business2 = factory_legal_entity("CP1111111")
    corrected_filing = factory_completed_filing(business2, ANNUAL_REPORT)

    f = copy.deepcopy(CORRECTION_AR)
    f["filing"]["header"]["identifier"] = identifier
    f["filing"]["correction"]["correctedFilingId"] = corrected_filing.id

    err = validate(legal_entity, f)
    if err:
        print(err.msg)

    # check that validation failed as expected
    assert HTTPStatus.BAD_REQUEST == err.code
    assert "Corrected filing is not a valid filing for this business." == err.msg[0]["error"]


def test_correction__corrected_filing_does_not_exist(session):
    """Check that a correction fails on a filing that does not exist."""
    # setup
    identifier = "CP2222567"
    legal_entity = factory_legal_entity(identifier)

    f = copy.deepcopy(CORRECTION_AR)
    f["filing"]["header"]["identifier"] = identifier
    f["filing"]["correction"]["correctedFilingId"] = 1

    err = validate(legal_entity, f)
    if err:
        print(err.msg)

    # check that validation failed as expected
    assert HTTPStatus.BAD_REQUEST == err.code
    assert err.msg[0]["error"].startswith("Corrected filing is not a valid filing")


def test_correction__corrected_filing_is_not_complete(session):
    """Check that a correction fails on a filing that is not complete."""
    # setup
    identifier = "CP1234567"
    legal_entity = factory_legal_entity(identifier)
    corrected_filing = factory_filing(legal_entity, ANNUAL_REPORT)

    f = copy.deepcopy(CORRECTION_AR)
    f["filing"]["header"]["identifier"] = identifier
    f["filing"]["correction"]["correctedFilingId"] = corrected_filing.id

    err = validate(legal_entity, f)
    if err:
        print(err.msg)

    # check that validation failed as expected
    assert HTTPStatus.BAD_REQUEST == err.code
    assert "Corrected filing is not a valid filing." == err.msg[0]["error"]
