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

"""Tests to assure the Authorization Services.

Test-Suite to ensure that the Authorization Service is working as expected.
"""
import random

import copy

from enum import Enum
from http import HTTPStatus

import pytest
from flask import jsonify
from registry_schemas.example_data import ALTERATION_FILING_TEMPLATE, ANNUAL_REPORT, CORRECTION_AR, \
    CHANGE_OF_REGISTRATION_TEMPLATE, RESTORATION, FILING_TEMPLATE, DISSOLUTION, PUT_BACK_ON, CONTINUATION_IN

from legal_api.models import Filing
from legal_api.models.business import Business

from legal_api.services.authz import BASIC_USER, COLIN_SVC_ROLE, STAFF_ROLE, authorized, get_allowed, is_allowed, \
    get_allowed_filings, get_allowable_actions
from legal_api.services.warnings.business.business_checks import WarningType
from tests import integration_authorization, not_github_ci
from tests.unit.models import factory_business, factory_filing, factory_incomplete_statuses, factory_completed_filing

from .utils import helper_create_jwt


def test_jwt_manager_initialized(jwt):
    """Assert that the jwt_manager is created as part of the fixtures."""
    assert jwt


@not_github_ci
def test_jwt_manager_correct_test_config(app_request, jwt):
    """Assert that the test configuration for the JWT is working as expected."""
    message = 'This is a protected end-point'
    protected_route = '/fake_jwt_route'

    @app_request.route(protected_route)
    @jwt.has_one_of_roles([STAFF_ROLE])
    def get():
        return jsonify(message=message)

    # assert that JWT is setup correctly for a known role
    token = helper_create_jwt(jwt, [STAFF_ROLE])
    headers = {'Authorization': 'Bearer ' + token}
    rv = app_request.test_client().get(protected_route, headers=headers)
    assert rv.status_code == HTTPStatus.OK

    # assert the JWT fails for an unknown role
    token = helper_create_jwt(jwt, ['SHOULD-FAIL'])
    headers = {'Authorization': 'Bearer ' + token}
    rv = app_request.test_client().get(protected_route, headers=headers)
    assert rv.status_code == HTTPStatus.UNAUTHORIZED


TEST_AUTHZ_DATA = [
    ('staff_role',  # test name
     'CP1234567',  # business identifier
     'happy-staff',  # username
     [STAFF_ROLE],  # roles
     ['view', 'edit'],  # allowed actions
     ['edit'],  # requested action
     HTTPStatus.OK),  # expected response
    ('colin svc role', 'CP1234567', 'CP1234567', [COLIN_SVC_ROLE], ['view', 'edit'], ['edit'],
     HTTPStatus.OK),
    ('authorized_user', 'CP0001237', 'CP1234567', [BASIC_USER], ['view', 'edit'], ['edit'],
     HTTPStatus.OK),
    ('unauthorized_user', 'CP1234567', 'Not-Match-Identifier', [BASIC_USER], None, ['edit'],
     HTTPStatus.METHOD_NOT_ALLOWED),
    ('missing_action', 'CP1234567', 'Not-Match-Identifier', [BASIC_USER], None, None,
     HTTPStatus.METHOD_NOT_ALLOWED),
    ('invalid_action', 'CP1234567', 'Not-Match-Identifier', [BASIC_USER], None, ['scrum'],
     HTTPStatus.METHOD_NOT_ALLOWED),
    ('add_comment_not_allowed', 'CP0001237', 'CP1234567', [BASIC_USER], None, ['add_comment'],
     HTTPStatus.METHOD_NOT_ALLOWED),
]


class FilingKey(str, Enum):
    """Define an enum for expected allowable filing keys."""

    ADMN_FRZE = 'ADMN_FRZE'
    IA_CP = 'IA_CP'
    IA_BC = 'IA_BC'
    IA_BEN = 'IA_BEN'
    IA_CC = 'IA_CC'
    IA_ULC = 'IA_ULC'
    REG_SP = 'REG_SP'
    REG_GP = 'REG_GP'
    CORRCTN = 'CORRCTN'
    CORRCTN_FIRMS = 'CORRCTN_FIRMS'
    AR_CP = 'AR_CP'
    AR_CORPS = 'AR_CORPS'
    COA_CP = 'COA_CP'
    COA_CORPS = 'COA_CORPS'
    COD_CP = 'COD_CP'
    COD_CORPS = 'COD_CORPS'
    COURT_ORDER = 'COURT_ORDER'
    VOL_DISS = 'VOL_DISS'
    ADM_DISS = 'ADM_DISS'
    VOL_DISS_FIRMS = 'VOL_DISS_FIRMS'
    ADM_DISS_FIRMS = 'ADM_DISS_FIRMS'
    REGISTRARS_NOTATION = 'REGISTRARS_NOTATION'
    REGISTRARS_ORDER = 'REGISTRARS_ORDER'
    SPECIAL_RESOLUTION = 'SPECIAL_RESOLUTION'
    ALTERATION = 'ALTERATION'
    CONTINUATION_OUT = 'CONTINUATION_OUT'
    TRANSITION = 'TRANSITION'
    CHANGE_OF_REGISTRATION = 'CHANGE_OF_REGISTRATION'
    CONV_FIRMS = 'CONV_FIRM'
    RESTRN_FULL_CORPS = 'RESTRN_FULL_CORPS'
    RESTRN_LTD_CORPS = 'RESTRN_LTD_CORPS'
    RESTRN_LTD_EXT_CORPS = 'RESTRN_LTD_EXT_CORPS'
    RESTRN_LTD_EXT_LLC = 'RESTRN_LTD_EXT_LLC'
    RESTRN_LTD_TO_FULL_CORPS = 'RESTRN_LTD_TO_FULL_CORPS'
    RESTRN_LTD_TO_FULL_LLC = 'RESTRN_LTD_TO_FULL_LLC'
    PUT_BACK_ON = 'PUT_BACK_ON'


EXPECTED_DATA = {
    FilingKey.ADMN_FRZE: {'displayName': 'Admin Freeze', 'feeCode': 'NOFEE', 'name': 'adminFreeze'},
    FilingKey.AR_CP: {'displayName': 'Annual Report', 'feeCode': 'OTANN', 'name': 'annualReport'},
    FilingKey.AR_CORPS: {'displayName': 'Annual Report', 'feeCode': 'BCANN', 'name': 'annualReport'},
    FilingKey.COA_CP: {'displayName': 'Address Change', 'feeCode': 'OTADD', 'name': 'changeOfAddress'},
    FilingKey.COA_CORPS: {'displayName': 'Address Change', 'feeCode': 'BCADD', 'name': 'changeOfAddress'},
    FilingKey.COD_CP: {'displayName': 'Director Change', 'feeCode': 'OTCDR', 'name': 'changeOfDirectors'},
    FilingKey.COD_CORPS: {'displayName': 'Director Change', 'feeCode': 'BCCDR', 'name': 'changeOfDirectors'},
    FilingKey.CORRCTN: {'displayName': 'Register Correction Application', 'feeCode': 'CRCTN', 'name': 'correction'},
    FilingKey.CORRCTN_FIRMS: {'displayName': 'Register Correction Application', 'feeCode': 'FMCORR',
                              'name': 'correction'},
    FilingKey.COURT_ORDER: {'displayName': 'Court Order', 'feeCode': 'NOFEE', 'name': 'courtOrder'},
    FilingKey.VOL_DISS: {'displayName': 'Voluntary Dissolution', 'feeCode': 'DIS_VOL',
                         'name': 'dissolution', 'type': 'voluntary'},
    FilingKey.ADM_DISS: {'displayName': 'Administrative Dissolution', 'feeCode': 'DIS_ADM',
                         'name': 'dissolution', 'type': 'administrative'},
    FilingKey.VOL_DISS_FIRMS: {'displayName': 'Statement of Dissolution', 'feeCode': 'DIS_VOL',
                                'name': 'dissolution', 'type': 'voluntary'},
    FilingKey.ADM_DISS_FIRMS: {'displayName': 'Statement of Dissolution', 'feeCode': 'DIS_ADM',
                               'name': 'dissolution', 'type': 'administrative'},
    FilingKey.REGISTRARS_NOTATION: {'displayName': "Registrar's Notation", 'feeCode': 'NOFEE',
                                    'name': 'registrarsNotation'},
    FilingKey.REGISTRARS_ORDER: {'displayName': "Registrar's Order", 'feeCode': 'NOFEE', 'name': 'registrarsOrder'},
    FilingKey.SPECIAL_RESOLUTION: {'displayName': 'Special Resolution', 'feeCode': 'SPRLN', 'name': 'specialResolution'},
    FilingKey.ALTERATION: {'displayName': 'Alteration', 'feeCode': 'ALTER', 'name': 'alteration'},
    FilingKey.CONTINUATION_OUT: {'displayName': '6-Month Consent to Continue Out', 'feeCode': 'CONTO',
                                 'name': 'consentContinuationOut'},
    FilingKey.TRANSITION: {'displayName': 'Transition Application', 'feeCode': 'TRANS', 'name': 'transition'},
    FilingKey.IA_CP: {'displayName': 'Incorporation Application', 'feeCode': 'OTINC',
                      'name': 'incorporationApplication'},
    FilingKey.IA_BC: {'displayName': 'BC Limited Company Incorporation Application', 'feeCode': 'BCINC',
                      'name': 'incorporationApplication'},
    FilingKey.IA_BEN: {'displayName': 'BC Benefit Company Incorporation Application', 'feeCode': 'BCINC',
                       'name': 'incorporationApplication'},
    FilingKey.IA_CC: {'displayName': 'BC Community Contribution Company Incorporation Application', 'feeCode': 'BCINC',
                      'name': 'incorporationApplication'},
    FilingKey.IA_ULC: {'displayName': 'BC Unlimited Liability Company Incorporation Application', 'feeCode': 'BCINC',
                       'name': 'incorporationApplication'},
    FilingKey.REG_SP: {'displayName': 'BC Sole Proprietorship Registration', 'feeCode': 'FRREG',
                       'name': 'registration'},
    FilingKey.REG_GP: {'displayName': 'BC General Partnership Registration', 'feeCode': 'FRREG',
                       'name': 'registration'},
    FilingKey.CHANGE_OF_REGISTRATION: {'displayName': 'Change of Registration Application', 'feeCode': 'FMCHANGE',
                                       'name': 'changeOfRegistration'},
    FilingKey.CONV_FIRMS: {'displayName': 'Record Conversion', 'feeCode': 'FMCONV', 'name': 'conversion'},
    FilingKey.RESTRN_FULL_CORPS:  {'displayName': 'Full Restoration Application', 'feeCode': 'RESTF',
                                   'name': 'restoration', 'type': 'fullRestoration'},
    FilingKey.RESTRN_LTD_CORPS: {'displayName': 'Limited Restoration Application', 'feeCode': 'RESTL',
                                 'name': 'restoration', 'type': 'limitedRestoration'},
    FilingKey.RESTRN_LTD_EXT_CORPS: {'displayName': 'Limited Restoration Extension Application', 'feeCode': 'RESXL',
                                     'name':'restoration', 'type': 'limitedRestorationExtension'},
    FilingKey.RESTRN_LTD_TO_FULL_CORPS: {'displayName': 'Conversion to Full Restoration Application', 'feeCode': 'RESXF',
                                         'name':'restoration', 'type': 'limitedRestorationToFull'},
    FilingKey.RESTRN_LTD_EXT_LLC: {'displayName': 'Limited Restoration Extension Application', 'feeCode': None,
                                     'name':'restoration', 'type': 'limitedRestorationExtension'},
    FilingKey.RESTRN_LTD_TO_FULL_LLC: {'displayName': 'Conversion to Full Restoration Application', 'feeCode': None,
                                         'name':'restoration', 'type': 'limitedRestorationToFull'},
    FilingKey.PUT_BACK_ON: {'displayName': 'Correction - Put Back On', 'feeCode': 'NOFEE', 'name': 'putBackOn'},
}

