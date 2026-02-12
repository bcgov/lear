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
import datedelta
from datetime import datetime, timezone
from freezegun import freeze_time
from http import HTTPStatus
from unittest.mock import patch

import pytest
from registry_schemas.example_data import CORRECTION_INCORPORATION, INCORPORATION_FILING_TEMPLATE

from legal_api.services import NameXService
from legal_api.services.filings import validate
from tests.unit import MockResponse
from tests.unit.models import factory_business, factory_completed_filing
from tests.unit.services.filings.validations import lists_are_equal


INCORPORATION_APPLICATION = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
CORRECTION = copy.deepcopy(CORRECTION_INCORPORATION)

BC_COMMENT_ONLY_CORRECTION = {
    'filing': {
        'header': {
            'name': 'correction',
            'date': '2025-01-01',
            'certifiedBy': 'system'
        },
        'business': {
            'identifier': 'BC1234567',
            'legalType': 'BC'
        },
        'correction': {
            'details': 'First correction',
            'correctedFilingId': '123456',
            'correctedFilingType': 'incorporationApplication',
            'comment': 'Correction for Incorporation Application filed on 2025-01-01 by system',
            'commentOnly': True
        }
    }
}


def test_valid_ia_correction(mocker, session):
    """Test that a valid IA without NR correction passes validation."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier)

    corrected_filing = factory_completed_filing(business, INCORPORATION_APPLICATION)

    f = copy.deepcopy(CORRECTION)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id

    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=True)

    err = validate(business, f)

    if err:
        print(err.msg)

    # check that validation passed
    assert None is err


@pytest.mark.parametrize('new_name, legal_type, nr_legal_type, nr_type, err_msg', [
    ('legal_name-BC1234568', 'CP', 'CP', 'BECV', None),
    ('legal_name-BC1234567_Changed', 'BEN', 'CP', 'BECV',
     'Name Request legal type is not same as the business legal type.'),
    ('nr_not_approved', 'BEN', 'CP', 'BECV', 'Name Request is not approved.')
])
def test_nr_correction(mocker, session, new_name, legal_type, nr_legal_type, nr_type, err_msg):
    """Test that a valid NR correction passes validation."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type=legal_type)

    INCORPORATION_APPLICATION['filing']['incorporationApplication']['nameRequest']['nrNumber'] = identifier
    INCORPORATION_APPLICATION['filing']['incorporationApplication']['nameRequest']['legalName'] = 'Test'

    corrected_filing = factory_completed_filing(business, INCORPORATION_APPLICATION)

    f = copy.deepcopy(CORRECTION)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id

    f['filing']['correction']['nameRequest']['nrNumber'] = identifier
    f['filing']['correction']['nameRequest']['legalName'] = new_name
    f['filing']['correction']['nameRequest']['legalType'] = legal_type
    f['filing']['business']['legalType'] = legal_type
    del f['filing']['correction']['commentOnly']

    nr_response_json = {
        'state': 'INPROGRESS' if new_name == 'nr_not_approved' else 'APPROVED',
        'expirationDate': '',
        'legalType': nr_legal_type,
        'names': [{
            'name': new_name,
            'state': 'INPROGRESS' if new_name == 'nr_not_approved' else 'APPROVED',
            'consumptionDate': ''
        }]
    }
    nr_response = MockResponse(nr_response_json)

    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=True)

    with patch.object(NameXService, 'query_nr_number', return_value=nr_response):
        err = validate(business, f)
        if err:
            print(err.msg)

    if not err_msg:
        assert None is err
    else:
        assert err
        assert HTTPStatus.BAD_REQUEST == err.code
        assert err.msg[0]['error'] == err_msg


