# Copyright © 2022 Province of British Columbia
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
"""Test Firms Correction validations."""

import copy
from http import HTTPStatus
from unittest.mock import patch

import pytest
from registry_schemas.example_data import CORRECTION_REGISTRATION, CHANGE_OF_REGISTRATION_TEMPLATE

from legal_api.services import NaicsService, NameXService
from legal_api.services.filings import validate
from tests.unit.models import factory_business, factory_completed_filing
from tests.unit import MockResponse

CHANGE_OF_REGISTRATION_APPLICATION = copy.deepcopy(CHANGE_OF_REGISTRATION_TEMPLATE)

GP_CORRECTION_REGISTRATION_APPLICATION = copy.deepcopy(CORRECTION_REGISTRATION)
GP_CORRECTION_REGISTRATION_APPLICATION['filing']['correction']['legalType'] = 'GP'
GP_CORRECTION_REGISTRATION_APPLICATION['filing']['business']['legalType'] = 'GP'
GP_CORRECTION_REGISTRATION_APPLICATION['filing']['correction']['type'] = 'CLIENT'

SP_CORRECTION_REGISTRATION_APPLICATION = copy.deepcopy(CORRECTION_REGISTRATION)
SP_CORRECTION_REGISTRATION_APPLICATION['filing']['correction']['type'] = 'CLIENT'
SP_CORRECTION_REGISTRATION_APPLICATION['filing']['correction']['legalType'] = 'SP'
SP_CORRECTION_REGISTRATION_APPLICATION['filing']['business']['legalType'] = 'SP'
SP_CORRECTION_REGISTRATION_APPLICATION['filing']['correction']['nameRequest']['legalType'] = 'SP'
SP_CORRECTION_REGISTRATION_APPLICATION['filing']['correction']['parties'][0]['roles'] = [
    {
        'roleType': 'Completing Party',
        'appointmentDate': '2022-01-01'

    },
    {
        'roleType': 'Proprietor',
        'appointmentDate': '2022-01-01'

    }
]
del SP_CORRECTION_REGISTRATION_APPLICATION['filing']['correction']['parties'][1]

nr_response = {
    'state': 'APPROVED',
    'expirationDate': '',
    'names': [{
        'name': CORRECTION_REGISTRATION['filing']['correction']['nameRequest']['legalName'],
        'state': 'APPROVED',
        'consumptionDate': ''
    }]
}

naics_response = {
    'code': CORRECTION_REGISTRATION['filing']['correction']['business']['naics']['naicsCode'],
    'classTitle': CORRECTION_REGISTRATION['filing']['correction']['business']['naics']['naicsDescription']
}

@pytest.mark.parametrize(
    'test_name, filing',
    [
        ('sp_correction', SP_CORRECTION_REGISTRATION_APPLICATION),
        ('gp_correction', GP_CORRECTION_REGISTRATION_APPLICATION),
    ]
)
def test_valid_firms_correction(session, test_name, filing):
    """Test that a valid Firms correction passes validation."""
    # setup
    identifier = 'FM1234567'
    business = factory_business(identifier)
    corrected_filing = factory_completed_filing(business, CHANGE_OF_REGISTRATION_APPLICATION)

    f = copy.deepcopy(filing)

    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id

    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_response)):
        with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
            err = validate(business, f)

            if err:
                print(err.msg)

    # check that validation passed
    assert None is err


@pytest.mark.parametrize(
    'test_name, filing, expected_msg',
    [
        ('sp_invalid_party', SP_CORRECTION_REGISTRATION_APPLICATION, '1 Proprietor and a Completing Party is required.'),
        ('gp_invalid_party', GP_CORRECTION_REGISTRATION_APPLICATION, '2 Partners and a Completing Party is required.'),
    ]
)
def test_firms_correction_invalid_parties(session, test_name, filing, expected_msg):
    """Test that a invalid Firms correction fails validation."""
    # setup
    identifier = 'FM1234567'
    business = factory_business(identifier)
    corrected_filing = factory_completed_filing(business, CHANGE_OF_REGISTRATION_APPLICATION)

    f = copy.deepcopy(filing)

    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id

    del f['filing']['correction']['parties'][0]['roles'][0]
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_response)):
        with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
            err = validate(business, f)

            if err:
                print(err.msg)

    # check that validation passed
    assert err
    assert err.msg[0]['error'] == expected_msg



