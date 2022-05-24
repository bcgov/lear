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
from http import HTTPStatus

import pytest
from flask import jsonify
from legal_api.models.business import Business

from legal_api.services.authz import BASIC_USER, COLIN_SVC_ROLE, STAFF_ROLE, authorized, get_allowed, is_allowed
from tests import integration_authorization, not_github_ci

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
    ('court_order_not_allowed', 'CP0001237', 'CP1234567', [BASIC_USER], None, ['court_order'],
     HTTPStatus.METHOD_NOT_ALLOWED),
    ('registrars_notation_not_allowed', 'CP0001237', 'CP1234567', [BASIC_USER], None, ['registrars_notation'],
     HTTPStatus.METHOD_NOT_ALLOWED),
    ('registrars_order_not_allowed', 'CP0001237', 'CP1234567', [BASIC_USER], None, ['registrars_order'],
     HTTPStatus.METHOD_NOT_ALLOWED),
]


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
    ('court_order_not_allowed', 'CP0001237', 'CP1234567', [BASIC_USER], None, ['court_order'],
     HTTPStatus.METHOD_NOT_ALLOWED),
    ('registrars_notation_not_allowed', 'CP0001237', 'CP1234567', [BASIC_USER], None, ['registrars_notation'],
     HTTPStatus.METHOD_NOT_ALLOWED),
    ('registrars_order_not_allowed', 'CP0001237', 'CP1234567', [BASIC_USER], None, ['registrars_order'],
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
    'test_name,state,legal_type,username,roles,expected',
    [
        # active business
        ('staff_active_cp', Business.State.ACTIVE, 'CP', 'staff', [STAFF_ROLE],
         ['annualReport', 'changeOfAddress', 'changeOfDirectors', 'correction',
            'courtOrder', 'dissolution', 'incorporationApplication',
            'specialResolution', 'registrarsNotation', 'registrarsOrder']),
        ('staff_active_bc', Business.State.ACTIVE, 'BC', 'staff', [STAFF_ROLE],
         ['alteration', 'courtOrder', 'dissolution', 'incorporationApplication',
            'transition', 'registrarsNotation', 'registrarsOrder']),
        ('staff_active_ben', Business.State.ACTIVE, 'BEN', 'staff', [STAFF_ROLE],
         ['alteration', 'annualReport', 'changeOfAddress', 'changeOfDirectors', 'conversion', 'correction',
            'courtOrder', 'dissolution', 'incorporationApplication',
            'transition', 'registrarsNotation', 'registrarsOrder']),
        ('staff_active_cc', Business.State.ACTIVE, 'CC', 'staff', [STAFF_ROLE],
         ['courtOrder', 'dissolution',
         'registrarsNotation', 'registrarsOrder']),
        ('staff_active_ulc', Business.State.ACTIVE, 'ULC', 'staff', [STAFF_ROLE],
         ['alteration', 'courtOrder', 'dissolution',
         'registrarsNotation', 'registrarsOrder']),
        ('staff_active_llc', Business.State.ACTIVE, 'LLC', 'staff', [STAFF_ROLE],
         ['courtOrder', 'dissolution',
         'registrarsNotation', 'registrarsOrder']),
        ('staff_active_sp', Business.State.ACTIVE, 'SP', 'staff', [STAFF_ROLE],
         ['changeOfRegistration', 'conversion', 'dissolution', 'registration']),
        ('staff_active_gp', Business.State.ACTIVE, 'GP', 'staff', [STAFF_ROLE],
         ['changeOfRegistration', 'conversion', 'dissolution', 'registration']),

        ('user_active_cp', Business.State.ACTIVE, 'CP', 'user', [BASIC_USER],
         ['annualReport', 'changeOfAddress', 'changeOfDirectors',
          'dissolution', 'incorporationApplication', 'specialResolution']),
        ('user_active_bc', Business.State.ACTIVE, 'BC', 'user', [BASIC_USER],
         ['alteration', 'dissolution', 'incorporationApplication', 'transition']),
        ('user_active_ben', Business.State.ACTIVE, 'BEN', 'user', [BASIC_USER],
         ['alteration', 'annualReport', 'changeOfAddress', 'changeOfDirectors',
            'dissolution', 'incorporationApplication', 'transition']),
        ('user_active_cc', Business.State.ACTIVE, 'CC', 'user', [BASIC_USER], ['dissolution']),
        ('user_active_ulc', Business.State.ACTIVE, 'ULC', 'user', [BASIC_USER], ['alteration', 'dissolution']),
        ('user_active_llc', Business.State.ACTIVE, 'LLC', 'user', [BASIC_USER], ['dissolution']),
        ('user_active_sp', Business.State.ACTIVE, 'SP', 'user', [BASIC_USER], ['changeOfRegistration', 'dissolution', 'registration']),
        ('user_active_gp', Business.State.ACTIVE, 'GP', 'user', [BASIC_USER], ['changeOfRegistration', 'dissolution', 'registration']),

        # historical business
        ('staff_historical_cp', Business.State.HISTORICAL, 'CP', 'staff', [STAFF_ROLE],
         ['courtOrder', 'registrarsNotation', 'registrarsOrder',
         {'restoration': ['fullRestoration']}]),
        ('staff_historical_bc', Business.State.HISTORICAL, 'BC', 'staff', [STAFF_ROLE],
         ['courtOrder', 'registrarsNotation', 'registrarsOrder',
         {'restoration': ['fullRestoration', 'limitedRestoration']}]),
        ('staff_historical_ben', Business.State.HISTORICAL, 'BEN', 'staff', [STAFF_ROLE],
         ['courtOrder', 'registrarsNotation', 'registrarsOrder',
         {'restoration': ['fullRestoration', 'limitedRestoration']}]),
        ('staff_historical_cc', Business.State.HISTORICAL, 'CC', 'staff', [STAFF_ROLE],
         ['courtOrder', 'registrarsNotation', 'registrarsOrder',
         {'restoration': ['fullRestoration', 'limitedRestoration']}]),
        ('staff_historical_ulc', Business.State.HISTORICAL, 'ULC', 'staff', [STAFF_ROLE],
         ['courtOrder', 'registrarsNotation', 'registrarsOrder',
         {'restoration': ['fullRestoration', 'limitedRestoration']}]),
        ('staff_historical_llc', Business.State.HISTORICAL, 'LLC', 'staff', [STAFF_ROLE],
         ['courtOrder', 'registrarsNotation', 'registrarsOrder',
         {'restoration': ['fullRestoration', 'limitedRestoration']}]),

        ('user_historical_llc', Business.State.HISTORICAL, 'LLC', 'user', [BASIC_USER], []),
    ]
)
def test_get_allowed(monkeypatch, app, jwt, test_name, state, legal_type, username, roles, expected):
    """Assert that get allowed returns valid filings."""
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        monkeypatch.setattr('flask.request.headers.get', mock_auth)
        filing_types = get_allowed(state, legal_type, jwt)
        assert filing_types == expected


