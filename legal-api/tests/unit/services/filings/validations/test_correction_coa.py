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

from registry_schemas.example_data import CHANGE_OF_ADDRESS, CORRECTION_COA, FILING_TEMPLATE

from legal_api.services.filings import validate
from tests.unit.models import factory_legal_entity, factory_completed_filing


def test_valid_coa_correction(session):
    """Test that a valid COA correction passes validation."""
    # setup
    identifier = 'CP1234567'
    name = 'changeOfAddress'
    legal_entity =factory_legal_entity(identifier)
    coa = copy.deepcopy(FILING_TEMPLATE)
    coa['filing']['header']['name'] = name
    coa['filing'][name] = CHANGE_OF_ADDRESS
    corrected_filing = factory_completed_filing(legal_entity, coa)

    f = copy.deepcopy(CORRECTION_COA)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id
    f['filing'][name]['offices']['registeredOffice']['deliveryAddress']['addressCountry'] = 'CA'
    f['filing'][name]['offices']['registeredOffice']['mailingAddress']['addressCountry'] = 'CA'

    err = validate(legal_entity, f)
    if err:
        print(err.msg)

    # check that validation passed
    assert None is err


def test_fail_coa_correction(session):
    """Test that an invalid COA correction passes validation."""
    # setup
    identifier = 'CP1234567'
    name = 'changeOfAddress'
    legal_entity =factory_legal_entity(identifier)
    coa = copy.deepcopy(FILING_TEMPLATE)
    coa['filing']['header']['name'] = name
    coa['filing'][name] = CHANGE_OF_ADDRESS
    corrected_filing = factory_completed_filing(legal_entity, coa)

    f = copy.deepcopy(CORRECTION_COA)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id
    f['filing'][name]['offices']['registeredOffice']['deliveryAddress']['addressCountry'] = 'DANG'
    f['filing'][name]['offices']['registeredOffice']['mailingAddress']['addressCountry'] = 'NABBIT'

    err = validate(legal_entity, f)
    if err:
        print(err.msg)

    # check that validation failed
    assert err
    assert HTTPStatus.BAD_REQUEST == err.code
    assert len(err.msg) == 2
    for msg in err.msg:
        assert "Address Country must be 'CA'." == msg['error']
