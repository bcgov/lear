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
import pycountry
from datetime import datetime, timezone
from freezegun import freeze_time
from http import HTTPStatus
from unittest.mock import patch

import pytest

from business_model.models import AmalgamatingBusiness, Amalgamation, Business, CourtOrder, Resolution
from business_common.utils.legislation_datetime import LegislationDatetime
from business_common.utils.datetime import datetime as dt, timedelta
from legal_api.services import NameXService
from legal_api.services.authz import BASIC_USER, STAFF_ROLE
from legal_api.services.filings import validate
from registry_schemas.example_data import (
    AMALGAMATION_APPLICATION,
    AMALGAMATION_OUT,
    CORRECTION_INCORPORATION,
    CONTINUATION_IN_FILING_TEMPLATE,
    CONTINUATION_OUT,
    COURT_ORDER_FILING_TEMPLATE,
    FILING_HEADER,
    INCORPORATION_FILING_TEMPLATE
)

from tests.unit import MockResponse
from tests.unit.models import factory_business, factory_completed_filing
from tests.unit.services.filings.validations import lists_are_equal
from tests.unit.services.utils import jwt_request_context


date_format = '%Y-%m-%d'
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


def test_valid_ia_correction(session, app, jwt):
    """Test that a valid IA without NR correction passes validation."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier)

    corrected_filing = factory_completed_filing(business, INCORPORATION_APPLICATION)

    f = copy.deepcopy(CORRECTION)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id

    with jwt_request_context(app, jwt, [STAFF_ROLE]):
        if err := validate(business, f):
            print(err.msg)

    # check that validation passed
    assert None is err


@pytest.mark.parametrize('new_name, legal_type, nr_legal_type, nr_type, err_msg', [
    ('legal_name-BC1234568', 'CP', 'CP', 'BECV', None),
    ('legal_name-BC1234567_Changed', 'BEN', 'CP', 'BECV',
     'Name Request legal type is not same as the business legal type.'),
    ('nr_not_approved', 'BEN', 'CP', 'BECV', 'Name Request is not approved.')
])
def test_nr_correction(session, app, jwt, new_name, legal_type, nr_legal_type, nr_type, err_msg):
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

    with patch.object(NameXService, 'query_nr_number', return_value=nr_response):
        with jwt_request_context(app, jwt, [STAFF_ROLE]):
            if err := validate(business, f):
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
def test_parties_correction(session, app, jwt, test_name, legal_type, correction_type, err_msg):
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

    roles = [BASIC_USER] if correction_type == 'CLIENT' else [STAFF_ROLE]

    with patch.object(NameXService, 'query_nr_number', return_value=nr_response):
        with jwt_request_context(app, jwt, roles):
            if err := validate(business, f):
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
def test_valid_comment_only_correction(session, app, jwt, correction_type, err_msg):
    """Test valid comment only IA validation."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier)

    corrected_filing = factory_completed_filing(business, INCORPORATION_APPLICATION)

    f = copy.deepcopy(BC_COMMENT_ONLY_CORRECTION)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id

    roles = [BASIC_USER] if correction_type == 'CLIENT' else [STAFF_ROLE]
    with jwt_request_context(app, jwt, roles):
        if err := validate(business, f):
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
def test_correction_share_class_series_validation(session, app, jwt, legal_type, has_rights_or_restrictions,
                                                  has_series, should_pass):
    """Test share class/series validation in correction filing."""
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

    with jwt_request_context(app, jwt, [BASIC_USER]):
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
def test_correction_resolution_date_old(session, app, jwt, test_name, has_rights_or_restrictions,
                                    has_series, resolution_dates, expected_code, expected_msg):
    """Test share class/series resolution date validation in correction filings."""
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
        with jwt_request_context(app, jwt, [BASIC_USER]):
            err = validate(business, filing)

    if expected_code:
        assert err
        assert any(expected_msg[0]['error'] in e['error'] for e in err.msg)
    else:
        assert err is None


