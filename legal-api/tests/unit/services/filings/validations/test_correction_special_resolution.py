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
"""Test Correction SPECIAL_RESOLUTION validations."""

import copy
from http import HTTPStatus

import pytest
from registry_schemas.example_data import CORRECTION_CP_SPECIAL_RESOLUTION,\
                                        CP_SPECIAL_RESOLUTION_TEMPLATE, FILING_HEADER
from legal_api.services.filings import validate
from tests.unit.models import factory_business, factory_completed_filing
from tests.unit.services.filings.validations import lists_are_equal

CP_SPECIAL_RESOLUTION_APPLICATION = copy.deepcopy(CP_SPECIAL_RESOLUTION_TEMPLATE)

def test_valid_special_resolution_correction(mocker, session):
    """Test that a valid SPECIAL_RESOLUTION correction passes validation."""
    # setup
    identifier = 'CP1234567'
    business = factory_business(identifier)
    corrected_filing = factory_completed_filing(business, CP_SPECIAL_RESOLUTION_APPLICATION)

    correction_data = copy.deepcopy(FILING_HEADER)
    correction_data['filing']['correction'] = copy.deepcopy(CORRECTION_CP_SPECIAL_RESOLUTION)
    correction_data['filing']['header']['name'] = 'correction'
    f = copy.deepcopy(correction_data)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id

    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=True)

    err = validate(business, f)

    if err:
        print(err.msg)

    # check that validation passed
    assert None is err


@pytest.mark.parametrize('test_name, legal_type, correction_type, err_msg', [
    ('valid_parties', 'CP', 'CLIENT', None),
    ('valid_parties', 'CP', 'STAFF', None),
    ('no_parties', 'CP', 'CLIENT', 
     [{'error': 'Parties list cannot be empty or null', 'path': '/filing/correction/parties/roles'}]),
    ('no_parties', 'CP', 'STAFF', 
     [{'error': 'Parties list cannot be empty or null', 'path': '/filing/correction/parties/roles'}]),
    ('empty_parties', 'CP', 'CLIENT', 
     [{'error': 'Parties list cannot be empty or null', 'path': '/filing/correction/parties/roles'}]),
    ('empty_parties', 'CP', 'STAFF', 
     [{'error': 'Parties list cannot be empty or null', 'path': '/filing/correction/parties/roles'}]),
    ('no_roles', 'CP', 'CLIENT',
     [{'error': 'Must have a minimum of one completing party', 'path': '/filing/correction/parties/roles'},
      {'error': 'Must have a minimum of three Directors', 'path': '/filing/correction/parties/roles'}]),
    ('no_roles', 'CP', 'STAFF',
     [{'error': 'Must have a minimum of three Directors', 'path': '/filing/correction/parties/roles'}]),
    ('only_completing', 'CP', 'CLIENT', 
     [{'error': 'Must have a minimum of three Directors', 'path': '/filing/correction/parties/roles'}]),
    ('only_completing', 'CP', 'STAFF', 
     [{'error': 'Should not provide completing party when correction type is STAFF', 'path': '/filing/correction/parties/roles'},
      {'error': 'Must have a minimum of three Directors', 'path': '/filing/correction/parties/roles'}]),
])
def test_parties_special_resolution_correction(mocker, session, test_name, legal_type, correction_type, err_msg):
    """Test parties for SPECIAL_RESOLUTION correction."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier)
    corrected_filing = factory_completed_filing(business, CP_SPECIAL_RESOLUTION_APPLICATION)

    correction_data = copy.deepcopy(FILING_HEADER)
    correction_data['filing']['correction'] = copy.deepcopy(CORRECTION_CP_SPECIAL_RESOLUTION)
    correction_data['filing']['header']['name'] = 'correction'
    
    f = copy.deepcopy(correction_data)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id
    f['filing']['correction']['type'] = correction_type

    if test_name == 'no_roles':
        f['filing']['correction']['parties'][0]['roles'] = []
        f['filing']['correction']['parties'][1]['roles'] = []
        f['filing']['correction']['parties'][2]['roles'] = []
    elif test_name == "no_parties":
        del f['filing']['correction']['parties']
    elif test_name == "empty_parties":
        f['filing']['correction']['parties'] = []
    elif test_name == "only_completing":
        del f['filing']['correction']['parties'][2]
        del f['filing']['correction']['parties'][1]
        del f['filing']['correction']['parties'][0]['roles'][1]
    elif test_name == 'valid_parties':
        if correction_type == 'STAFF':
            del f['filing']['correction']['parties'][0]['roles'][0]  # completing party

    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=True)

    err = validate(business, f)
    if err:
      print(err.msg)

    if err_msg:
        assert err
        assert HTTPStatus.BAD_REQUEST == err.code
        assert lists_are_equal(err.msg, err_msg)
    else:
        assert None is err