@pytest.mark.parametrize('test_name, legal_type, correction_type, err_msg', [
    ('valid_parties', 'BEN', 'CLIENT', None),
    ('valid_parties', 'BC', 'CLIENT', None),
    ('valid_parties', 'ULC', 'CLIENT', None),
    ('valid_parties', 'CC', 'CLIENT', None),
    ('valid_parties', 'BEN', 'STAFF', None),
    ('valid_parties', 'BC', 'STAFF', None),
    ('valid_parties', 'ULC', 'STAFF', None),
    ('valid_parties', 'CC', 'STAFF', None),

    ('no_roles', 'BC', 'CLIENT',
     [{'error': 'Must have a minimum of one completing party', 'path': '/filing/correction/parties/roles'}]),
    ('no_roles', 'ULC', 'CLIENT',
     [{'error': 'Must have a minimum of one completing party', 'path': '/filing/correction/parties/roles'}]),
    ('no_roles', 'CC', 'CLIENT',
     [{'error': 'Must have a minimum of one completing party', 'path': '/filing/correction/parties/roles'}]),
    ('no_roles', 'BEN', 'CLIENT',
     [{'error': 'Must have a minimum of one completing party', 'path': '/filing/correction/parties/roles'}]),
    ('no_roles', 'BEN', 'STAFF', None),
    ('no_roles', 'BC', 'STAFF', None),
    ('no_roles', 'ULC', 'STAFF', None),
    ('no_roles', 'CC', 'STAFF', None),
])
def test_parties_correction(mocker, session, test_name, legal_type, correction_type, err_msg):
    """Test that a valid NR correction passes validation."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type=legal_type)

    INCORPORATION_APPLICATION['filing']['incorporationApplication']['nameRequest']['nrNumber'] = identifier
    INCORPORATION_APPLICATION['filing']['incorporationApplication']['nameRequest']['legalName'] = 'Test'

    corrected_filing = factory_completed_filing(business, INCORPORATION_APPLICATION)

    f = copy.deepcopy(CORRECTION)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id
    f['filing']['correction']['type'] = correction_type

    f['filing']['correction']['nameRequest']['nrNumber'] = identifier
    f['filing']['correction']['nameRequest']['legalName'] = 'test'
    f['filing']['correction']['nameRequest']['legalType'] = legal_type
    f['filing']['business']['legalType'] = legal_type
    del f['filing']['correction']['commentOnly']

    if test_name == 'no_roles':
        f['filing']['correction']['parties'][0]['roles'] = []
    elif test_name == 'valid_parties':
        if legal_type == 'CC':
            director = copy.deepcopy(f['filing']['correction']['parties'][0])
            del director['roles'][0]  # completing party
            f['filing']['correction']['parties'].append(director)
            f['filing']['correction']['parties'].append(director)

        if correction_type == 'STAFF':
            del f['filing']['correction']['parties'][0]['roles'][0]  # completing party

    nr_response_json = {
        'state': 'APPROVED',
        'expirationDate': '',
        'legalType': legal_type,
        'names': [{
            'name': 'test',
            'state': 'APPROVED',
            'consumptionDate': ''
        }]
    }
    nr_response = MockResponse(nr_response_json)

    if correction_type == 'CLIENT':
        mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=False)
    else:
        mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=True)

    with patch.object(NameXService, 'query_nr_number', return_value=nr_response):
        err = validate(business, f)
        if err:
            print(err.msg)

    if err_msg:
        assert err
        assert HTTPStatus.BAD_REQUEST == err.code
        assert lists_are_equal(err.msg, err_msg)
    else:
        assert None is err


@pytest.mark.parametrize('correction_type, err_msg', [
    ('STAFF', None),
    ('CLIENT', 'Only staff can file comment only Corrections.')
])
def test_valid_comment_only_correction(mocker, session, correction_type, err_msg):
    """Test valid comment only IA validation."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier)

    corrected_filing = factory_completed_filing(business, INCORPORATION_APPLICATION)

    f = copy.deepcopy(BC_COMMENT_ONLY_CORRECTION)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id

    if correction_type == 'CLIENT':
        mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=False)
    else:
        mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=True)

    err = validate(business, f)

    if err:
        print(err.msg)

    if not err_msg:
        assert None is err
    else:
        assert err
        assert HTTPStatus.BAD_REQUEST == err.code
        assert err.msg[0]['error'] == err_msg


@pytest.mark.parametrize(
    'legal_type, has_rights_or_restrictions, has_series, should_pass',
    [
        ('BC', False, True, False),
        ('BC', False, False, True),
        ('BC', True, True, True),
        ('BC', True, False, True),
        ('ULC', False, True, False),
        ('ULC', False, False, True),
        ('ULC', True, True, True),
        ('ULC', True, False, True),
        ('CC', False, True, False),
        ('CC', False, False, True),
        ('CC', True, True, True),
        ('CC', True, False, True),
        ('BEN', False, True, False),
        ('BEN', False, False, True),
        ('BEN', True, True, True),
        ('BEN', True, False, True),
    ]
)
def test_correction_share_class_series_validation(mocker, session, legal_type, has_rights_or_restrictions,
                                                  has_series, should_pass):
    """Test share class/series validation in correction filing."""
    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=False)
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type=legal_type)
    corrected_filing = factory_completed_filing(business, INCORPORATION_APPLICATION)

    filing = copy.deepcopy(CORRECTION)
    filing['filing']['header']['identifier'] = identifier
    filing['filing']['correction']['correctedFilingId'] = corrected_filing.id
    filing['filing']['business']['legalType'] = legal_type
    del filing['filing']['correction']['commentOnly']

    if legal_type == 'CC':
        director = copy.deepcopy(filing['filing']['correction']['parties'][0])
        del director['roles'][0]
        filing['filing']['correction']['parties'].append(director)
        filing['filing']['correction']['parties'].append(director)

    for share_class in filing['filing']['correction']['shareStructure']['shareClasses']:
        share_class['hasRightsOrRestrictions'] = has_rights_or_restrictions
        if not has_rights_or_restrictions:
            if not has_series:
                share_class.pop('series', None)

    err = validate(business, filing)

    if should_pass:
        assert err is None
    else:
        assert err
        assert any('cannot have series when hasRightsOrRestrictions is false' in msg['error'] for msg in err.msg)