@pytest.mark.parametrize(
    'test_name, has_rights_or_restrictions, has_series, resolution_dates, expected_code, expected_msg',
    [
        ('SUCCESS_class_has_rights', True, False, [{'date':'2024-01-01'}], None, None),
        ('SUCCESS_class_no_rights', False, False, [], None, None),
        ('SUCCESS_series_has_rights', True, True, [{'date':'2024-01-01'}], None, None),
        ('SUCCESS_series_no_rights', False, False, [], None, None),
        ('SUCCESS_existing_resolution', True, False, [{'date':'2024-01-01'}], None, None),

        ('FAILURE_class_missing_date', True, False, [], HTTPStatus.BAD_REQUEST, [
            {'error': 'Resolution date is required when hasRightsOrRestrictions is true.',
             'path': '/filing/correction/shareStructure/resolutionDates'}
        ]),
        ('FAILURE_series_missing_date', False, True, [], HTTPStatus.BAD_REQUEST, [
            {'error': 'Resolution date is required when hasRightsOrRestrictions is true.',
             'path': '/filing/correction/shareStructure/resolutionDates'}
        ]),

        ('FAILURE_future_date', True, False, [{'date': (NOW + datedelta.DAY).date().isoformat()}], HTTPStatus.BAD_REQUEST, [
            {'error': 'Resolution date cannot be in the future.',
             'path': '/filing/correction/shareStructure/resolutionDates'}
        ]),

        ('FAILURE_before_founding', True, False, [{'date': (FOUNDING_DATE - datedelta.DAY).date().isoformat()}], HTTPStatus.BAD_REQUEST, [
            {'error': 'Resolution date cannot be before the business founding date.',
             'path': '/filing/correction/shareStructure/resolutionDates'}
        ]),
        
        ('FAILURE_invalid_resolution_id', True, False, [{'id': 9999999, 'date': '2024-01-01'}], HTTPStatus.BAD_REQUEST, [
            {'error': 'Not a valid Resolution Id for this business.',
             'path': '/filing/correction/shareStructure/resolutionDates/0'}
        ]),
    ]
)
def test_correction_resolution_date(session, app, jwt, test_name, has_rights_or_restrictions,
                                    has_series, resolution_dates, expected_code, expected_msg):
    """Test share class/series resolution date validation in correction filings."""
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

    if test_name == "SUCCESS_existing_resolution":
        res_obj = Resolution()
        res_obj.resolution_date=datetime.fromisoformat(resolution_dates[0]["date"])
        res_obj.business_id = business.id
        res_obj.resolution_type = Resolution.ResolutionType.SPECIAL.value
        res_obj.save()
        resolution_dates[0]["id"] = res_obj.id

    filing['filing']['correction']['shareStructure']['resolutionDates'] = resolution_dates

    # Remove the second share class if it exists
    share_classes = filing['filing']['correction']['shareStructure']['shareClasses']
    if len(share_classes) > 1:
        share_classes.pop(1)

    with freeze_time(NOW):
        with jwt_request_context(app, jwt, [BASIC_USER]):
            err = validate(business, filing)

    if expected_code:
        assert err
        assert any(expected_msg[0]['error'] in e['error'] for e in err.msg)
    else:
        assert err is None


