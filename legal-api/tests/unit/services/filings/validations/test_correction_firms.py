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
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

import pytest
from registry_schemas.example_data import CORRECTION_REGISTRATION, CHANGE_OF_REGISTRATION_TEMPLATE

from legal_api.services import NaicsService, NameXService
from legal_api.services.filings import validate
from legal_api.services.authz import STAFF_ROLE, BASIC_USER
from tests.unit.models import factory_business, factory_completed_filing
from tests.unit import MockResponse

from ...utils import helper_create_jwt

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
def test_valid_firms_correction(mocker, app, session, jwt, test_name, filing):
    """Test that a valid Firms correction passes validation."""
    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=False)  # Client
    
    # setup
    identifier = 'FM1234567'
    founding_date = datetime(2022, 1, 1)
    f = copy.deepcopy(filing)
    legal_type = f['filing']['correction']['nameRequest']['legalType']
    business = factory_business(identifier, founding_date=founding_date, entity_type=legal_type)
    corrected_filing = factory_completed_filing(business, CHANGE_OF_REGISTRATION_APPLICATION)

    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id

    nr_res = copy.deepcopy(nr_response)
    nr_res['legalType'] = legal_type
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_res)):
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
def test_firms_correction_invalid_parties(mocker, app, session, jwt, test_name, filing, expected_msg):
    """Test that a invalid Firms correction fails validation."""
    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=False)  # Client
    
    # setup
    identifier = 'FM1234567'
    f = copy.deepcopy(filing)
    legal_type = f['filing']['correction']['nameRequest']['legalType']
    business = factory_business(identifier, entity_type=legal_type)
    corrected_filing = factory_completed_filing(business, CHANGE_OF_REGISTRATION_APPLICATION)

    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id

    del f['filing']['correction']['parties'][0]['roles'][0]
    nr_res = copy.deepcopy(nr_response)
    nr_res['legalType'] = legal_type
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_res)):
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
def test_firms_correction_naics(mocker, app, session, jwt, test_name, filing, existing_naics_code, existing_naics_desc,
                                correction_naics_code, correction_naics_desc, naics_response, expected_msg):
    """Test that NAICS code and description are correctly validated."""
    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=False)  # Client
    
    # setup
    identifier = 'FM1234567'
    founding_date = datetime(2022, 1, 1)
    f = copy.deepcopy(filing)
    legal_type = f['filing']['correction']['nameRequest']['legalType']
    business = factory_business(identifier=identifier, founding_date=founding_date, naics_code=existing_naics_code, naics_desc=existing_naics_desc, entity_type=legal_type)

    corrected_filing = factory_completed_filing(business, CHANGE_OF_REGISTRATION_APPLICATION)

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

    nr_res = copy.deepcopy(nr_response)
    nr_res['legalType'] = legal_type
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_res)):
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