BLOCKER_FILING_STATUSES = factory_incomplete_statuses()
BLOCKER_FILING_STATUSES_AND_ADDITIONAL = factory_incomplete_statuses(['unknown_status_1',
                                                                      'unknown_status_2'])
BLOCKER_FILING_TYPES = ['alteration', 'correction']

RESTORATION_FILING_TEMPLATE = copy.deepcopy(FILING_TEMPLATE)
RESTORATION_FILING_TEMPLATE['filing']['restoration'] = RESTORATION

DISSOLUTION_FILING_TEMPLATE = copy.deepcopy(FILING_TEMPLATE)
DISSOLUTION_FILING_TEMPLATE['filing']['dissolution'] = DISSOLUTION

PUT_BACK_ON_FILING_TEMPLATE = copy.deepcopy(FILING_TEMPLATE)
PUT_BACK_ON_FILING_TEMPLATE['filing']['putBackOn'] = PUT_BACK_ON

CONTINUATION_IN_TEMPLATE = copy.deepcopy(FILING_TEMPLATE)
CONTINUATION_IN_TEMPLATE['filing']['continuationIn'] = CONTINUATION_IN

FILING_DATA = {
    'alteration': ALTERATION_FILING_TEMPLATE,
    'correction': CORRECTION_AR,
    'changeOfRegistration': CHANGE_OF_REGISTRATION_TEMPLATE,
    'restoration.limitedRestoration': RESTORATION_FILING_TEMPLATE,
    'restoration.fullRestoration': RESTORATION_FILING_TEMPLATE,
    'restoration.limitedRestorationExtension': RESTORATION_FILING_TEMPLATE,
    'dissolution': DISSOLUTION_FILING_TEMPLATE,
    'putBackOn': PUT_BACK_ON_FILING_TEMPLATE,
    'continuationIn': CONTINUATION_IN_TEMPLATE
}

MISSING_BUSINESS_INFO_WARNINGS = [{ 'warningType': WarningType.MISSING_REQUIRED_BUSINESS_INFO,
                                    'code': 'NO_BUSINESS_OFFICE',
                                    'message': 'A business office is required.'}]

def expected_lookup(filing_keys: list):
    results = []
    for filing_key in filing_keys:
        results.append(EXPECTED_DATA[filing_key])
    return results


@not_github_ci
@pytest.mark.parametrize('test_name,identifier,username,roles,allowed_actions,requested_actions,expected',
                         TEST_AUTHZ_DATA)
def test_authorized_user(monkeypatch, app_request, jwt,
                         test_name, identifier, username, roles, allowed_actions, requested_actions, expected):
    """Assert that the type of user authorization is correct, based on the expected outcome."""
    from requests import Response
    print(test_name)

    # mocks, the get and json calls for requests.Response
    def mock_get(*args, **kwargs):  # pylint: disable=unused-argument; mocks of library methods
        resp = Response()
        resp.status_code = 200
        return resp

    def mock_json(self, **kwargs):  # pylint: disable=unused-argument; mocks of library methods
        return {'roles': allowed_actions}

    monkeypatch.setattr('requests.sessions.Session.get', mock_get)
    monkeypatch.setattr('requests.Response.json', mock_json)

    # setup
    @app_request.route('/fake_jwt_route/<string:identifier>')
    @jwt.requires_auth
    def get_fake(identifier: str):
        if not authorized(identifier, jwt, ['view']):
            return jsonify(message='failed'), HTTPStatus.METHOD_NOT_ALLOWED
        return jsonify(message='success'), HTTPStatus.OK

    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {'Authorization': 'Bearer ' + token}

    # test it
    rv = app_request.test_client().get(f'/fake_jwt_route/{identifier}', headers=headers)

    # check it
    assert rv.status_code == expected


TEST_INTEG_AUTHZ_DATA = [
    ('staff_role',  # test name
     'CP1234567',  # business identifier
     'happy-staff',  # username
     [STAFF_ROLE],  # roles
     ['view', 'edit'],  # allowed actions
     ['edit'],  # requested action
     HTTPStatus.OK),  # expected response
    ('colin svc role', 'CP1234567', 'CP1234567', [COLIN_SVC_ROLE], ['view', 'edit'], ['edit'],
     HTTPStatus.OK),
    ('unauthorized_user', 'CP1234567', 'Not-Match-Identifier', [BASIC_USER], None, ['edit'],
     HTTPStatus.METHOD_NOT_ALLOWED),
    ('missing_action', 'CP1234567', 'Not-Match-Identifier', [BASIC_USER], None, None,
     HTTPStatus.METHOD_NOT_ALLOWED),
    ('invalid_action', 'CP1234567', 'Not-Match-Identifier', [BASIC_USER], None, ['scrum'],
     HTTPStatus.METHOD_NOT_ALLOWED),
    ('add_comment_not_allowed', 'CP0001237', 'CP1234567', [BASIC_USER], None, ['add_comment'],
     HTTPStatus.METHOD_NOT_ALLOWED),
]


@integration_authorization
@pytest.mark.parametrize('test_name,identifier,username,roles,allowed_actions,requested_actions,expected',
                         TEST_INTEG_AUTHZ_DATA)
def test_authorized_user_integ(monkeypatch, app, jwt,
                               test_name, identifier, username, roles, allowed_actions, requested_actions, expected):
    """Assert that the type of user authorization is correct, based on the expected outcome."""
    import flask  # noqa: F401; import actually used in mock
    # setup
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers['Authorization']

    with app.test_request_context():
        monkeypatch.setattr('flask.request.headers.get', mock_auth)

        rv = authorized(identifier, jwt, ['view'])

# check it
    if expected == HTTPStatus.OK:
        assert rv
    else:
        assert not rv


def test_authorized_missing_args():
    """Assert that the missing args return False."""
    identifier = 'a corp'
    jwt = 'fake'
    action = 'fake'

    rv = authorized(identifier, jwt, None)
    assert not rv

    rv = authorized(identifier, None, action)
    assert not rv

    rv = authorized(None, jwt, action)
    assert not rv