@pytest.mark.parametrize(
    'use_nr, new_name, legal_type, new_legal_type, nr_type, mock_directors, should_pass, num_errors', [
    (False, '', 'BEN', 'BEN', '', True, False, 1),
    (False, '', 'BEN', 'BC', '', True, True, 0),
    (False, '', 'BEN', 'ULC', '', True, False, 1),
    (False, '', 'BEN', 'CC', '', True, True, 1),
    (False, '', 'BEN', 'CP', '', True, False, 1),
    (False, '', 'BEN', 'C', '', True, False, 1),
    (False, '', 'BEN', 'CBEN', '', True, False, 1),
    (False, '', 'BEN', 'CUL', '', True, False, 1),
    (False, '', 'BEN', 'CCC', '', True, False, 1),

    (False, '', 'BC', 'BC', '', True, False, 1),
    (False, '', 'BC', 'BEN', '', True, True, 0),
    (False, '', 'BC', 'ULC', '', True, True, 0),
    (False, '', 'BC', 'CC', '', True, True, 0),
    (False, '', 'BC', 'CP', '', True, False, 1),
    (False, '', 'BC', 'C', '', True, False, 1),
    (False, '', 'BC', 'CBEN', '', True, False, 1),
    (False, '', 'BC', 'CUL', '', True, False, 1),
    (False, '', 'BC', 'CCC', '', True, False, 1),

    (False, '', 'ULC', 'ULC', '', True, False, 1),
    (False, '', 'ULC', 'BC', '', True, True, 0),
    (False, '', 'ULC', 'BEN', '', True, True, 0),
    (False, '', 'ULC', 'CC', '', True, False, 1),
    (False, '', 'ULC', 'CP', '', True, False, 1),
    (False, '', 'ULC', 'C', '', True, False, 1),
    (False, '', 'ULC', 'CBEN', '', True, False, 1),
    (False, '', 'ULC', 'CUL', '', True, False, 1),
    (False, '', 'ULC', 'CCC', '', True, False, 1),

    (False, '', 'CC', 'CC', '', True, False, 1),
    (False, '', 'CC', 'BEN', '', True, False, 1),
    (False, '', 'CC', 'BC', '', True, False, 1),
    (False, '', 'CC', 'ULC', '', True, False, 1),
    (False, '', 'CC', 'CP', '', True, False, 1),
    (False, '', 'CC', 'C', '', True, False, 1),
    (False, '', 'CC', 'CBEN', '', True, False, 1),
    (False, '', 'CC', 'CUL', '', True, False, 1),
    (False, '', 'CC', 'CCC', '', True, False, 1),

    (False, '', 'CBEN', 'CBEN', '', True, False, 1),
    (False, '', 'CBEN', 'C', '', True, True, 0),
    (False, '', 'CBEN', 'CUL', '', True, False, 1),
    (False, '', 'CBEN', 'CCC', '', True, True, 1),
    (False, '', 'CBEN', 'BEN', '', True, False, 1),
    (False, '', 'CBEN', 'BC', '', True, False, 1),
    (False, '', 'CBEN', 'ULC', '', True, False, 1),
    (False, '', 'CBEN', 'CC', '', True, False, 1),
    (False, '', 'CBEN', 'CP', '', True, False, 1),

    (False, '', 'C', 'C', '', True, False, 1),
    (False, '', 'C', 'CBEN', '', True, True, 0),
    (False, '', 'C', 'CUL', '', True, True, 0),
    (False, '', 'C', 'CCC', '', True, True, 0),
    (False, '', 'C', 'BC', '', True, False, 1),
    (False, '', 'C', 'BEN', '', True, False, 1),
    (False, '', 'C', 'ULC', '', True, False, 1),
    (False, '', 'C', 'CC', '', True, False, 1),
    (False, '', 'C', 'CP', '', True, False, 1),

    (False, '', 'CUL', 'CUL', '', True, False, 1),
    (False, '', 'CUL', 'C', '', True, True, 0),
    (False, '', 'CUL', 'CBEN', '', True, True, 0),
    (False, '', 'CUL', 'CCC', '', True, False, 1),
    (False, '', 'CUL', 'ULC', '', True, False, 1),
    (False, '', 'CUL', 'BC', '', True, False, 1),
    (False, '', 'CUL', 'BEN', '', True, False, 1),
    (False, '', 'CUL', 'CC', '', True, False, 1),
    (False, '', 'CUL', 'CP', '', True, False, 1),

    (False, '', 'CCC', 'CCC', '', True, False, 1),
    (False, '', 'CCC', 'CBEN', '', True, False, 1),
    (False, '', 'CCC', 'C', '', True, False, 1),
    (False, '', 'CCC', 'CUL', '', True, False, 1),
    (False, '', 'CCC', 'CC', '', True, False, 1),
    (False, '', 'CCC', 'BEN', '', True, False, 1),
    (False, '', 'CCC', 'BC', '', True, False, 1),
    (False, '', 'CCC', 'ULC', '', True, False, 1),
    (False, '', 'CCC', 'CP', '', True, False, 1),

    # check minimum directors validation
    (False, '', 'BC', 'CC', '', False, False, 1),
    (False, '', 'CBEN', 'CCC', '', False, False, 1)
])
@patch('business_model.models.PartyRole.get_parties_by_role')
def test_new_legal_type(mock_get_parties, session, app, jwt, use_nr, new_name, legal_type, new_legal_type, nr_type, mock_directors, should_pass, num_errors):
    """Test that a valid Alteration without NR correction passes validation."""
    # setup
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type=legal_type)

    corrected_filing = factory_completed_filing(business, INCORPORATION_APPLICATION)

    filing = copy.deepcopy(CORRECTION)
    filing['filing']['header']['identifier'] = identifier
    filing['filing']['correction']['correctedFilingId'] = corrected_filing.id
    del filing['filing']['correction']['commentOnly']

    filing['filing']['correction']['newLegalType'] = new_legal_type

    class MockDirector:
        def __init__(self, cessation_date=None):
            self.cessation_date = cessation_date

    def create_mock_directors(count=3):
        """Return a list of mock directors for tests."""
        return [MockDirector() for _ in range(count)]  

    # mock directors
    if mock_directors:
        mock_get_parties.return_value = create_mock_directors(3)
    else:
        mock_get_parties.return_value = []

    if use_nr:
        filing['filing']['business']['identifier'] = identifier
        filing['filing']['business']['legalName'] = 'legal_name-BC1234567'
        filing['filing']['business']['legalType'] = legal_type

        filing['filing']['correction']['nameRequest']['nrNumber'] = identifier
        filing['filing']['correction']['nameRequest']['legalName'] = new_name
        filing['filing']['correction']['nameRequest']['legalType'] = new_legal_type

        nr_json = {
            "state": "APPROVED",
            "expirationDate": "",
            "requestTypeCd": nr_type,
            "names": [{
                "name": new_name,
                "state": "APPROVED",
                "consumptionDate": ""
            }],
            "legalType": new_legal_type
        }

        nr_response = MockResponse(nr_json)
        with patch.object(NameXService, 'query_nr_number', return_value=nr_response):
            with jwt_request_context(app, jwt, [BASIC_USER]):
                err = validate(business, filing)
    else:
        del filing['filing']['correction']['nameRequest']
        with jwt_request_context(app, jwt, [BASIC_USER]):
            err = validate(business, filing)

    if err:
        print(err.msg)

    if should_pass:
        # check that validation passed
        assert None is err
    else:
        # check that validation failed
        assert err
        assert HTTPStatus.BAD_REQUEST == err.code
        assert len(err.msg) == num_errors

        # check for minimum directors error message
        if (new_legal_type in [Business.LegalTypes.BC_CCC.value, Business.LegalTypes.CCC_CONTINUE_IN.value,
                               Business.LegalTypes.COOP.value] and not mock_directors):
            assert 'Must have a minimum of three directors. File a change of director filing first.' in [e['error'] for e in err.msg]