@pytest.mark.parametrize('test_name, filing, username, roles, founding_date_str, delta_date, is_valid', 
                         [
                             ('sp_no_correction_by_staff', SP_CORRECTION_REGISTRATION_APPLICATION, 'staff', STAFF_ROLE, '2022-01-01', None, True),
                             ('gp_no_correction_by_staff', GP_CORRECTION_REGISTRATION_APPLICATION, 'staff', STAFF_ROLE, '2022-01-01', None, True),
                             ('sp_correction_greater_by_staff', SP_CORRECTION_REGISTRATION_APPLICATION, 'staff', STAFF_ROLE, '2022-01-01', timedelta(days=90), True),
                             ('gp_correction_greater_by_staff', GP_CORRECTION_REGISTRATION_APPLICATION, 'staff', STAFF_ROLE, '2022-01-01', timedelta(days=90), True),
                             ('sp_correction_invalid_greater_by_staff', SP_CORRECTION_REGISTRATION_APPLICATION, 'staff', STAFF_ROLE, '2022-01-01', timedelta(days=91), False),
                             ('gp_correction_invalid_greater_by_staff', GP_CORRECTION_REGISTRATION_APPLICATION, 'staff', STAFF_ROLE, '2022-01-01', timedelta(days=91), False),
                             ('sp_correction_lesser_by_staff', SP_CORRECTION_REGISTRATION_APPLICATION, 'staff', STAFF_ROLE, '2022-01-01', relativedelta(years=-20), True),
                             ('gp_correction_lesser_by_staff', GP_CORRECTION_REGISTRATION_APPLICATION, 'staff', STAFF_ROLE, '2022-01-01', relativedelta(years=-20), True),

                             ('sp_no_correction_by_general_user', SP_CORRECTION_REGISTRATION_APPLICATION, 'general user', [BASIC_USER], '2022-01-01', None, True),
                             ('gp_no_correction_by_general_user', GP_CORRECTION_REGISTRATION_APPLICATION, 'general user', [BASIC_USER], '2022-01-01', None, True),
                             ('sp_correction_greater_by_general_user', SP_CORRECTION_REGISTRATION_APPLICATION, 'general user', [BASIC_USER], '2022-01-01', timedelta(days=90), True),
                             ('gp_correction_greater_by_general_user', GP_CORRECTION_REGISTRATION_APPLICATION, 'general user', [BASIC_USER], '2022-01-01', timedelta(days=90), True),
                             ('sp_correction_invalid_greater_by_general_user', SP_CORRECTION_REGISTRATION_APPLICATION, 'general user', [BASIC_USER], '2022-01-01', timedelta(days=91), False),
                             ('gp_correction_invalid_greater_by_general_user', GP_CORRECTION_REGISTRATION_APPLICATION, 'general user', [BASIC_USER], '2022-01-01', timedelta(days=91), False),
                             ('sp_correction_lesser_by_general_user', SP_CORRECTION_REGISTRATION_APPLICATION, 'general user', [BASIC_USER], '2022-01-01', relativedelta(years=-10), True),
                             ('gp_correction_lesser_by_general_user', GP_CORRECTION_REGISTRATION_APPLICATION, 'general user', [BASIC_USER], '2022-01-01', relativedelta(years=-10), True),
                             ('sp_correction_invalid_lesser_by_general_user', SP_CORRECTION_REGISTRATION_APPLICATION, 'general user', [BASIC_USER], '2022-01-01', relativedelta(years=-10, days=-1), False),
                             ('gp_correction_invalid_lesser_by_general_user', GP_CORRECTION_REGISTRATION_APPLICATION, 'general user', [BASIC_USER], '2022-01-01', relativedelta(years=-10, days=-1), False),
                         ])
def test_firms_correction_start_date(mocker, app, session, jwt, test_name, filing, username, roles, founding_date_str, delta_date, is_valid):
    """Test that start date of firms is correctly validated."""
    def mock_validate_roles(required_roles):
        if roles in required_roles:
            return True
        return False
    mocker.patch('legal_api.utils.auth.jwt.validate_roles', side_effect=mock_validate_roles)  # Client
    
    identifier = 'FM1234567'
    founding_date = datetime.strptime(founding_date_str, '%Y-%m-%d')
    f = copy.deepcopy(filing)
    legal_type = f['filing']['correction']['nameRequest']['legalType']
    business = factory_business(identifier=identifier, founding_date=founding_date, entity_type=legal_type)

    corrected_filing = factory_completed_filing(business, CHANGE_OF_REGISTRATION_APPLICATION)

    start_date = founding_date
    if delta_date:
        start_date = start_date + delta_date

    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id
    f['filing']['correction']['startDate'] = start_date.strftime('%Y-%m-%d')

    nr_res = copy.deepcopy(nr_response)
    nr_res['legalType'] = legal_type
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_res)):
        with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
            err = validate(business, f)

    if is_valid:
        assert not err
    else:
        assert err