def test_authorized_bad_url(monkeypatch, app, jwt):
    """Assert that an invalid auth service URL returns False."""
    import flask  # noqa: F401; import actually used in mock
    # setup
    identifier = 'CP1234567'
    username = 'username'
    roles = [BASIC_USER]
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers['Authorization']

    with app.test_request_context():
        monkeypatch.setattr('flask.request.headers.get', mock_auth)
        auth_svc_url = app.config['AUTH_SVC_URL']
        app.config['AUTH_SVC_URL'] = 'http://no.way.this.works/dribble'

        rv = authorized(identifier, jwt, ['view'])

        app.config['AUTH_SVC_URL'] = auth_svc_url

    assert not rv


def test_authorized_invalid_roles(monkeypatch, app, jwt):
    """Assert that an invalid role returns False."""
    import flask  # noqa: F401 ; import actually used in mock
    # setup noqa: I003
    identifier = 'CP1234567'
    username = 'username'
    roles = ['NONE']
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers['Authorization']

    with app.test_request_context():
        monkeypatch.setattr('flask.request.headers.get', mock_auth)
        rv = authorized(identifier, jwt, ['view'])

    assert not rv


@pytest.mark.parametrize(
    'test_name,state,legal_types,username,roles,expected',
    [
        # active business
        ('staff_active_cp', Business.State.ACTIVE, ['CP'], 'staff', [STAFF_ROLE],
         ['adminFreeze', 'annualReport', 'changeOfAddress', 'changeOfDirectors', 'correction', 'courtOrder',
          {'dissolution': ['voluntary', 'administrative']}, 'incorporationApplication',
          'registrarsNotation', 'registrarsOrder', 'specialResolution']),
        ('staff_active_corps', Business.State.ACTIVE, ['BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE],
         ['adminFreeze', 'alteration', 'annualReport', 'changeOfAddress', 'changeOfDirectors', 'consentContinuationOut',
          'correction', 'courtOrder', {'dissolution': ['voluntary', 'administrative']},'incorporationApplication',
          'registrarsNotation', 'registrarsOrder', 'transition', {'restoration': ['limitedRestorationExtension', 'limitedRestorationToFull']}]),
        ('staff_active_llc', Business.State.ACTIVE, ['LLC'], 'staff', [STAFF_ROLE], []),
        ('staff_active_firms', Business.State.ACTIVE, ['SP', 'GP'], 'staff', [STAFF_ROLE],
         ['adminFreeze', 'changeOfRegistration', 'conversion', 'correction', 'courtOrder',
          'registrarsNotation', 'registrarsOrder', 'registration']),

        ('user_active_cp', Business.State.ACTIVE, ['CP'], 'general', [BASIC_USER],
         ['annualReport', 'changeOfAddress', 'changeOfDirectors',
          {'dissolution': ['voluntary']}, 'incorporationApplication', 'specialResolution']),
        ('staff_active_corps', Business.State.ACTIVE, ['BC', 'BEN', 'CC', 'ULC'], 'general', [BASIC_USER],
         ['alteration', 'annualReport', 'changeOfAddress', 'changeOfDirectors',
          {'dissolution': ['voluntary']}, 'incorporationApplication', 'transition']),
        ('user_active_llc', Business.State.ACTIVE, ['LLC'], 'general', [BASIC_USER], []),
        ('staff_active_firms', Business.State.ACTIVE, ['SP', 'GP'], 'general', [BASIC_USER],
         ['changeOfRegistration', 'registration']),

        # historical business
        ('staff_historical_cp', Business.State.HISTORICAL, ['CP'], 'staff', [STAFF_ROLE],
         ['courtOrder', 'putBackOn', 'registrarsNotation', 'registrarsOrder']),
        ('staff_historical_corps', Business.State.HISTORICAL, ['BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE],
         ['courtOrder', 'putBackOn', 'registrarsNotation', 'registrarsOrder',
         {'restoration': ['fullRestoration', 'limitedRestoration']}]),
        ('staff_historical_llc', Business.State.HISTORICAL, ['LLC'], 'staff', [STAFF_ROLE], []),
        ('staff_historical_firms', Business.State.HISTORICAL, ['SP', 'GP'], 'staff', [STAFF_ROLE],
         ['courtOrder', 'putBackOn', 'registrarsNotation', 'registrarsOrder']),

        ('user_historical', Business.State.HISTORICAL, ['BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [BASIC_USER], [])
    ]
)
def test_get_allowed(monkeypatch, app, jwt, test_name, state, legal_types, username, roles, expected):
    """Assert that get allowed returns valid filings."""
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        monkeypatch.setattr('flask.request.headers.get', mock_auth)
        for legal_type in legal_types:
            filing_types = get_allowed(state, legal_type, jwt)
            assert filing_types == expected


@pytest.mark.parametrize(
    'test_name,state,filing_type,sub_filing_type,legal_types,username,roles,expected',
    [
        # active business
        ('staff_active_allowed', Business.State.ACTIVE, 'alteration', None,
         ['BC', 'BEN', 'ULC', 'CC'], 'staff', [STAFF_ROLE], True),
        ('staff_active', Business.State.ACTIVE, 'alteration', None,
         ['CP', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_active_allowed', Business.State.ACTIVE, 'annualReport', None,
         ['CP', 'BEN', 'BC', 'CC', 'ULC'], 'staff', [STAFF_ROLE], True),
        ('staff_active', Business.State.ACTIVE, 'annualReport', None,
         ['LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_active_allowed', Business.State.ACTIVE, 'changeOfAddress', None,
         ['CP', 'BEN', 'BC', 'CC', 'ULC'], 'staff', [STAFF_ROLE], True),
        ('staff_active', Business.State.ACTIVE, 'changeOfAddress', None,
         ['LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_active_allowed', Business.State.ACTIVE, 'changeOfDirectors', None,
         ['CP', 'BEN', 'BC', 'CC', 'ULC'], 'staff', [STAFF_ROLE], True),
        ('staff_active', Business.State.ACTIVE, 'changeOfDirectors', None,
         ['LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_active_allowed', Business.State.ACTIVE, 'correction', None,
         ['CP', 'BEN', 'BC', 'CC', 'ULC', 'SP', 'GP'], 'staff', [STAFF_ROLE], True),
        ('staff_active', Business.State.ACTIVE, 'correction', None,
         ['LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_active_allowed', Business.State.ACTIVE, 'courtOrder', None,
         ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE], True),

        ('staff_active_allowed', Business.State.ACTIVE, 'courtOrder', None,
         ['LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_active_allowed', Business.State.ACTIVE, 'dissolution', 'voluntary',
         ['CP', 'BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE], True),

        ('staff_active_allowed', Business.State.ACTIVE, 'dissolution', 'administrative',
         ['CP', 'BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE], True),

        ('staff_active_allowed', Business.State.ACTIVE, 'incorporationApplication', None,
         ['CP', 'BC', 'BEN', 'ULC', 'CC'], 'staff', [STAFF_ROLE], True),
        
        ('staff_active', Business.State.ACTIVE, 'restoration', 'limitedRestorationExtension',
         ['BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE], True),
        ('staff_active', Business.State.ACTIVE, 'restoration', 'limitedRestorationToFull',
         ['BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE], True),

        ('staff_active', Business.State.ACTIVE, 'restoration', 'fullRestoration',
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),
        ('staff_active', Business.State.ACTIVE, 'restoration', 'limitedRestoration',
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_active_allowed', Business.State.ACTIVE, 'specialResolution', None, ['CP'], 'staff', [STAFF_ROLE], True),
        ('staff_active', Business.State.ACTIVE, 'specialResolution', None,
         ['BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_active_allowed', Business.State.ACTIVE, 'transition', None,
         ['BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE], True),
        ('staff_active', Business.State.ACTIVE, 'transition', None,
         ['CP', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_active_allowed', Business.State.ACTIVE, 'registrarsNotation', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE], True),

        ('staff_active_allowed', Business.State.ACTIVE, 'registrarsOrder', None,
         ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE], True),

        ('staff_active_allowed', Business.State.ACTIVE, 'registration', None,
         ['SP', 'GP'], 'staff', [STAFF_ROLE], True),

        ('staff_active_allowed', Business.State.ACTIVE, 'changeOfRegistration', None,
         ['SP', 'GP'], 'staff', [STAFF_ROLE], True),

        ('staff_active_allowed', Business.State.ACTIVE, 'consentContinuationOut', None,
         ['BC', 'BEN', 'ULC', 'CC'], 'staff', [STAFF_ROLE], True),


        ('user_active_allowed', Business.State.ACTIVE, 'alteration', None,
         ['BC', 'BEN', 'ULC', 'CC'], 'general', [BASIC_USER], True),
        ('user_active', Business.State.ACTIVE, 'alteration', None,
         ['CP', 'LLC'], 'general', [BASIC_USER], False),

        ('user_active_allowed', Business.State.ACTIVE, 'annualReport', None,
         ['CP', 'BEN', 'BC', 'CC', 'ULC'], 'general', [BASIC_USER], True),
        ('user_active', Business.State.ACTIVE, 'annualReport', None,
         ['LLC'], 'general', [BASIC_USER], False),

        ('user_active_allowed', Business.State.ACTIVE, 'changeOfAddress', None,
         ['CP', 'BEN', 'BC', 'CC', 'ULC'], 'general', [BASIC_USER], True),
        ('user_active', Business.State.ACTIVE, 'changeOfAddress', None,
         ['LLC'], 'general', [BASIC_USER], False),

        ('user_active_allowed', Business.State.ACTIVE, 'changeOfDirectors', None,
         ['CP', 'BEN', 'BC', 'CC', 'ULC'], 'general', [BASIC_USER], True),
        ('user_active', Business.State.ACTIVE, 'changeOfDirectors', None,
         ['LLC'], 'general', [BASIC_USER], False),

        ('user_active', Business.State.ACTIVE, 'correction', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'general', [BASIC_USER], False),

        ('user_active', Business.State.ACTIVE, 'courtOrder', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'general', [BASIC_USER], False),

        ('user_active_allowed', Business.State.ACTIVE, 'dissolution', 'voluntary',
         ['CP', 'BC', 'BEN', 'CC', 'ULC'], 'general', [BASIC_USER], True),

        ('user_active_allowed', Business.State.ACTIVE, 'incorporationApplication', None,
         ['CP', 'BC', 'BEN', 'ULC', 'CC'], 'general', [BASIC_USER], True),

        ('user_active_allowed', Business.State.ACTIVE, 'registration', None,
         ['SP', 'GP'], 'general', [BASIC_USER], True),

        ('user_active_allowed', Business.State.ACTIVE, 'changeOfRegistration', None,
         ['SP', 'GP'], 'general', [BASIC_USER], True),

        ('user_active', Business.State.ACTIVE, 'restoration', 'fullRestoration',
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'general', [BASIC_USER], False),

        ('user_active', Business.State.ACTIVE, 'restoration', 'limitedRestoration',
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'general', [BASIC_USER], False),

        ('user_active_allowed', Business.State.ACTIVE, 'specialResolution', None, ['CP'], 'general', [BASIC_USER], True),
        ('user_active', Business.State.ACTIVE, 'specialResolution', None,
         ['BC', 'BEN', 'CC', 'ULC', 'LLC'], 'general', [BASIC_USER], False),

        ('user_active_allowed', Business.State.ACTIVE, 'transition', None,
         ['BC', 'BEN', 'CC', 'ULC'], 'general', [BASIC_USER], True),
        ('user_active', Business.State.ACTIVE, 'transition', None,
         ['CP', 'LLC'], 'general', [BASIC_USER], False),

        ('user_active', Business.State.ACTIVE, 'registrarsNotation', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'general', [BASIC_USER], False),

        ('user_active', Business.State.ACTIVE, 'registrarsOrder', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'general', [BASIC_USER], False),

        ('user_active', Business.State.ACTIVE, 'consentContinuationOut', None,
         ['BC', 'BEN', 'ULC', 'CC'], 'staff', [BASIC_USER], False),


        # historical business
        ('staff_historical', Business.State.HISTORICAL, 'alteration', None,
         ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE], False),

        ('staff_historical', Business.State.HISTORICAL, 'annualReport', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_historical', Business.State.HISTORICAL, 'changeOfAddress', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_historical', Business.State.HISTORICAL, 'changeOfDirectors', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_historical', Business.State.HISTORICAL, 'correction', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_historical_allowed', Business.State.HISTORICAL, 'courtOrder', None,
         ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE], True),

        ('staff_historical', Business.State.HISTORICAL, 'dissolution', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC', 'SP', 'GP'], 'staff', [STAFF_ROLE], False),

        ('staff_historical', Business.State.HISTORICAL, 'incorporationApplication', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_historical_allowed', Business.State.HISTORICAL, 'restoration', 'fullRestoration',
         ['BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE], True),

        ('staff_historical_allowed', Business.State.HISTORICAL, 'restoration', 'limitedRestoration',
         ['BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE], True),

        ('staff_historical', Business.State.HISTORICAL, 'restoration', 'fullRestoration',
         ['CP'], 'staff', [STAFF_ROLE], False),

        ('staff_historical', Business.State.HISTORICAL, 'restoration', 'limitedRestoration',
         ['CP'], 'staff', [STAFF_ROLE], False),

        ('staff_historical', Business.State.HISTORICAL, 'specialResolution', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_historical', Business.State.HISTORICAL, 'transition', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_historical_allowed', Business.State.HISTORICAL, 'registrarsNotation', None,
         ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE], True),

        ('staff_historical_allowed', Business.State.HISTORICAL, 'registrarsOrder', None,
         ['SP', 'GP', 'CP', 'BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE], True),

        ('staff_historical', Business.State.HISTORICAL, 'registration', None,
         ['SP', 'GP'], 'staff', [STAFF_ROLE], False),

        ('staff_historical', Business.State.HISTORICAL, 'changeOfRegistration', None,
         ['SP', 'GP'], 'staff', [STAFF_ROLE], False),

        ('staff_historical', Business.State.HISTORICAL, 'consentContinuationOut', None,
         ['BC', 'BEN', 'ULC', 'CC'], 'staff', [STAFF_ROLE], False),


        ('user_historical', Business.State.HISTORICAL, 'alteration', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'general', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'annualReport', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'general', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'changeOfAddress', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'general', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'changeOfDirectors', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'general', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'correction', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'general', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'courtOrder', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'general', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'dissolution', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC', 'SP', 'GP', 'SP', 'GP'], 'general', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'incorporationApplication', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'general', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'restoration', 'fullRestoration',
         ['BC', 'BEN', 'CC', 'ULC'], 'general', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'restoration', 'limitedRestoration',
         ['BC', 'BEN', 'CC', 'ULC'], 'general', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'specialResolution', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'general', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'transition', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'general', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'registrarsNotation', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'general', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'registrarsOrder', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'general', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'registration', None,
         ['SP', 'GP'], 'general', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'changeOfRegistration', None,
         ['SP', 'GP'], 'general', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'consentContinuationOut', None,
         ['BC', 'BEN', 'ULC', 'CC'], 'staff', [BASIC_USER], False),
    ]
)
def test_is_allowed(monkeypatch, app, jwt, test_name, state, filing_type, sub_filing_type,
                    legal_types, username, roles, expected):
    """Assert that get allowed returns valid filings."""
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        monkeypatch.setattr('flask.request.headers.get', mock_auth)
        for legal_type in legal_types:
            filing_types = is_allowed(state, filing_type, legal_type, jwt, sub_filing_type)
            assert filing_types == expected


@pytest.mark.parametrize(
    'test_name,business_exists,state,legal_types,username,roles,expected',
    [
        # active business - staff user
        ('staff_active_cp', True, Business.State.ACTIVE, ['CP'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.ADMN_FRZE,
                          FilingKey.AR_CP,
                          FilingKey.COA_CP,
                          FilingKey.COD_CP,
                          FilingKey.CORRCTN,
                          FilingKey.COURT_ORDER,
                          FilingKey.VOL_DISS,
                          FilingKey.ADM_DISS,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER,
                          FilingKey.SPECIAL_RESOLUTION])),
        ('staff_active_corps', True, Business.State.ACTIVE, ['BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.ADMN_FRZE,
                          FilingKey.ALTERATION,
                          FilingKey.AR_CORPS,
                          FilingKey.COA_CORPS,
                          FilingKey.COD_CORPS,
                          FilingKey.CONTINUATION_OUT,
                          FilingKey.CORRCTN,
                          FilingKey.COURT_ORDER,
                          FilingKey.VOL_DISS,
                          FilingKey.ADM_DISS,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER,
                          FilingKey.TRANSITION])),
        ('staff_active_llc', True, Business.State.ACTIVE, ['LLC'], 'staff', [STAFF_ROLE], []),
        ('staff_active_firms', True, Business.State.ACTIVE, ['SP', 'GP'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.ADMN_FRZE,
                          FilingKey.CHANGE_OF_REGISTRATION,
                          FilingKey.CONV_FIRMS,
                          FilingKey.CORRCTN_FIRMS,
                          FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER])),

        # active business - general user
        ('general_user_cp', True, Business.State.ACTIVE, ['CP'], 'general', [BASIC_USER],
         expected_lookup([FilingKey.AR_CP,
                          FilingKey.COA_CP,
                          FilingKey.COD_CP,
                          FilingKey.VOL_DISS,
                          FilingKey.SPECIAL_RESOLUTION])),
        ('general_user_corps', True, Business.State.ACTIVE, ['BC', 'BEN', 'CC', 'ULC'], 'general', [BASIC_USER],
         expected_lookup([FilingKey.ALTERATION,
                          FilingKey.AR_CORPS,
                          FilingKey.COA_CORPS,
                          FilingKey.COD_CORPS,
                          FilingKey.VOL_DISS,
                          FilingKey.TRANSITION])),
        ('general_user_llc', True, Business.State.ACTIVE, ['LLC'], 'general', [BASIC_USER], []),
        ('general_user_firms', True, Business.State.ACTIVE, ['SP', 'GP'], 'general', [BASIC_USER],
         expected_lookup([FilingKey.CHANGE_OF_REGISTRATION])),

        # historical business - staff user
        ('staff_historical_cp', True, Business.State.HISTORICAL, ['CP'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER])),
        ('staff_historical_corps', True, Business.State.HISTORICAL, ['BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER,
                          FilingKey.RESTRN_FULL_CORPS,
                          FilingKey.RESTRN_LTD_CORPS])),
        ('staff_historical_llc', True, Business.State.HISTORICAL, ['LLC'], 'staff', [STAFF_ROLE], []),
        ('staff_historical_firms', True, Business.State.HISTORICAL, ['SP', 'GP'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER])),

        # historical business - general user
        ('general_user_historical_cp', True, Business.State.HISTORICAL, ['CP'], 'general', [BASIC_USER], []),
        ('general_user_historical_corps', True, Business.State.HISTORICAL, ['BC', 'BEN', 'CC', 'ULC'], 'general',
         [BASIC_USER], []),
        ('general_user_historical_llc', True, Business.State.HISTORICAL, ['LLC'], 'general', [BASIC_USER], []),
        ('general_user_historical_firms', True, Business.State.HISTORICAL, ['SP', 'GP'], 'general', [BASIC_USER], []),
    ]
)
def test_get_allowed_actions(monkeypatch, app, session, jwt, test_name, business_exists, state, legal_types, username,
                             roles, expected):
    """Assert that get_allowed_actions returns the expected allowable filing info."""
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        monkeypatch.setattr('flask.request.headers.get', mock_auth)

        for legal_type in legal_types:
            business = None
            if business_exists:
                business = create_business(legal_type, state)
            result = get_allowable_actions(jwt, business)
            assert result
            assert result['filing']['filingSubmissionLink']
            assert result['filing']['filingTypes'] == expected


@pytest.mark.parametrize(
    'test_name,business_exists,state,legal_types,username,roles,expected',
    [
        # no business - staff user
        ('staff_no_business_cp', False, Business.State.ACTIVE, ['CP'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.IA_CP])),
        ('staff_no_business_bc', False, Business.State.ACTIVE, ['BC'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.IA_BC])),
        ('staff_no_business_ben', False, Business.State.ACTIVE, ['BEN'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.IA_BEN])),
        ('staff_no_business_cc', False, Business.State.ACTIVE, ['CC'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.IA_CC])),
        ('staff_no_business_ulc', False, Business.State.ACTIVE, ['ULC'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.IA_ULC])),
        ('staff_no_business_llc', False, Business.State.ACTIVE, ['LLC'], 'staff', [STAFF_ROLE], []),
        ('staff_no_business_sp', False, Business.State.ACTIVE, ['SP'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.REG_SP])),
        ('staff_no_business_gp', False, Business.State.ACTIVE, ['GP'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.REG_GP])),

        # no business - general user
        ('general_user_no_business_cp', False, Business.State.ACTIVE, ['CP'], 'general', [BASIC_USER],
         expected_lookup([FilingKey.IA_CP])),
        ('general_user_no_business_bc', False, Business.State.ACTIVE, ['BC'], 'general', [BASIC_USER],
         expected_lookup([FilingKey.IA_BC])),
        ('general_user_no_business_ben', False, Business.State.ACTIVE, ['BEN'], 'general', [BASIC_USER],
         expected_lookup([FilingKey.IA_BEN])),
        ('general_user_no_business_cc', False, Business.State.ACTIVE, ['CC'], 'general', [BASIC_USER],
         expected_lookup([FilingKey.IA_CC])),
        ('general_user_no_business_ulc', False, Business.State.ACTIVE, ['ULC'], 'general', [BASIC_USER],
         expected_lookup([FilingKey.IA_ULC])),
        ('general_user_no_business_llc', False, Business.State.ACTIVE, ['LLC'], 'general', [BASIC_USER], []),
        ('general_user_no_business_sp', False, Business.State.ACTIVE, ['SP'], 'general', [BASIC_USER],
         expected_lookup([FilingKey.REG_SP])),
        ('general_user_no_business_gp', False, Business.State.ACTIVE, ['GP'], 'general', [BASIC_USER],
         expected_lookup([FilingKey.REG_GP])),

        # active business - staff user
        ('staff_active_cp', True, Business.State.ACTIVE, ['CP'], 'staff', [STAFF_ROLE],
          expected_lookup([FilingKey.ADMN_FRZE,
                           FilingKey.AR_CP,
                           FilingKey.COA_CP,
                           FilingKey.COD_CP,
                           FilingKey.CORRCTN,
                           FilingKey.COURT_ORDER,
                           FilingKey.VOL_DISS,
                           FilingKey.ADM_DISS,
                           FilingKey.REGISTRARS_NOTATION,
                           FilingKey.REGISTRARS_ORDER,
                           FilingKey.SPECIAL_RESOLUTION])),
        ('staff_active_corps', True, Business.State.ACTIVE, ['BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.ADMN_FRZE,
                          FilingKey.ALTERATION,
                          FilingKey.AR_CORPS,
                          FilingKey.COA_CORPS,
                          FilingKey.COD_CORPS,
                          FilingKey.CONTINUATION_OUT,
                          FilingKey.CORRCTN,
                          FilingKey.COURT_ORDER,
                          FilingKey.VOL_DISS,
                          FilingKey.ADM_DISS,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER,
                          FilingKey.TRANSITION])),
        ('staff_active_llc', True, Business.State.ACTIVE, ['LLC'], 'staff', [STAFF_ROLE], []),
        ('staff_active_firms', True, Business.State.ACTIVE, ['SP', 'GP'], 'staff', [STAFF_ROLE],
          expected_lookup([FilingKey.ADMN_FRZE,
                           FilingKey.CHANGE_OF_REGISTRATION,
                           FilingKey.CONV_FIRMS,
                           FilingKey.CORRCTN_FIRMS,
                           FilingKey.COURT_ORDER,
                           FilingKey.REGISTRARS_NOTATION,
                           FilingKey.REGISTRARS_ORDER])),

        # active business - general user
        ('general_user_cp', True, Business.State.ACTIVE, ['CP'], 'general', [BASIC_USER],
         expected_lookup([FilingKey.AR_CP,
                          FilingKey.COA_CP,
                          FilingKey.COD_CP,
                          FilingKey.VOL_DISS,
                          FilingKey.SPECIAL_RESOLUTION])),
        ('general_user_corps', True, Business.State.ACTIVE, ['BC', 'BEN', 'CC', 'ULC'], 'general', [BASIC_USER],
         expected_lookup([FilingKey.ALTERATION,
                          FilingKey.AR_CORPS,
                          FilingKey.COA_CORPS,
                          FilingKey.COD_CORPS,
                          FilingKey.VOL_DISS,
                          FilingKey.TRANSITION])),
        ('general_user_llc', True, Business.State.ACTIVE, ['LLC'], 'general', [BASIC_USER], []),
        ('general_user_firms', True, Business.State.ACTIVE, ['SP', 'GP'], 'general', [BASIC_USER],
         expected_lookup([FilingKey.CHANGE_OF_REGISTRATION])),

        # historical business - staff user
        ('staff_historical_cp', True, Business.State.HISTORICAL, ['CP'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER])),
        ('staff_historical_corps', True, Business.State.HISTORICAL, ['BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER,
                          FilingKey.RESTRN_FULL_CORPS,
                          FilingKey.RESTRN_LTD_CORPS])),
        ('staff_historical_llc', True, Business.State.HISTORICAL, ['LLC'], 'staff', [STAFF_ROLE], []),
        ('staff_historical_firms', True, Business.State.HISTORICAL, ['SP', 'GP'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER])),

        # historical business - general user
        ('general_user_historical_cp', True, Business.State.HISTORICAL, ['CP'], 'general', [BASIC_USER], []),
        ('general_user_historical_corps', True, Business.State.HISTORICAL, ['BC', 'BEN', 'CC', 'ULC'], 'general',
         [BASIC_USER], []),
        ('general_user_historical_llc', True, Business.State.HISTORICAL, ['LLC'], 'general', [BASIC_USER], []),
        ('general_user_historical_firms', True, Business.State.HISTORICAL, ['SP', 'GP'], 'general', [BASIC_USER], []),
    ]
)
def test_get_allowed_filings(monkeypatch, app, session, jwt, test_name, business_exists, state, legal_types, username, roles, expected):
    """Assert that get allowed returns valid filings."""
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        monkeypatch.setattr('flask.request.headers.get', mock_auth)

        for legal_type in legal_types:
            business = None
            if business_exists:
                business = create_business(legal_type, state)
            filing_types = get_allowed_filings(business, state, legal_type, jwt)
            assert filing_types == expected


@pytest.mark.parametrize(
    'test_name,business_exists,state,legal_types,username,roles,expected',
    [
        # active business - staff user
        ('staff_active_cp', True, Business.State.ACTIVE, ['CP'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.ADMN_FRZE,
                          FilingKey.COURT_ORDER,
                          FilingKey.ADM_DISS,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER])),
        ('staff_active_corps', True, Business.State.ACTIVE, ['BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.ADMN_FRZE,
                          FilingKey.COURT_ORDER,
                          FilingKey.ADM_DISS,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER,
                          FilingKey.TRANSITION])),
        ('staff_active_llc', True, Business.State.ACTIVE, ['LLC'], 'staff', [STAFF_ROLE], []),
        ('staff_active_firms', True, Business.State.ACTIVE, ['SP', 'GP'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.ADMN_FRZE,
                          FilingKey.CONV_FIRMS,
                          FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER])),

        # active business - general user
        ('general_user_cp', True, Business.State.ACTIVE, ['CP'], 'general', [BASIC_USER], []),
        ('general_user_corps', True, Business.State.ACTIVE, ['BC', 'BEN', 'CC', 'ULC'], 'general', [BASIC_USER],
         expected_lookup([FilingKey.TRANSITION])),
        ('general_user_llc', True, Business.State.ACTIVE, ['LLC'], 'general', [BASIC_USER], []),
        ('general_user_firms', True, Business.State.ACTIVE, ['SP', 'GP'], 'general', [BASIC_USER], []),

        # historical business - staff user
        ('staff_historical_cp', True, Business.State.HISTORICAL, ['CP'], 'staff', [STAFF_ROLE],
        expected_lookup([FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER])),
        ('staff_historical_corps', True, Business.State.HISTORICAL, ['BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER,
                          FilingKey.RESTRN_FULL_CORPS,
                          FilingKey.RESTRN_LTD_CORPS])),
        ('staff_historical_llc', True, Business.State.HISTORICAL, ['LLC'], 'staff', [STAFF_ROLE], []),
        ('staff_historical_firms', True, Business.State.HISTORICAL, ['SP', 'GP'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER])),

        # historical business - general user
        ('general_user_historical_cp', True, Business.State.HISTORICAL, ['CP'], 'general', [BASIC_USER], []),
        ('general_user_historical_corps', True, Business.State.HISTORICAL, ['BC', 'BEN', 'CC', 'ULC'], 'general',
         [BASIC_USER], []),
        ('general_user_historical_llc', True, Business.State.HISTORICAL, ['LLC'], 'general', [BASIC_USER], []),
        ('general_user_historical_firms', True, Business.State.HISTORICAL, ['SP', 'GP'], 'general', [BASIC_USER], []),
    ]
)
def test_get_allowed_filings_blocker_admin_freeze(monkeypatch, app, session, jwt, test_name, business_exists, state,
                                                  legal_types, username, roles, expected):
    """Assert that get allowed returns valid filings when business is frozen."""
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        monkeypatch.setattr('flask.request.headers.get', mock_auth)

        for legal_type in legal_types:
            business = None
            if business_exists:
                identifier = (f'BC{random.SystemRandom().getrandbits(0x58)}')[:9]
                business = factory_business(identifier=identifier,
                                            entity_type=legal_type,
                                            state=state,
                                            admin_freeze=True)
            filing_types = get_allowed_filings(business, state, legal_type, jwt)
            assert filing_types == expected


@pytest.mark.parametrize(
    'test_name,state,legal_types,username,roles,filing_statuses,expected',
    [
        # active business - staff user
        ('staff_active_cp', Business.State.ACTIVE, ['CP'], 'staff', [STAFF_ROLE], BLOCKER_FILING_STATUSES,
         expected_lookup([FilingKey.ADMN_FRZE,
                          FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER])),
        ('staff_active_corps', Business.State.ACTIVE, ['BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE],
         BLOCKER_FILING_STATUSES,
         expected_lookup([FilingKey.ADMN_FRZE,
                          FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER,
                          FilingKey.TRANSITION])),
        ('staff_active_llc', Business.State.ACTIVE, ['LLC'], 'staff', [STAFF_ROLE], BLOCKER_FILING_STATUSES, []),
        ('staff_active_firms', Business.State.ACTIVE, ['SP', 'GP'], 'staff', [STAFF_ROLE], BLOCKER_FILING_STATUSES,
         expected_lookup([FilingKey.ADMN_FRZE,
                          FilingKey.CONV_FIRMS,
                          FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER])),

        # active business - general user
        ('general_user_cp', Business.State.ACTIVE, ['CP'], 'general', [BASIC_USER], BLOCKER_FILING_STATUSES, []),
        ('general_user_corps', Business.State.ACTIVE, ['BC', 'BEN', 'CC', 'ULC'], 'general', [BASIC_USER],
         BLOCKER_FILING_STATUSES, expected_lookup([FilingKey.TRANSITION])),
        ('general_user_llc', Business.State.ACTIVE, ['LLC'], 'general', [BASIC_USER], BLOCKER_FILING_STATUSES, []),
        ('general_user_firms', Business.State.ACTIVE, ['SP', 'GP'], 'general', [BASIC_USER], BLOCKER_FILING_STATUSES,
         []),

        # historical business - staff user
        ('staff_historical_cp', Business.State.HISTORICAL, ['CP'], 'staff', [STAFF_ROLE], BLOCKER_FILING_STATUSES,
         expected_lookup([FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER])),
        ('staff_historical_corps', Business.State.HISTORICAL, ['BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE],
         BLOCKER_FILING_STATUSES,
         expected_lookup([FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER,
                          FilingKey.RESTRN_FULL_CORPS,
                          FilingKey.RESTRN_LTD_CORPS])),
        ('staff_historical_llc', Business.State.HISTORICAL, ['LLC'], 'staff', [STAFF_ROLE],
         BLOCKER_FILING_STATUSES, []),
        ('staff_historical_firms', Business.State.HISTORICAL, ['SP', 'GP'], 'staff', [STAFF_ROLE],
         BLOCKER_FILING_STATUSES,
         expected_lookup([FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER])),

        # historical business - general user
        ('general_user_historical_cp', Business.State.HISTORICAL, ['CP'], 'general', [BASIC_USER],
         BLOCKER_FILING_STATUSES, []),
        ('general_user_historical_corps', Business.State.HISTORICAL, ['BC', 'BEN', 'CC', 'ULC'], 'general',
         [BASIC_USER], BLOCKER_FILING_STATUSES, []),
        ('general_user_historical_llc', Business.State.HISTORICAL, ['LLC'], 'general', [BASIC_USER],
         BLOCKER_FILING_STATUSES, []),
        ('general_user_historical_firms', Business.State.HISTORICAL, ['SP', 'GP'], 'general', [BASIC_USER],
         BLOCKER_FILING_STATUSES, []),
    ]
)
def test_allowed_filings_blocker_filing_incomplete(monkeypatch, app, session, jwt, test_name, state, legal_types,
                                                       username, roles, filing_statuses, expected):
    """Assert that get allowed returns valid filings when business has blocker filings.

       A blocker filing in this instance is any filing that has a status of DRAFT, PENDING, PENDING CORRECTION,
       ERROR or PAID.
    """
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        monkeypatch.setattr('flask.request.headers.get', mock_auth)

        for legal_type in legal_types:
            for filing_status in filing_statuses:
                business = create_business(legal_type, state)
                create_incomplete_filing(business=business,
                                         filing_name='unknownFiling',
                                         filing_status=filing_status)
                filing_types = get_allowed_filings(business, state, legal_type, jwt)
                assert filing_types == expected


@pytest.mark.parametrize(
    'test_name,state,legal_types,username,roles,filing_types,filing_statuses,expected',
    [
        # active business - staff user
        ('staff_active_cp', Business.State.ACTIVE, ['CP'], 'staff', [STAFF_ROLE],
         BLOCKER_FILING_TYPES, BLOCKER_FILING_STATUSES_AND_ADDITIONAL,
         expected_lookup([FilingKey.ADMN_FRZE,
                          FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER])),
        ('staff_active_corps', Business.State.ACTIVE, ['BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE],
         BLOCKER_FILING_TYPES, BLOCKER_FILING_STATUSES_AND_ADDITIONAL,
         expected_lookup([FilingKey.ADMN_FRZE,
                          FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER,
                          FilingKey.TRANSITION])),
        ('staff_active_llc', Business.State.ACTIVE, ['LLC'], 'staff', [STAFF_ROLE],
         BLOCKER_FILING_TYPES, BLOCKER_FILING_STATUSES_AND_ADDITIONAL, []),
        ('staff_active_firms', Business.State.ACTIVE, ['SP', 'GP'], 'staff', [STAFF_ROLE],
         BLOCKER_FILING_TYPES, BLOCKER_FILING_STATUSES_AND_ADDITIONAL,
         expected_lookup([FilingKey.ADMN_FRZE,
                          FilingKey.CONV_FIRMS,
                          FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER])),

        # active business - general user
        ('general_user_cp', Business.State.ACTIVE, ['CP'], 'general', [BASIC_USER],
         BLOCKER_FILING_TYPES, BLOCKER_FILING_STATUSES_AND_ADDITIONAL, []),
        ('general_user_corps', Business.State.ACTIVE, ['BC', 'BEN', 'CC', 'ULC'], 'general', [BASIC_USER],
         BLOCKER_FILING_TYPES, BLOCKER_FILING_STATUSES_AND_ADDITIONAL, expected_lookup([FilingKey.TRANSITION])),
        ('general_user_llc', Business.State.ACTIVE, ['LLC'], 'general', [BASIC_USER], BLOCKER_FILING_TYPES,
         BLOCKER_FILING_STATUSES_AND_ADDITIONAL, []),
        ('general_user_firms', Business.State.ACTIVE, ['SP', 'GP'], 'general', [BASIC_USER], BLOCKER_FILING_TYPES,
         BLOCKER_FILING_STATUSES_AND_ADDITIONAL, []),

        # historical business - staff user
        ('staff_historical_cp', Business.State.HISTORICAL, ['CP'], 'staff', [STAFF_ROLE],
         BLOCKER_FILING_TYPES, BLOCKER_FILING_STATUSES_AND_ADDITIONAL,
         expected_lookup([FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER])),
        ('staff_historical_corps', Business.State.HISTORICAL, ['BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE],
         BLOCKER_FILING_TYPES, BLOCKER_FILING_STATUSES_AND_ADDITIONAL,
         expected_lookup([FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER,
                          FilingKey.RESTRN_FULL_CORPS,
                          FilingKey.RESTRN_LTD_CORPS])),
        ('staff_historical_llc', Business.State.HISTORICAL, ['LLC'], 'staff', [STAFF_ROLE],
         BLOCKER_FILING_TYPES, BLOCKER_FILING_STATUSES_AND_ADDITIONAL, []),
        ('staff_historical_firms', Business.State.HISTORICAL, ['SP', 'GP'], 'staff', [STAFF_ROLE],
         BLOCKER_FILING_TYPES, BLOCKER_FILING_STATUSES_AND_ADDITIONAL,
         expected_lookup([FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER])),

        # historical business - general user
        ('general_user_historical_cp', Business.State.HISTORICAL, ['CP'], 'general', [BASIC_USER],
         BLOCKER_FILING_TYPES, BLOCKER_FILING_STATUSES_AND_ADDITIONAL, []),
        ('general_user_historical_corps', Business.State.HISTORICAL, ['BC', 'BEN', 'CC', 'ULC'], 'general',
         [BASIC_USER], BLOCKER_FILING_TYPES, BLOCKER_FILING_STATUSES_AND_ADDITIONAL, []),
        ('general_user_historical_llc', Business.State.HISTORICAL, ['LLC'], 'general', [BASIC_USER],
         BLOCKER_FILING_TYPES, BLOCKER_FILING_STATUSES_AND_ADDITIONAL, []),
        ('general_user_historical_firms', Business.State.HISTORICAL, ['SP', 'GP'], 'general', [BASIC_USER],
         BLOCKER_FILING_TYPES, BLOCKER_FILING_STATUSES_AND_ADDITIONAL, []),
    ]
)
def test_allowed_filings_blocker_filing_specific_incomplete(monkeypatch, app, session, jwt, test_name, state,
                                                            legal_types, username, roles, filing_types, filing_statuses,
                                                            expected):
    """Assert that get allowed returns valid filings when business has blocker filings.

       A blocker filing in this instance is any filing incomplete filing where filing type is an alteration or a
       correction.  Note that this should also test unexpected incomplete status values.
    """
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        monkeypatch.setattr('flask.request.headers.get', mock_auth)

        for legal_type in legal_types:
            for filing_status in filing_statuses:
                for filing_type in filing_types:
                    business = create_business(legal_type, state)
                    filing_dict = FILING_DATA.get(filing_type, None)
                    create_incomplete_filing(business=business,
                                                      filing_name=filing_type,
                                                      filing_status=filing_status,
                                                      filing_dict=filing_dict,
                                                      filing_type=filing_type)
                    allowed_filing_types = get_allowed_filings(business, state, legal_type, jwt)
                    assert allowed_filing_types == expected


@pytest.mark.parametrize(
    'test_name,state,legal_types,username,roles,expected',
    [
        # active business - staff user
        ('staff_active_cp', Business.State.ACTIVE, ['CP'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.ADMN_FRZE,
                          FilingKey.AR_CP,
                          FilingKey.COA_CP,
                          FilingKey.COD_CP,
                          FilingKey.CORRCTN,
                          FilingKey.COURT_ORDER,
                          FilingKey.VOL_DISS,
                          FilingKey.ADM_DISS,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER,
                          FilingKey.SPECIAL_RESOLUTION])),
        ('staff_active_corps', Business.State.ACTIVE, ['BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.ADMN_FRZE,
                          FilingKey.ALTERATION,
                          FilingKey.AR_CORPS,
                          FilingKey.COA_CORPS,
                          FilingKey.COD_CORPS,
                          FilingKey.CONTINUATION_OUT,
                          FilingKey.CORRCTN,
                          FilingKey.COURT_ORDER,
                          FilingKey.VOL_DISS,
                          FilingKey.ADM_DISS,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER,
                          FilingKey.TRANSITION])),
        ('staff_active_llc', Business.State.ACTIVE, ['LLC'], 'staff', [STAFF_ROLE], []),
        ('staff_active_firms', Business.State.ACTIVE, ['SP', 'GP'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.ADMN_FRZE,
                          FilingKey.CONV_FIRMS,
                          FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER])),

        # active business - general user
        ('general_user_cp', Business.State.ACTIVE, ['CP'], 'general', [BASIC_USER],
         expected_lookup([FilingKey.AR_CP,
                          FilingKey.COA_CP,
                          FilingKey.COD_CP,
                          FilingKey.VOL_DISS,
                          FilingKey.SPECIAL_RESOLUTION])),
        ('general_user_corps', Business.State.ACTIVE, ['BC', 'BEN', 'CC', 'ULC'], 'general', [BASIC_USER],
         expected_lookup([FilingKey.ALTERATION,
                          FilingKey.AR_CORPS,
                          FilingKey.COA_CORPS,
                          FilingKey.COD_CORPS,
                          FilingKey.VOL_DISS,
                          FilingKey.TRANSITION])),
        ('general_user_llc', Business.State.ACTIVE, ['LLC'], 'general', [BASIC_USER], []),
        ('general_user_firms', Business.State.ACTIVE, ['SP', 'GP'], 'general', [BASIC_USER], []),

        # historical business - staff user
        ('staff_historical_cp', Business.State.HISTORICAL, ['CP'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER])),
        ('staff_historical_corps', Business.State.HISTORICAL, ['BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER,
                          FilingKey.RESTRN_FULL_CORPS,
                          FilingKey.RESTRN_LTD_CORPS])),
        ('staff_historical_llc', Business.State.HISTORICAL, ['LLC'], 'staff', [STAFF_ROLE], []),
        ('staff_historical_firms', Business.State.HISTORICAL, ['SP', 'GP'], 'staff', [STAFF_ROLE],
         expected_lookup([FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER])),

        # historical business - general user
        ('general_user_historical_cp', Business.State.HISTORICAL, ['CP'], 'general', [BASIC_USER], []),
        ('general_user_historical_corps', Business.State.HISTORICAL, ['BC', 'BEN', 'CC', 'ULC'], 'general',
         [BASIC_USER], []),
        ('general_user_historical_llc', Business.State.HISTORICAL, ['LLC'], 'general', [BASIC_USER], []),
        ('general_user_historical_firms', Business.State.HISTORICAL, ['SP', 'GP'], 'general', [BASIC_USER], []),
    ]
)
def test_allowed_filings_warnings(monkeypatch, app, session, jwt, test_name, state, legal_types, username, roles, expected):
    """Assert that get allowed returns valid filings when business has warnings."""
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        monkeypatch.setattr('flask.request.headers.get', mock_auth)
        for legal_type in legal_types:
            business = create_business(legal_type, state)
            if legal_type in ('SP', 'GP') and state == Business.State.ACTIVE:
                business.warnings = MISSING_BUSINESS_INFO_WARNINGS
            filing_types = get_allowed_filings(business, state, legal_type, jwt)
            assert filing_types == expected



@pytest.mark.parametrize(
    'test_name,state,legal_types,username,roles,state_filing_types,state_filing_sub_types,expected',
    [
        # active business - staff user
        ('staff_active_cp_unaffected', Business.State.ACTIVE, ['CP'], 'staff', [STAFF_ROLE],
         ['restoration', 'restoration', None, 'restoration'],
         ['limitedRestoration', 'limitedRestorationExtension', None, 'fullRestoration'],
         expected_lookup([FilingKey.ADMN_FRZE,
                          FilingKey.AR_CP,
                          FilingKey.COA_CP,
                          FilingKey.COD_CP,
                          FilingKey.CORRCTN,
                          FilingKey.COURT_ORDER,
                          FilingKey.VOL_DISS,
                          FilingKey.ADM_DISS,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER,
                          FilingKey.SPECIAL_RESOLUTION])),

        ('staff_active_corps_valid_state_filing_success', Business.State.ACTIVE, ['BC', 'BEN', 'CC', 'ULC'], 'staff',
         [STAFF_ROLE], ['restoration', 'restoration'], ['limitedRestoration', 'limitedRestorationExtension'],
         expected_lookup([FilingKey.ADMN_FRZE,
                          FilingKey.ALTERATION,
                          FilingKey.AR_CORPS,
                          FilingKey.COA_CORPS,
                          FilingKey.COD_CORPS,
                          FilingKey.CONTINUATION_OUT,
                          FilingKey.CORRCTN,
                          FilingKey.COURT_ORDER,
                          FilingKey.VOL_DISS,
                          FilingKey.ADM_DISS,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER,
                          FilingKey.TRANSITION,
                          FilingKey.RESTRN_LTD_EXT_CORPS,
                          FilingKey.RESTRN_LTD_TO_FULL_CORPS])),
        ('staff_active_corps_valid_state_filing_fail', Business.State.ACTIVE, ['BC', 'BEN', 'CC', 'ULC'], 'staff',
         [STAFF_ROLE], [None, 'restoration'], [None, 'fullRestoration'],
         expected_lookup([FilingKey.ADMN_FRZE,
                          FilingKey.ALTERATION,
                          FilingKey.AR_CORPS,
                          FilingKey.COA_CORPS,
                          FilingKey.COD_CORPS,
                          FilingKey.CONTINUATION_OUT,
                          FilingKey.CORRCTN,
                          FilingKey.COURT_ORDER,
                          FilingKey.VOL_DISS,
                          FilingKey.ADM_DISS,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER,
                          FilingKey.TRANSITION])),
        ('staff_active_llc_valid_state_filing_success', Business.State.ACTIVE, ['LLC'], 'staff', [STAFF_ROLE],
         ['restoration', 'restoration'], ['limitedRestoration', 'limitedRestorationExtension'], []),
        ('staff_active_llc_valid_state_filing_fail', Business.State.ACTIVE, ['LLC'], 'staff', [STAFF_ROLE],
         [None, 'restoration'], [None, 'fullRestoration'], []),

        ('staff_active_firms_unaffected', Business.State.ACTIVE, ['SP', 'GP'], 'staff', [STAFF_ROLE],
         ['putBackOn', None], [None, None],
         expected_lookup([FilingKey.ADMN_FRZE,
                          FilingKey.CHANGE_OF_REGISTRATION,
                          FilingKey.CONV_FIRMS,
                          FilingKey.CORRCTN_FIRMS,
                          FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER])),

        # active business - general user
        ('general_user_cp_unaffected', Business.State.ACTIVE, ['CP'], 'general', [BASIC_USER],
         ['restoration', 'restoration', None, 'restoration'],
         ['limitedRestoration', 'limitedRestorationExtension', None, 'fullRestoration'],
         expected_lookup([FilingKey.AR_CP,
                          FilingKey.COA_CP,
                          FilingKey.COD_CP,
                          FilingKey.VOL_DISS,
                          FilingKey.SPECIAL_RESOLUTION])),
        ('general_user_corps_unaffected', Business.State.ACTIVE, ['BC', 'BEN', 'CC', 'ULC'], 'general', [BASIC_USER],
         ['restoration', 'restoration', None, 'restoration'],
         ['limitedRestoration', 'limitedRestorationExtension', None, 'fullRestoration'],
         expected_lookup([FilingKey.ALTERATION,
                          FilingKey.AR_CORPS,
                          FilingKey.COA_CORPS,
                          FilingKey.COD_CORPS,
                          FilingKey.VOL_DISS,
                          FilingKey.TRANSITION])),
        ('general_user_llc_unaffected', Business.State.ACTIVE, ['LLC'], 'general', [BASIC_USER],
         ['restoration', 'restoration', None, 'restoration'],
         ['limitedRestoration', 'limitedRestorationExtension', None, 'fullRestoration'], []),
        ('general_user_firms_unaffected', Business.State.ACTIVE, ['SP', 'GP'], 'general', [BASIC_USER],
         ['putBackOn', None], [None, None],
         expected_lookup([FilingKey.CHANGE_OF_REGISTRATION])),

        # historical business - staff user
        ('staff_historical_cp_unaffected', Business.State.HISTORICAL, ['CP'], 'staff', [STAFF_ROLE],
         ['dissolution', None], [None, None],
         expected_lookup([FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER])),
        ('staff_historical_cp_invalid_state_filing_fail', Business.State.HISTORICAL, ['CP'], 'staff', [STAFF_ROLE],
         ['continuationIn'], [None],
         expected_lookup([FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER])),
        ('staff_historical_corps_valid_state_filing_success', Business.State.HISTORICAL, ['BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE],
         ['putBackOn'], [None],
         expected_lookup([FilingKey.COURT_ORDER,
                          FilingKey.PUT_BACK_ON,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER,
                          FilingKey.RESTRN_FULL_CORPS,
                          FilingKey.RESTRN_LTD_CORPS])),
        ('staff_historical_corps_unaffected', Business.State.HISTORICAL, ['BC', 'BEN', 'CC', 'ULC'], 'staff', [STAFF_ROLE],
         ['dissolution', None], [None, None],
         expected_lookup([FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER,
                          FilingKey.RESTRN_FULL_CORPS,
                          FilingKey.RESTRN_LTD_CORPS])),
        ('staff_historical_corps_invalid_state_filing_fail', Business.State.HISTORICAL, ['BC', 'BEN', 'CC', 'ULC'],
         'staff', [STAFF_ROLE], ['continuationIn'], [None],
         expected_lookup([FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER])),
        ('staff_historical_llc_unaffected', Business.State.HISTORICAL, ['LLC'], 'staff', [STAFF_ROLE],
         ['dissolution', None], [None, None], []),
        ('staff_historical_firms_unaffected', Business.State.HISTORICAL, ['SP', 'GP'], 'staff', [STAFF_ROLE],
         ['dissolution', None], [None, None],
         expected_lookup([FilingKey.COURT_ORDER,
                          FilingKey.REGISTRARS_NOTATION,
                          FilingKey.REGISTRARS_ORDER])),

        # historical business - general user
        ('general_user_historical_cp_unaffected', Business.State.HISTORICAL, ['CP'], 'general', [BASIC_USER],
         ['dissolution', 'continuationIn', None], [None, None, None], []),
        ('general_user_historical_corps_unaffected', Business.State.HISTORICAL, ['BC', 'BEN', 'CC', 'ULC'], 'general',
         [BASIC_USER], ['dissolution', 'continuationIn', None], [None, None, None], []),
        ('general_user_historical_llc_unaffected', Business.State.HISTORICAL, ['LLC'], 'general', [BASIC_USER],
         ['dissolution', None], [None, None], []),
        ('general_user_historical_firms_unaffected', Business.State.HISTORICAL, ['SP', 'GP'], 'general', [BASIC_USER],
         ['dissolution', None], [None, None], [])
    ]
)
def test_allowed_filings_state_filing_check(monkeypatch, app, session, jwt, test_name, state, legal_types, username,
                                            roles, state_filing_types, state_filing_sub_types, expected):
    """Assert that get allowed returns valid filings when validStateFilings or invalidStateFilings blocker is defined.

       A filing with validStateFiling defined should only return a target filing if the business state filing matches
       one of the state filing types defined in validStateFiling.

       A filing with invalidStateFiling defined should only return a target filing if the business state filing does
       not match one of the state filing types defined in invalidStateFiling.
    """
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        monkeypatch.setattr('flask.request.headers.get', mock_auth)

        for legal_type in legal_types:
            for idx, state_filing_type in enumerate(state_filing_types):
                business = create_business(legal_type, state)
                state_filing_sub_type = state_filing_sub_types[idx]
                if state_filing_type:
                    state_filing = create_state_filing(business, state_filing_type, state_filing_sub_type)
                    business.state_filing_id = state_filing.id
                    business.save()
                allowed_filing_types = get_allowed_filings(business, state, legal_type, jwt)
                assert allowed_filing_types == expected


def create_business(legal_type, state):
    """Create a business."""
    identifier = (f'BC{random.SystemRandom().getrandbits(0x58)}')[:9]
    business = factory_business(identifier=identifier,
                                entity_type=legal_type,
                                state=state)
    return business


def create_incomplete_filing(business,
                             filing_name,
                             filing_status,
                             filing_dict:dict=copy.deepcopy(ANNUAL_REPORT),
                             filing_type=None):
    """Create an incomplete filing of a given status."""
    filing_dict['filing']['header']['name'] = filing_name
    if filing_dict:
        filing_dict = copy.deepcopy(filing_dict)
    filing = factory_filing(business=business, data_dict=filing_dict)
    filing.skip_status_listener = True
    filing._status = filing_status
    filing._filing_type = filing_type
    return filing


def create_state_filing(business, filing_type, filing_sub_type=None):
    """Create a state filing."""
    filing_key = filing_type
    if filing_sub_type:
        filing_key = f'{filing_type}.{filing_sub_type}'
    filing_dict = copy.deepcopy(FILING_DATA.get(filing_key, None))
    filing_dict['filing']['header']['name'] = filing_type
    if filing_sub_type:
        filing_sub_type_key = Filing.FILING_SUB_TYPE_KEYS.get(filing_type, None)
        filing_dict['filing'][filing_type][filing_sub_type_key] = filing_sub_type
    state_filing = factory_completed_filing(business=business,
                                            data_dict=filing_dict,
                                            filing_type=filing_type,
                                            filing_sub_type=filing_sub_type)
    return state_filing