def test_validate_correction_continuation_in_incorporation_date(mocker, app, session, jwt):
    """Assert that an error is raised if the correction continuation_in incorporation date is set to a future date."""
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type='C')
    corrected_filing = factory_completed_filing(business, CONTINUATION_IN_FILING_TEMPLATE)

    filing = copy.deepcopy(CORRECTION)
    filing['filing']['header']['identifier'] = identifier
    filing['filing']['correction']['correctedFilingId'] = corrected_filing.id

    filing['filing']['correction']['correctedFilingType'] = 'continuationIn'
    future_date = (dt.now() + timedelta(days=1)).date().isoformat()  # Set date to tomorrow
    filing['filing']['correction']['continuationIn'] = {
        'country': 'CA',
        'region': 'AB',
        'legalName': 'HAULER SERVICES',
        'identifier': 'AB1234567',
        'incorporationDate': future_date
    }
    filing['filing']['business']['legalType'] = 'C'
    del filing['filing']['correction']['commentOnly']


    with jwt_request_context(app, jwt, [BASIC_USER]):
        err = validate(business, filing)

    # Assert that the error list contains the appropriate error for future incorporation date
    assert len(err.msg) == 1
    assert err.msg[0]['error'] == 'Incorporation date cannot be in the future.'
    assert err.msg[0]['path'] == '/filing/correction/continuationIn/incorporationDate'


@pytest.mark.parametrize(
    'test_name, identifier, legal_name, expected_errors',
    [
        (
            'SUCCESS',
            'C1234567',
            'Test',
            []
        ),
        (
            'SUCCESS_IDENTIFIER_AT_MAX_LENGTH',
            'A' * 50,
            'Test',
            []
        ),
        (
            'SUCCESS_LEGAL_NAME_AT_MAX_LENGTH',
            'C1234567',
            'A' * 1000,
            []
        ),
        (
            'FAIL_IDENTIFIER_EXCEEDS_MAX_LENGTH',
            'A' * 51,
            'Test',
            [
                {
                    'error': 'Identifier must not exceed 50 characters.',
                    'path': '/filing/correction/continuationIn/identifier'
                }
            ]
        ),
        (
            'FAIL_LEGAL_NAME_EXCEEDS_MAX_LENGTH',
            'C1234567',
            'A' * 1001,
            [
                {
                    'error': 'Legal name must not exceed 1000 characters.',
                    'path': '/filing/correction/continuationIn/legalName'
                }
            ]
        ),
        (
            'FAIL_BOTH_EXCEED_MAX_LENGTH',
            'A' * 51,
            'A' * 1001,
            [
                {
                    'error': 'Identifier must not exceed 50 characters.',
                    'path': '/filing/correction/continuationIn/identifier'
                },
                {
                    'error': 'Legal name must not exceed 1000 characters.',
                    'path': '/filing/correction/continuationIn/legalName'
                }
            ]
        ),
    ]
)
def test_validate_continuation_in_field_lengths(mocker, app, session, jwt,
                                                     test_name, identifier, legal_name, expected_errors):
    """Assert that identifier and legalName enforce max length for continuation in filings.

    The required (non-empty / non-whitespace) rule for these fields now lives in the schema;
    see test_continuation_in_foreign_jurisdiction_name_rejected_by_schema.
    """
    _identifier = 'BC1234567'
    business = factory_business(_identifier, entity_type='C')
    corrected_filing = factory_completed_filing(business, CONTINUATION_IN_FILING_TEMPLATE)

    filing = copy.deepcopy(CORRECTION)
    filing['filing']['header']['identifier'] = _identifier
    filing['filing']['correction']['correctedFilingId'] = corrected_filing.id
    filing['filing']['correction']['correctedFilingType'] = 'continuationIn'
    continuation_in = {
        'country': 'US',
        'region': 'WA',
        'legalName': 'HAULER SERVICES',
        'incorporationDate': dt.now().date().isoformat()
    }
    filing['filing']['business']['legalType'] = 'C'
    del filing['filing']['correction']['commentOnly']

    if identifier is not None:
        continuation_in['identifier'] = identifier

    if legal_name is not None:
        continuation_in['legalName'] = legal_name

    filing['filing']['correction']['continuationIn'] = continuation_in
    with jwt_request_context(app, jwt, [BASIC_USER]):
        err = validate(business, filing)

    if expected_errors:
        assert err.msg == expected_errors
    else:
        assert err is None


def test_validate_continuation_in_expro_founding_date_match(mocker, app, session, jwt):
    """Assert continuation EXPRO business with matching founding date."""
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type='C')
    corrected_filing = factory_completed_filing(business, CONTINUATION_IN_FILING_TEMPLATE)

    filing = copy.deepcopy(CORRECTION)
    filing['filing']['header']['identifier'] = identifier
    filing['filing']['correction']['correctedFilingId'] = corrected_filing.id
    filing['filing']['correction']['correctedFilingType'] = 'continuationIn'
    filing['filing']['correction']['continuationIn'] = {
        'country': 'CA',
        'region': 'AB',
        'legalName': 'HAULER SERVICES',
        'identifier': 'AB1234567',
        'incorporationDate': dt.now().date().isoformat(),
        'expro': {
            'identifier': 'A0077779',
            'legalName': 'Test Company Inc.'
        }
    }
    filing['filing']['business']['legalType'] = 'C'
    del filing['filing']['correction']['commentOnly']

    mocker.patch('legal_api.services.filings.validations.continuation_in.colin.query_business', return_value=(
        {
            'business': {
                'identifier': 'A0077779',
                'legalName': 'Test Company Inc.'
            }
        },
        HTTPStatus.OK
    ))

    with jwt_request_context(app, jwt, [BASIC_USER]):
        err = validate(business, filing)
    assert not err