@pytest.mark.parametrize(
    'test_name, filing, existing_naics_code, existing_naics_desc, correction_naics_code, correction_naics_desc, naics_response, expected_msg',
    [
        # SP tests
        ('sp_naics_new_valid_naics_code_and_desc', SP_CORRECTION_REGISTRATION_APPLICATION,
         '112910', 'Apiculture', '112510', 'Aquaculture', {'code': '112510', 'classTitle': 'Aquaculture'}, None),
        ('sp_naics_new_valid_naics_code_and_desc', SP_CORRECTION_REGISTRATION_APPLICATION,
         None, None, '112510', 'Aquaculture', {'code': '112510', 'classTitle': 'Aquaculture'}, None),
        ('sp_naics_new_valid_naics_code_and_desc', SP_CORRECTION_REGISTRATION_APPLICATION,
         None, 'some desc', '112510', 'Aquaculture', {'code': '112510', 'classTitle': 'Aquaculture'}, None),
        ('sp_no_naics_changes', SP_CORRECTION_REGISTRATION_APPLICATION, '112910', 'Apiculture', '112910', 'Apiculture',
         None, None),
        ('sp_no_naics_changes', SP_CORRECTION_REGISTRATION_APPLICATION, None, '112910', None, '112910', None, None),
        ('sp_no_naics_changes', SP_CORRECTION_REGISTRATION_APPLICATION, '112910', None, '112910', None, None, None),
        ('sp_no_naics_changes', SP_CORRECTION_REGISTRATION_APPLICATION, None, 'some desc', None, 'some desc', None, None),
        ('sp_naics_change_no_code_match', SP_CORRECTION_REGISTRATION_APPLICATION,
         '112910', 'Apiculture', '111111', 'desc 23434', None, 'Invalid naics code or description.'),
        ('sp_naics_change_desc_mismatch', SP_CORRECTION_REGISTRATION_APPLICATION,
         '112910', 'Apiculture', '112910', 'wrong desc', {'code': '112910', 'classTitle': 'Apiculture'},
         'Invalid naics code or description.'),
        # GP tests
        ('gp_naics_new_valid_naics_code_and_desc', GP_CORRECTION_REGISTRATION_APPLICATION,
         '112910', 'Apiculture', '112510', 'Aquaculture', {'code': '112510', 'classTitle': 'Aquaculture'}, None),
        ('gp_naics_new_valid_naics_code_and_desc', GP_CORRECTION_REGISTRATION_APPLICATION,
         None, None, '112510', 'Aquaculture', {'code': '112510', 'classTitle': 'Aquaculture'}, None),
        ('gp_naics_new_valid_naics_code_and_desc', GP_CORRECTION_REGISTRATION_APPLICATION,
         None, 'some desc', '112510', 'Aquaculture', {'code': '112510', 'classTitle': 'Aquaculture'}, None),
        ('gp_no_naics_changes', GP_CORRECTION_REGISTRATION_APPLICATION, '112910', 'Apiculture', '112910', 'Apiculture',
         None, None),
        ('gp_no_naics_changes', GP_CORRECTION_REGISTRATION_APPLICATION, None, '112910', None, '112910', None, None),
        ('gp_no_naics_changes', GP_CORRECTION_REGISTRATION_APPLICATION, '112910', None, '112910', None, None, None),
        ('gp_no_naics_changes', GP_CORRECTION_REGISTRATION_APPLICATION, None, 'some desc', None, 'some desc', None, None),
        ('gp_naics_change_no_code_match', GP_CORRECTION_REGISTRATION_APPLICATION,
         '112910', 'Apiculture', '111111', 'desc 23434', None, 'Invalid naics code or description.'),
        ('gp_naics_change_desc_mismatch', GP_CORRECTION_REGISTRATION_APPLICATION,
         '112910', 'Apiculture', '112910', 'wrong desc', {'code': '112910', 'classTitle': 'Apiculture'},
         'Invalid naics code or description.'),
    ]
)
def test_firms_correction_naics(session, test_name, filing, existing_naics_code, existing_naics_desc,
                                correction_naics_code, correction_naics_desc, naics_response, expected_msg):
    """Test that NAICS code and description are correctly validated."""
    # setup
    identifier = 'FM1234567'
    business = factory_business(identifier=identifier, naics_code=existing_naics_code, naics_desc=existing_naics_desc)

    corrected_filing = factory_completed_filing(business, CHANGE_OF_REGISTRATION_APPLICATION)

    f = copy.deepcopy(filing)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id
    if correction_naics_code:
        f['filing']['correction']['business']['naics']['naicsCode'] = correction_naics_code
    else:
        del f['filing']['correction']['business']['naics']['naicsCode']
    if correction_naics_desc:
        f['filing']['correction']['business']['naics']['naicsDescription'] = correction_naics_desc
    else:
        del f['filing']['correction']['business']['naics']['naicsDescription']

    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_response)):
        with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
            err = validate(business, f)

            if err:
                print(err.msg)

    # check for expected validation resultsn
    if expected_msg:
        assert err
        assert err.msg[0]['error'] == expected_msg
    else:
        assert None is err