@pytest.mark.parametrize(
    'test_name,state,filing_type,sub_filing_type,legal_types,username,roles,expected',
    [
        # active business
        ('staff_active_allowed', Business.State.ACTIVE, 'alteration', None,
         ['BC', 'BEN', 'ULC'], 'staff', [STAFF_ROLE], True),
        ('staff_active', Business.State.ACTIVE, 'alteration', None,
         ['CP', 'CC', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_active_allowed', Business.State.ACTIVE, 'annualReport', None,
         ['CP', 'BEN'], 'staff', [STAFF_ROLE], True),
        ('staff_active', Business.State.ACTIVE, 'annualReport', None,
         ['BC', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_active_allowed', Business.State.ACTIVE, 'changeOfAddress', None,
         ['CP', 'BEN'], 'staff', [STAFF_ROLE], True),
        ('staff_active', Business.State.ACTIVE, 'changeOfAddress', None,
         ['BC', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_active_allowed', Business.State.ACTIVE, 'changeOfDirectors', None,
         ['CP', 'BEN'], 'staff', [STAFF_ROLE], True),
        ('staff_active', Business.State.ACTIVE, 'changeOfDirectors', None,
         ['BC', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_active_allowed', Business.State.ACTIVE, 'correction', None,
         ['CP', 'BEN'], 'staff', [STAFF_ROLE], True),
        ('staff_active', Business.State.ACTIVE, 'correction', None,
         ['BC', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_active_allowed', Business.State.ACTIVE, 'courtOrder', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], True),

        ('staff_active_allowed', Business.State.ACTIVE, 'dissolution', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC', 'SP', 'GP'], 'staff', [STAFF_ROLE], True),

        ('staff_active_allowed', Business.State.ACTIVE, 'incorporationApplication', None,
         ['CP', 'BC', 'BEN'], 'staff', [STAFF_ROLE], True),

        ('staff_active', Business.State.ACTIVE, 'restoration', 'fullRestoration',
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),
        ('staff_active', Business.State.ACTIVE, 'restoration', 'limitedRestoration',
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_active_allowed', Business.State.ACTIVE, 'specialResolution', None, ['CP'], 'staff', [STAFF_ROLE], True),
        ('staff_active', Business.State.ACTIVE, 'specialResolution', None,
         ['BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_active_allowed', Business.State.ACTIVE, 'transition', None,
         ['BC', 'BEN'], 'staff', [STAFF_ROLE], True),
        ('staff_active', Business.State.ACTIVE, 'transition', None,
         ['CP', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_active_allowed', Business.State.ACTIVE, 'registrarsNotation', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], True),

        ('staff_active_allowed', Business.State.ACTIVE, 'registrarsOrder', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], True),

        ('staff_active_allowed', Business.State.ACTIVE, 'registration', None,
         ['SP', 'GP'], 'staff', [STAFF_ROLE], True),

        ('staff_active_allowed', Business.State.ACTIVE, 'changeOfRegistration', None,
         ['SP', 'GP'], 'staff', [STAFF_ROLE], True),


        ('user_active_allowed', Business.State.ACTIVE, 'alteration', None,
         ['BC', 'BEN', 'ULC'], 'user', [BASIC_USER], True),
        ('user_active', Business.State.ACTIVE, 'alteration', None,
         ['CP', 'CC', 'LLC'], 'user', [BASIC_USER], False),

        ('user_active_allowed', Business.State.ACTIVE, 'annualReport', None, ['CP', 'BEN'], 'user', [BASIC_USER], True),
        ('user_active', Business.State.ACTIVE, 'annualReport', None,
         ['BC', 'CC', 'ULC', 'LLC'], 'user', [BASIC_USER], False),

        ('user_active_allowed', Business.State.ACTIVE, 'changeOfAddress', None,
         ['CP', 'BEN'], 'user', [BASIC_USER], True),
        ('user_active', Business.State.ACTIVE, 'changeOfAddress', None,
         ['BC', 'CC', 'ULC', 'LLC'], 'user', [BASIC_USER], False),

        ('user_active_allowed', Business.State.ACTIVE, 'changeOfDirectors', None,
         ['CP', 'BEN'], 'user', [BASIC_USER], True),
        ('user_active', Business.State.ACTIVE, 'changeOfDirectors', None,
         ['BC', 'CC', 'ULC', 'LLC'], 'user', [BASIC_USER], False),

        ('user_active', Business.State.ACTIVE, 'correction', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'user', [BASIC_USER], False),

        ('user_active', Business.State.ACTIVE, 'courtOrder', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'user', [BASIC_USER], False),

        ('user_active_allowed', Business.State.ACTIVE, 'dissolution', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC', 'SP', 'GP'], 'user', [BASIC_USER], True),

        ('user_active_allowed', Business.State.ACTIVE, 'incorporationApplication', None,
         ['CP', 'BC', 'BEN'], 'user', [BASIC_USER], True),

        ('user_active_allowed', Business.State.ACTIVE, 'registration', None,
         ['SP', 'GP'], 'user', [BASIC_USER], True),

        ('user_active_allowed', Business.State.ACTIVE, 'changeOfRegistration', None,
         ['SP', 'GP'], 'user', [BASIC_USER], True),

        ('user_active', Business.State.ACTIVE, 'restoration', 'fullRestoration',
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'user', [BASIC_USER], False),

        ('user_active', Business.State.ACTIVE, 'restoration', 'limitedRestoration',
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'user', [BASIC_USER], False),

        ('user_active_allowed', Business.State.ACTIVE, 'specialResolution', None, ['CP'], 'user', [BASIC_USER], True),
        ('user_active', Business.State.ACTIVE, 'specialResolution', None,
         ['BC', 'BEN', 'CC', 'ULC', 'LLC'], 'user', [BASIC_USER], False),

        ('user_active_allowed', Business.State.ACTIVE, 'transition', None, ['BC', 'BEN'], 'user', [BASIC_USER], True),
        ('user_active', Business.State.ACTIVE, 'transition', None,
         ['CP', 'CC', 'ULC', 'LLC'], 'user', [BASIC_USER], False),

        ('user_active', Business.State.ACTIVE, 'registrarsNotation', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'user', [BASIC_USER], False),

        ('user_active', Business.State.ACTIVE, 'registrarsOrder', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'user', [BASIC_USER], False),

        # historical business
        ('staff_historical', Business.State.HISTORICAL, 'alteration', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_historical', Business.State.HISTORICAL, 'annualReport', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_historical', Business.State.HISTORICAL, 'changeOfAddress', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_historical', Business.State.HISTORICAL, 'changeOfDirectors', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_historical', Business.State.HISTORICAL, 'correction', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_historical_allowed', Business.State.HISTORICAL, 'courtOrder', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], True),

        ('staff_historical', Business.State.HISTORICAL, 'dissolution', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC', 'SP', 'GP'], 'staff', [STAFF_ROLE], False),

        ('staff_historical', Business.State.HISTORICAL, 'incorporationApplication', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_historical_allowed', Business.State.HISTORICAL, 'restoration', 'fullRestoration',
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], True),

        ('staff_historical_allowed', Business.State.HISTORICAL, 'restoration', 'limitedRestoration',
         ['BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], True),
        ('staff_historical', Business.State.HISTORICAL, 'restoration', 'limitedRestoration',
         ['CP'], 'staff', [STAFF_ROLE], False),

        ('staff_historical', Business.State.HISTORICAL, 'specialResolution', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_historical', Business.State.HISTORICAL, 'transition', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], False),

        ('staff_historical_allowed', Business.State.HISTORICAL, 'registrarsNotation', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], True),

        ('staff_historical_allowed', Business.State.HISTORICAL, 'registrarsOrder', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'staff', [STAFF_ROLE], True),

        ('staff_historical', Business.State.HISTORICAL, 'registration', None,
         ['SP', 'GP'], 'staff', [STAFF_ROLE], False),

        ('staff_historical', Business.State.HISTORICAL, 'changeOfRegistration', None,
         ['SP', 'GP'], 'staff', [STAFF_ROLE], False),


        ('user_historical', Business.State.HISTORICAL, 'alteration', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'user', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'annualReport', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'user', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'changeOfAddress', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'user', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'changeOfDirectors', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'user', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'correction', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'user', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'courtOrder', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'user', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'dissolution', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC', 'SP', 'GP', 'SP', 'GP'], 'user', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'incorporationApplication', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'user', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'restoration', 'fullRestoration',
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'user', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'restoration', 'limitedRestoration',
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'user', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'specialResolution', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'user', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'transition', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'user', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'registrarsNotation', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'user', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'registrarsOrder', None,
         ['CP', 'BC', 'BEN', 'CC', 'ULC', 'LLC'], 'user', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'registration', None,
         ['SP', 'GP'], 'user', [BASIC_USER], False),

        ('user_historical', Business.State.HISTORICAL, 'changeOfRegistration', None,
         ['SP', 'GP'], 'user', [BASIC_USER], False),
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