@pytest.mark.parametrize('filing_type', ['continuationOut', 'amalgamationOut'])
@pytest.mark.parametrize(
    'test_name, expected_code, message',
    [
        ('FAIL_IN_FUTURE', HTTPStatus.BAD_REQUEST, '{0} out date must be today or past.'),
        ('SUCCESS_NO_CCO', None, None),
        ('SUCCESS', None, None)
    ]
)
def test_validate_continuation_out_date(session, app, jwt, filing_type, test_name, expected_code, message):
    """Assert validate continuation_out_date."""
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type='BC')
    continuation_out_filing = copy.deepcopy(FILING_HEADER)
    continuation_out_filing['filing'][filing_type] = copy.deepcopy(CONTINUATION_OUT if filing_type == 'continuationOut' else AMALGAMATION_OUT)
    continuation_out_filing['filing']['header']['name'] = filing_type

    corrected_filing = factory_completed_filing(business, continuation_out_filing)


    filing = copy.deepcopy(CORRECTION)
    filing['filing']['header']['identifier'] = identifier
    filing['filing']['correction']['correctedFilingId'] = corrected_filing.id
    filing['filing']['correction']['correctedFilingType'] = filing_type
    filing['filing']['correction'][filing_type] = {
        'country': 'CA',
        'region': 'AB',
        'legalName': 'HAULER SERVICES',
        'date': '2023-06-19'
    }
    del filing['filing']['correction']['commentOnly']

    if test_name == 'FAIL_IN_FUTURE':
        filing['filing']['correction'][filing_type]['date'] = \
            (LegislationDatetime.now() + datedelta.datedelta(days=1)).strftime(date_format)

    with jwt_request_context(app, jwt, [BASIC_USER]):
        err = validate(business, filing)

    # validate outcomes
    if test_name == 'FAIL_IN_FUTURE':
        assert expected_code == err.code
        assert message.format(filing_type.replace('Out', '').capitalize()) == err.msg[0]['error']
    else:
        assert not err


@pytest.mark.parametrize('filing_type', ['continuationOut', 'amalgamationOut'])
@pytest.mark.parametrize(
    'test_name, expected_code, message',
    [
        ('FAIL_NO_COUNTRY', HTTPStatus.UNPROCESSABLE_ENTITY, None),
        ('FAIL_INVALID_COUNTRY', HTTPStatus.BAD_REQUEST, 'Invalid country.'),
        ('FAIL_REGION_BC', HTTPStatus.BAD_REQUEST, 'Region should not be BC.'),
        ('FAIL_INVALID_REGION', HTTPStatus.BAD_REQUEST, 'Invalid region.'),
        ('FAIL_INVALID_US_REGION', HTTPStatus.BAD_REQUEST, 'Invalid region.'),
        ('SUCCESS', None, None)
    ]
)
def test_validate_continuation_out_foreign_jurisdiction(session, app, jwt, filing_type, test_name, expected_code, message):
    """Assert validate continuation_out foreign jurisdiction."""
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type='BC')
    continuation_out_filing = copy.deepcopy(FILING_HEADER)
    continuation_out_filing['filing'][filing_type] = copy.deepcopy(CONTINUATION_OUT if filing_type == 'continuationOut' else AMALGAMATION_OUT)
    continuation_out_filing['filing']['header']['name'] = filing_type

    corrected_filing = factory_completed_filing(business, continuation_out_filing)

    filing = copy.deepcopy(CORRECTION)
    filing['filing']['header']['identifier'] = identifier
    filing['filing']['correction']['correctedFilingId'] = corrected_filing.id
    filing['filing']['correction']['correctedFilingType'] = filing_type
    filing['filing']['correction'][filing_type] = {
        'country': 'CA',
        'region': 'AB',
        'legalName': 'HAULER SERVICES',
        'date': '2023-06-19'
    }
    del filing['filing']['correction']['commentOnly']


    if test_name == 'FAIL_NO_COUNTRY':
        del filing['filing']['correction'][filing_type]['country']
    elif test_name == 'FAIL_INVALID_COUNTRY':
        filing['filing']['correction'][filing_type]['country'] = 'NONE'
    elif test_name == 'FAIL_REGION_BC':
        filing['filing']['correction'][filing_type]['region'] = 'BC'
    elif test_name == 'FAIL_INVALID_REGION':
        filing['filing']['correction'][filing_type]['region'] = 'NONE'
    elif test_name == 'FAIL_INVALID_US_REGION':
        filing['filing']['correction'][filing_type]['country'] = 'US'
        filing['filing']['correction'][filing_type]['region'] = 'NONE'

    with jwt_request_context(app, jwt, [BASIC_USER]):
        err = validate(business, filing)

    # validate outcomes
    if test_name != 'SUCCESS':
        assert expected_code == err.code
        if message:
            assert message == err.msg[0]['error']
    else:
        assert not err