NOW = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
FOUNDING_DATE = NOW - datedelta.YEAR

@pytest.mark.parametrize(
    'test_name, has_rights_or_restrictions, has_series, resolution_dates, expected_code, expected_msg',
    [
        ('SUCCESS_class_has_rights', True, False, ['2024-01-01'], None, None),
        ('SUCCESS_class_no_rights', False, False, [], None, None),
        ('SUCCESS_series_has_rights', True, True, ['2024-01-01'], None, None),
        ('SUCCESS_series_no_rights', False, False, [], None, None),

        ('FAILURE_class_missing_date', True, False, [], HTTPStatus.BAD_REQUEST, [
            {'error': 'Resolution date is required when hasRightsOrRestrictions is true.',
             'path': '/filing/correction/shareStructure/resolutionDates'}
        ]),
        ('FAILURE_series_missing_date', False, True, [], HTTPStatus.BAD_REQUEST, [
            {'error': 'Resolution date is required when hasRightsOrRestrictions is true.',
             'path': '/filing/correction/shareStructure/resolutionDates'}
        ]),

        ('FAILURE_too_many_dates', True, False, ['2024-01-01', '2024-02-01'], HTTPStatus.BAD_REQUEST, [
            {'error': 'Only one resolution date is permitted.',
             'path': '/filing/correction/shareStructure/resolutionDates'}
        ]),

        ('FAILURE_future_date', True, False, [(NOW + datedelta.DAY).date().isoformat()], HTTPStatus.BAD_REQUEST, [
            {'error': 'Resolution date cannot be in the future.',
             'path': '/filing/correction/shareStructure/resolutionDates'}
        ]),

        ('FAILURE_before_founding', True, False, [(FOUNDING_DATE - datedelta.DAY).date().isoformat()], HTTPStatus.BAD_REQUEST, [
            {'error': 'Resolution date cannot be before the business founding date.',
             'path': '/filing/correction/shareStructure/resolutionDates'}
        ]),
    ]
)
def test_correction_resolution_date(mocker, session, test_name, has_rights_or_restrictions,
                                    has_series, resolution_dates, expected_code, expected_msg):
    """Test share class/series resolution date validation in correction filings."""
    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=False)
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type='BC')
    business.founding_date = FOUNDING_DATE

    corrected_filing = factory_completed_filing(business, INCORPORATION_APPLICATION)

    filing = copy.deepcopy(CORRECTION)
    filing['filing']['header']['identifier'] = identifier
    filing['filing']['correction']['correctedFilingId'] = corrected_filing.id
    del filing['filing']['correction']['commentOnly']

    # Share structure setup
    filing['filing']['correction']['shareStructure'] = copy.deepcopy(
        INCORPORATION_FILING_TEMPLATE['filing']['incorporationApplication'].get('shareStructure', {})
    )
    share_class = filing['filing']['correction']['shareStructure']['shareClasses'][0]
    share_class['hasRightsOrRestrictions'] = has_rights_or_restrictions

    # Series handling
    if has_series:
        share_class['series'] = share_class.get('series', [{}])
        share_class['series'][0]['hasRightsOrRestrictions'] = True
    else:
        share_class.pop('series', None)

    filing['filing']['correction']['shareStructure']['resolutionDates'] = resolution_dates

    # Remove the second share class if it exists
    share_classes = filing['filing']['correction']['shareStructure']['shareClasses']
    if len(share_classes) > 1:
        share_classes.pop(1)

    with freeze_time(NOW):
        err = validate(business, filing)

    if expected_code:
        assert err
        assert any(expected_msg[0]['error'] in e['error'] for e in err.msg)
    else:
        assert err is None