def test_validate_correction_amalgamation_ting_not_found(mocker, app, session, jwt):
    """Assert that an error is raised if the correction amalgamation filing has an id that doesn't exist"""
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type='BC')
    filing_type = 'amalgamationApplication'
    data, corrected_filing = _create_amalgation_business(business)
    del data['amalgamatingBusinesses'][0]
    data['amalgamatingBusinesses'][0]['id'] = 986546516

    filing = copy.deepcopy(CORRECTION)
    filing['filing']['header']['identifier'] = identifier
    filing['filing']['correction']['correctedFilingId'] = corrected_filing.id

    filing['filing']['correction']['correctedFilingType'] = filing_type
    filing['filing']['correction']['amalgamation'] = data
    filing['filing']['business']['legalType'] = 'BC'
    del filing['filing']['correction']['commentOnly']


    with jwt_request_context(app, jwt, [BASIC_USER]):
        err = validate(business, filing)

    assert len(err.msg) == 1
    assert err.msg[0]['error'] == 'Amalgamating business not found.'
    assert err.msg[0]['path'] == '/filing/correction/amalgamation/amalgamatingBusinesses/0'


@pytest.mark.parametrize(
    'test_name, expected_code, message',
    [
        ('FAIL_NO_COUNTRY', HTTPStatus.UNPROCESSABLE_ENTITY, None),
        ('FAIL_INVALID_COUNTRY', HTTPStatus.BAD_REQUEST, 'Invalid country.'),
        ('FAIL_INVALID_REGION', HTTPStatus.BAD_REQUEST, 'Invalid region.'),
        ('SUCCESS', None, None)
    ]
)
def test_validate_correction_amalgamation_foreign_jurisdiction(mocker, app, session, jwt, test_name, expected_code, message):
    """Assert that an error is raised if the correction amalgamation filing has an invalid business"""
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type='BC')
    filing_type = 'amalgamationApplication'
    data, corrected_filing = _create_amalgation_business(business)
    del data['amalgamatingBusinesses'][0]

    if test_name == 'FAIL_NO_COUNTRY':
        del data['amalgamatingBusinesses'][0]['foreignJurisdiction']['country']
    elif test_name == 'FAIL_INVALID_COUNTRY':
        data['amalgamatingBusinesses'][0]['foreignJurisdiction']['country'] = 'NONE'
    elif test_name == 'FAIL_INVALID_REGION':
        data['amalgamatingBusinesses'][0]['foreignJurisdiction']['region'] = 'NONE'
    elif test_name == 'FAIL_INVALID_US_REGION':
        data['amalgamatingBusinesses'][0]['foreignJurisdiction']['country'] = 'US'
        data['amalgamatingBusinesses'][0]['foreignJurisdiction']['region'] = 'NONE'

    filing = copy.deepcopy(CORRECTION)
    filing['filing']['header']['identifier'] = identifier
    filing['filing']['correction']['correctedFilingId'] = corrected_filing.id

    filing['filing']['correction']['correctedFilingType'] = filing_type
    filing['filing']['correction']['amalgamation'] = data
    filing['filing']['business']['legalType'] = 'BC'
    del filing['filing']['correction']['commentOnly']

    with jwt_request_context(app, jwt, [BASIC_USER]):
        err = validate(business, filing)

    # validate outcomes
    if test_name != 'SUCCESS':
        assert expected_code == err.code
        if message:
            assert message == err.msg[0]['error']
    else:
        assert not err


def test_validate_correction_amalgamation_ting_invalid(mocker, app, session, jwt):
    """Assert that an error is raised if the correction amalgamation filing has an invalid business"""
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type='BC')
    filing_type = 'amalgamationApplication'
    data, corrected_filing = _create_amalgation_business(business)
    data['amalgamatingBusinesses'][0]['foreignJurisdiction'] = {
        'country': 'CA',
        'region': 'AB',
    }
    data['amalgamatingBusinesses'][0]['legalName'] = 'HAULER SERVICES'
    filing = copy.deepcopy(CORRECTION)
    filing['filing']['header']['identifier'] = identifier
    filing['filing']['correction']['correctedFilingId'] = corrected_filing.id

    filing['filing']['correction']['correctedFilingType'] = filing_type
    filing['filing']['correction']['amalgamation'] = data
    filing['filing']['business']['legalType'] = 'BC'
    del filing['filing']['correction']['commentOnly']


    with jwt_request_context(app, jwt, [BASIC_USER]):
        err = validate(business, filing)

    assert len(err.msg) == 1
    assert err.msg[0]['error'] == 'Can only correct foreign businesses.'
    assert err.msg[0]['path'] == '/filing/correction/amalgamation/amalgamatingBusinesses/0'


def _create_amalgation_business(business):
    amalgamating_identifier = 'BC1234567'
    amalgamating_business = factory_business(amalgamating_identifier, entity_type='BC')
    filing_type = "amalgamationApplication"
    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing'][filing_type] = copy.deepcopy(AMALGAMATION_APPLICATION)
    filing_json['filing']['header']['name'] = filing_type

    filing = factory_completed_filing(business, filing_json)
    amalgamating_business_json = [
        {
            'role': 'amalgamating',
            'identifier': amalgamating_identifier
        },
        {
            'role': 'amalgamating',
            'foreignJurisdiction': {
                'country': 'CA',
                'region': 'AB',
            },
            'legalName': 'HAULER SERVICES',
            'identifier': 'AB1234567'
        }
    ]

    data = {
        'courtApproval': False,
        'amalgamatingBusinesses':amalgamating_business_json
    }
    amalgamation = Amalgamation(
        amalgamation_type=Amalgamation.AmalgamationTypes.regular,
        amalgamation_date=LegislationDatetime.now(),
        court_approval=False,
        filing_id=filing.id,
        business_id=business.id,
    )
    amalgamation.amalgamating_businesses.append(AmalgamatingBusiness(
        role=AmalgamatingBusiness.Role.amalgamating,
        business_id=amalgamating_business.id
    ))
    amalgamation.amalgamating_businesses.append(AmalgamatingBusiness(
        role=AmalgamatingBusiness.Role.amalgamating,
        foreign_jurisdiction=amalgamating_business_json[1]['foreignJurisdiction']['country'],
        foreign_jurisdiction_region=amalgamating_business_json[1]['foreignJurisdiction']['region'],
        foreign_name=amalgamating_business_json[1]['legalName'],
        foreign_identifier=amalgamating_business_json[1]['identifier']
    ))
    business.amalgamation.append(amalgamation)
    business.save()
    for ting in amalgamation.amalgamating_businesses.all():
        if ting.business_id:
            amalgamating_business_json[0]['id'] = ting.id
        else:
            amalgamating_business_json[1]['id'] = ting.id
    return data, filing


@pytest.mark.parametrize('invalid_court_order, error_msg', [
    ({
        'fileNumber': '123456789012345678901',  # long fileNumber
        'orderDate': '2021-01-30T09:56:01+01:00',
        'effectOfOrder': 'planOfArrangement'
    }, "'123456789012345678901' is too long"),
    ({
        'orderDate': '2021-01-30T09:56:01+01:00',
        'effectOfOrder': 'planOfArrangement'
    }, "'fileNumber' is a required property"),
    ({
        'fileNumber': 'Valid file number',
        'orderDate': 'a2021-01-30T09:56:01',  # Invalid date
        'effectOfOrder': 'planOfArrangement'
    }, "'a2021-01-30T09:56:01' is not a 'date-time'"),
    ({
        'fileNumber': 'Valid file number',
        'orderDate': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        'effectOfOrder': 'planOfArrangement'
    }, "Court order date cannot be in the future."),
    ({
        'fileNumber': 'Valid File Number',
        'orderDate': '2021-01-30T09:56:01+01:00',
        'effectOfOrder': 'invalid'  # Invalid effectOfOrder
    }, 'Invalid effectOfOrder.')
])
def test_validate_invalid_court_order(app, jwt, session, invalid_court_order, error_msg):
    """Assert not valid court order."""
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type='BC')

    corrected_filing = factory_completed_filing(business, INCORPORATION_APPLICATION)

    filing = copy.deepcopy(CORRECTION)
    filing['filing']['header']['identifier'] = identifier
    filing['filing']['correction']['correctedFilingId'] = corrected_filing.id
    del filing['filing']['correction']['commentOnly']
    filing['filing']['correction']['courtOrder'] = invalid_court_order

    with jwt_request_context(app, jwt, [BASIC_USER]):
        err = validate(business, filing)
    assert err
    assert err.msg[0]['error'] == error_msg


@pytest.mark.parametrize('invalid_court_order, error_msg', [
    ({
        'fileNumber': '123456789012345678901',  # long fileNumber
        'orderDate': '2021-01-30T09:56:01+01:00',
        'effectOfOrder': 'planOfArrangement'
    }, "'123456789012345678901' is too long"),
    ({
        'orderDate': '2021-01-30T09:56:01+01:00',
        'effectOfOrder': 'planOfArrangement'
    }, "'fileNumber' is a required property"),
    ({
        'fileNumber': 'Valid file number',
        'orderDate': 'a2021-01-30T09:56:01',  # Invalid date
        'effectOfOrder': 'planOfArrangement'
    }, "'a2021-01-30T09:56:01' is not a 'date-time'"),
    ({
        'fileNumber': 'Valid file number',
        'orderDate': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        'effectOfOrder': 'planOfArrangement'
    }, "Court order date cannot be in the future."),
    ({
        'fileNumber': 'Valid File Number',
        'orderDate': '2021-01-30T09:56:01+01:00',
        'effectOfOrder': 'invalid'  # Invalid effectOfOrder
    }, 'Invalid effectOfOrder.')
])
def test_validate_invalid_court_orders_new(app, jwt, session, invalid_court_order, error_msg):
    """Assert not valid court order."""
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type='BC')

    ia_filing = factory_completed_filing(business, INCORPORATION_APPLICATION)

    filing = copy.deepcopy(CORRECTION)
    filing['filing']['header']['identifier'] = identifier
    filing['filing']['correction']['correctedFilingId'] = ia_filing.id
    del filing['filing']['correction']['commentOnly']
    invalid_court_order["filingId"] = ia_filing.id

    filing['filing']['correction']['courtOrders'] = [invalid_court_order]

    with jwt_request_context(app, jwt, [BASIC_USER]):
        err = validate(business, filing)
    assert err
    assert err.msg[0]['error'] == error_msg


@pytest.mark.parametrize('invalid_court_order, error_msg', [
    ({
        'fileNumber': '123456789012345678901',  # long fileNumber
        'orderDate': '2021-01-30T09:56:01+01:00',
        'effectOfOrder': 'planOfArrangement'
    }, "'123456789012345678901' is too long"),
    ({
        'orderDate': '2021-01-30T09:56:01+01:00',
        'effectOfOrder': 'planOfArrangement'
    }, "'fileNumber' is a required property"),
    ({
        'fileNumber': 'Valid File Number',
        'orderDate': '2021-01-30T09:56:01+01:00',
        'effectOfOrder': 'invalid'  # Invalid effectOfOrder
    }, 'Invalid effectOfOrder.')
])
def test_validate_invalid_court_orders_old(app, jwt, session, invalid_court_order, error_msg):
    """Assert not valid court order."""
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type='BC')

    ia_filing = factory_completed_filing(business, INCORPORATION_APPLICATION)
    court_order_filing = factory_completed_filing(business, COURT_ORDER_FILING_TEMPLATE)
    court_order = CourtOrder(
        filing_id=court_order_filing.id,
        business_id=business.id,
        effect_of_order='planOfArrangement',
        order_details='Court order details'
    )
    court_order.save()

    filing = copy.deepcopy(CORRECTION)
    filing['filing']['header']['identifier'] = identifier
    filing['filing']['correction']['correctedFilingId'] = ia_filing.id
    del filing['filing']['correction']['commentOnly']
    invalid_court_order["filingId"] = ia_filing.id
    invalid_court_order["id"] = court_order.id

    filing['filing']['correction']['courtOrders'] = [invalid_court_order]

    with jwt_request_context(app, jwt, [BASIC_USER]):
        err = validate(business, filing)
    assert err
    assert err.msg[0]['error'] == error_msg


@pytest.mark.parametrize('test_name, error_msg', [
    ("court_order_not_found", "Court order not found."),
    ("filing_id_does_not_match", "Filing Id does not match corrected filing Id."),
    ("multiple_court_orders", "Only one court order can be added."),
    ("multiple_court_orders_existing", "Only one court order can be added per filing."),
])
def test_validate_invalid_court_orders(app, jwt, session, test_name, error_msg):
    """Assert not valid court order."""
    identifier = 'BC1234567'
    business = factory_business(identifier, entity_type='BC')

    invalid_court_order = {
        'fileNumber': '123456789',
        'effectOfOrder': 'planOfArrangement',
        'orderDetails': 'Court order details',
        "filingId": 5645646
    }
    ia_filing = factory_completed_filing(business, INCORPORATION_APPLICATION)

    filing = copy.deepcopy(CORRECTION)
    filing['filing']['header']['identifier'] = identifier
    filing['filing']['correction']['correctedFilingId'] = ia_filing.id
    del filing['filing']['correction']['commentOnly']
    if test_name == "court_order_not_found":
        invalid_court_order["filingId"] = ia_filing.id
        invalid_court_order["id"] = 99999999
        filing['filing']['correction']['courtOrders'] = [invalid_court_order]
    elif test_name == "filing_id_does_not_match":
        invalid_court_order["filingId"] = 6546456
        filing['filing']['correction']['courtOrders'] = [invalid_court_order]
    elif test_name == "multiple_court_orders":
        invalid_court_order["filingId"] = ia_filing.id
        filing['filing']['correction']['courtOrders'] = [invalid_court_order, invalid_court_order]
    elif test_name == "multiple_court_orders_existing":
        court_order = CourtOrder(
            filing_id=ia_filing.id,
            business_id=business.id,
            effect_of_order='planOfArrangement',
            order_details='Court order details'
        )
        court_order.save()

        invalid_court_order["filingId"] = ia_filing.id
        invalid_court_order2 = copy.deepcopy(invalid_court_order)
        invalid_court_order2["id"] = court_order.id
        filing['filing']['correction']['courtOrders'] = [invalid_court_order, invalid_court_order2]

    with jwt_request_context(app, jwt, [BASIC_USER]):
        err = validate(business, filing)
    assert err
    assert err.msg[0]['error'] == error_msg
