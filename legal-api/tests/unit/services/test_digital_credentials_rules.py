# Copyright © 2024 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for the Digital Credentials Rules service.

Test suite to ensure that the Digital Credentials Rules service is working as expected.
"""
from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest
import jwt as pyjwt
from legal_api.models.business import Business
from legal_api.models.party import Party
from legal_api.models.party_role import PartyRole
from legal_api.models.user import User
from legal_api.services import DigitalCredentialsRulesService
from legal_api.services.authz import PUBLIC_USER, STAFF_ROLE, are_digital_credentials_allowed
from tests.unit.services.utils import create_business, create_party_role, create_test_user, helper_create_jwt
from tests.unit.models import factory_user, factory_completed_filing


@pytest.fixture(scope='module')
def rules():
    return DigitalCredentialsRulesService()


@pytest.mark.parametrize(
    'test_user, expected',
    [
        (Party(**{'first_name': 'First', 'last_name': 'Last'}),
         {'first_name': 'first', 'last_name': 'last'}),
        (Party(**{'first_name': 'First', 'middle_initial': 'M',
         'last_name': 'Last'}), {'first_name': 'first m', 'last_name': 'last'}),
        (User(**{'firstname': 'First', 'lastname': 'Last'}),
         {'first_name': 'first', 'last_name': 'last'}),
        (User(**{'firstname': 'First', 'middlename': 'M', 'lastname': 'Last'}),
         {'first_name': 'first m', 'last_name': 'last'}),
        (User(), {'first_name': '', 'last_name': ''}),
        (Party(), {'first_name': '', 'last_name': ''}),
    ]
)
def test_formatted_user(app, session, rules, test_user, expected):
    """Assert that the user is formatted correctly."""

    assert rules.formatted_user(test_user) == expected


@patch('legal_api.models.User.find_by_jwt_token',
       return_value=None)
@patch('legal_api.services.digital_credentials_rules.DigitalCredentialsRulesService.is_self_registered_owner_operator',
       return_value=True)
def test_are_digital_credentials_allowed_false_when_no_user(monkeypatch, app, session, jwt, rules):
    token_json = {'username': 'test'}
    token = helper_create_jwt(
        jwt, roles=[PUBLIC_USER], username=token_json['username'])
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        jwt.get_token_auth_header = MagicMock(return_value=token)
        pyjwt.decode = MagicMock(return_value=token_json)
        monkeypatch.setattr('flask.request.headers.get', mock_auth)

        user = User.find_by_jwt_token(jwt)
        business = create_business('SP', Business.State.ACTIVE)
        assert rules.are_digital_credentials_allowed(user, business) is False


@patch('legal_api.models.User.find_by_jwt_token',
       return_value=User(id=1, login_source='NOT_BCSC'))
@patch('legal_api.services.digital_credentials_rules.DigitalCredentialsRulesService.is_self_registered_owner_operator',
       return_value=True)
def test_are_digital_credentials_allowed_false_when_login_source_not_bcsc(monkeypatch, app, session, jwt, rules):
    token_json = {'username': 'test'}
    token = helper_create_jwt(
        jwt, roles=[PUBLIC_USER], username=token_json['username'])
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        jwt.get_token_auth_header = MagicMock(return_value=token)
        pyjwt.decode = MagicMock(return_value=token_json)
        monkeypatch.setattr('flask.request.headers.get', mock_auth)

        user = User.find_by_jwt_token(jwt)
        business = create_business('SP', Business.State.ACTIVE)
        assert rules.are_digital_credentials_allowed(user, business) is False


@patch('legal_api.models.User.find_by_jwt_token',
       return_value=User(id=1, login_source='BCSC'))
@patch('legal_api.services.digital_credentials_rules.DigitalCredentialsRulesService.is_self_registered_owner_operator',
       return_value=True)
def test_are_digital_credentials_allowed_false_when_wrong_business_type(monkeypatch, app, session, jwt, rules):
    token_json = {'username': 'test'}
    token = helper_create_jwt(
        jwt, roles=[PUBLIC_USER], username=token_json['username'])
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        jwt.get_token_auth_header = MagicMock(return_value=token)
        pyjwt.decode = MagicMock(return_value=token_json)
        monkeypatch.setattr('flask.request.headers.get', mock_auth)

        user = User.find_by_jwt_token(jwt)
        business = create_business('GP', Business.State.ACTIVE)
        assert rules.are_digital_credentials_allowed(user, business) is False


@patch('legal_api.models.User.find_by_jwt_token',
       return_value=User(id=1, login_source='BCSC'))
@patch('legal_api.services.digital_credentials_rules.DigitalCredentialsRulesService.is_self_registered_owner_operator',
       return_value=False)
def test_are_digital_credentials_allowed_false_when_not_owner_operator(monkeypatch, app, session, jwt):
    token_json = {'username': 'test'}
    token = helper_create_jwt(
        jwt, roles=[PUBLIC_USER], username=token_json['username'])
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        jwt.get_token_auth_header = MagicMock(return_value=token)
        pyjwt.decode = MagicMock(return_value=token_json)
        monkeypatch.setattr('flask.request.headers.get', mock_auth)

        business = create_business('SP', Business.State.ACTIVE)
        assert are_digital_credentials_allowed(business, jwt) is False


@patch('legal_api.models.User.find_by_jwt_token',
       return_value=User(id=1, login_source='BCSC'))
@patch('legal_api.services.digital_credentials_rules.DigitalCredentialsRulesService.is_self_registered_owner_operator',
       return_value=True)
def test_are_digital_credentials_allowed_true(monkeypatch, app, session, jwt, rules):
    token_json = {'username': 'test'}
    token = helper_create_jwt(
        jwt, roles=[PUBLIC_USER], username=token_json['username'])
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        jwt.get_token_auth_header = MagicMock(return_value=token)
        pyjwt.decode = MagicMock(return_value=token_json)
        monkeypatch.setattr('flask.request.headers.get', mock_auth)

        user = User.find_by_jwt_token(jwt)
        business = create_business('SP', Business.State.ACTIVE)
        assert rules.are_digital_credentials_allowed(user, business) is True


@patch('legal_api.services.authz.get_registration_filing', return_value=None)
def test_is_self_registered_owner_operator_false_when_no_registration_filing(app, session, rules):
    user = factory_user(username='test', firstname='Test', lastname='User')
    business = create_business('SP', Business.State.ACTIVE)

    assert rules.is_self_registered_owner_operator(user, business) is False


def test_is_self_registered_owner_operator_false_when_no_proprietors(app, session, rules):
    user = factory_user(username='test', firstname='Test', lastname='User')
    business = create_business('SP', Business.State.ACTIVE)
    completing_party_role = create_party_role(
        PartyRole.RoleTypes.COMPLETING_PARTY,
        **create_test_user()
    )
    filing = factory_completed_filing(
        business=business,
        data_dict={'filing': {'header': {'name': 'registration'}}},
        filing_date=datetime.utcnow(), filing_type='registration'
    )
    filing.filing_party_roles.append(completing_party_role)
    filing.submitter_id = user.id
    filing.save()

    assert rules.is_self_registered_owner_operator(user, business) is False


@patch('legal_api.models.PartyRole.get_parties_by_role',
       return_value=[PartyRole(role=PartyRole.RoleTypes.PROPRIETOR.value)])
def test_is_self_registered_owner_operator_false_when_no_proprietor(app, session, rules):
    user = factory_user(username='test', firstname='Test', lastname='User')
    business = create_business('SP', Business.State.ACTIVE)
    completing_party_role = create_party_role(
        PartyRole.RoleTypes.COMPLETING_PARTY,
        **create_test_user()
    )
    filing = factory_completed_filing(
        business=business,
        data_dict={'filing': {'header': {'name': 'registration'}}},
        filing_date=datetime.utcnow(), filing_type='registration'
    )
    filing.filing_party_roles.append(completing_party_role)
    filing.submitter_id = user.id
    filing.save()

    assert rules.is_self_registered_owner_operator(user, business) is False


@patch('legal_api.models.PartyRole.get_party_roles_by_filing', return_value=None)
def test_is_self_registered_owner_operator_false_when_no_completing_parties(app, session, rules):
    user = factory_user(username='test', firstname='Test', lastname='User')
    business = create_business('SP', Business.State.ACTIVE)
    proprietor_party_role = create_party_role(
        PartyRole.RoleTypes.PROPRIETOR,
        **create_test_user()
    )
    proprietor_party_role.business_id = business.id
    proprietor_party_role.save()

    assert rules.is_self_registered_owner_operator(user, business) is False


@patch('legal_api.models.PartyRole.get_party_roles_by_filing',
       return_value=[PartyRole(role=PartyRole.RoleTypes.COMPLETING_PARTY.value)])
def test_is_self_registered_owner_operator_false_when_no_completing_party(app, session, rules):
    user = factory_user(username='test', firstname='Test', lastname='User')
    business = create_business('SP', Business.State.ACTIVE)
    proprietor_party_role = create_party_role(
        PartyRole.RoleTypes.PROPRIETOR,
        **create_test_user()
    )
    proprietor_party_role.business_id = business.id
    proprietor_party_role.save()

    assert rules.is_self_registered_owner_operator(user, business) is False


def test_is_self_registered_owner_operator_false_when_parties_not_matching(app, session, rules):
    user = factory_user(username='test', firstname='Test1', lastname='User1')
    business = create_business('SP', Business.State.ACTIVE)
    completing_party_role = create_party_role(
        PartyRole.RoleTypes.COMPLETING_PARTY,
        **create_test_user(suffix='1')
    )
    filing = factory_completed_filing(
        business=business,
        data_dict={'filing': {'header': {'name': 'registration'}}},
        filing_date=datetime.utcnow(), filing_type='registration'
    )
    filing.filing_party_roles.append(completing_party_role)
    filing.submitter_id = user.id
    filing.save()

    proprietor_party_role = create_party_role(
        PartyRole.RoleTypes.PROPRIETOR,
        **create_test_user(suffix='2')
    )
    proprietor_party_role.business_id = business.id
    proprietor_party_role.save()

    assert rules.is_self_registered_owner_operator(user, business) is False


def test_is_self_registered_owner_operator_false_when_user_not_matching(app, session, rules):
    user = factory_user(username='test', firstname='Test1', lastname='User1')
    business = create_business('SP', Business.State.ACTIVE)
    completing_party_role = create_party_role(
        PartyRole.RoleTypes.COMPLETING_PARTY,
        **create_test_user(suffix='2')
    )
    filing = factory_completed_filing(
        business=business,
        data_dict={'filing': {'header': {'name': 'registration'}}},
        filing_date=datetime.utcnow(), filing_type='registration'
    )
    filing.filing_party_roles.append(completing_party_role)
    filing.submitter_id = user.id
    filing.save()

    proprietor_party_role = create_party_role(
        PartyRole.RoleTypes.PROPRIETOR,
        **create_test_user(suffix='2')
    )
    proprietor_party_role.business_id = business.id
    proprietor_party_role.save()

    assert rules.is_self_registered_owner_operator(
        business, user) is False


def test_is_self_registered_owner_operator_false_when_proprietor_uses_middle_name_field_and_user_does_not(app, session, rules):
    user = factory_user(username='test', firstname='Test', lastname='User')
    business = create_business('SP', Business.State.ACTIVE)
    completing_party_role = create_party_role(
        PartyRole.RoleTypes.COMPLETING_PARTY,
        **create_test_user(first_name='TEST', last_name='USER', default_middle=False)
    )
    filing = factory_completed_filing(
        business=business,
        data_dict={'filing': {'header': {'name': 'registration'}}},
        filing_date=datetime.utcnow(), filing_type='registration'
    )
    filing.filing_party_roles.append(completing_party_role)
    filing.submitter_id = user.id
    filing.save()

    proprietor_party_role = create_party_role(
        PartyRole.RoleTypes.PROPRIETOR,
        **create_test_user()
    )
    proprietor_party_role.business_id = business.id
    proprietor_party_role.save()

    assert rules.is_self_registered_owner_operator(user, business) is False


def test_is_self_registered_owner_operator_true_when_proprietor_and_user_uses_middle_name_field(app, session, rules):
    user = factory_user(username='test', firstname='Test Tu', lastname='User')
    business = create_business('SP', Business.State.ACTIVE)
    completing_party_role = create_party_role(
        PartyRole.RoleTypes.COMPLETING_PARTY,
        **create_test_user(first_name='TEST TU', last_name='USER', default_middle=False)
    )
    filing = factory_completed_filing(
        business=business,
        data_dict={'filing': {'header': {'name': 'registration'}}},
        filing_date=datetime.utcnow(), filing_type='registration'
    )
    filing.filing_party_roles.append(completing_party_role)
    filing.submitter_id = user.id
    filing.save()

    proprietor_party_role = create_party_role(
        PartyRole.RoleTypes.PROPRIETOR,
        **create_test_user(first_name='TEST', middle_initial='TU', last_name='USER')
    )
    proprietor_party_role.business_id = business.id
    proprietor_party_role.save()

    assert rules.is_self_registered_owner_operator(user, business) is True


def test_is_self_registered_owner_operator_true(app, session, rules):
    user = factory_user(username='test', firstname='Test', lastname='User')
    business = create_business('SP', Business.State.ACTIVE)
    completing_party_role = create_party_role(
        PartyRole.RoleTypes.COMPLETING_PARTY,
        **create_test_user(first_name='TEST', last_name='USER', default_middle=False)
    )
    filing = factory_completed_filing(
        business=business,
        data_dict={'filing': {'header': {'name': 'registration'}}},
        filing_date=datetime.utcnow(), filing_type='registration'
    )
    filing.filing_party_roles.append(completing_party_role)
    filing.submitter_id = user.id
    filing.save()

    proprietor_party_role = create_party_role(
        PartyRole.RoleTypes.PROPRIETOR,
        **create_test_user(first_name='TEST', last_name='USER', default_middle=False)
    )
    proprietor_party_role.business_id = business.id
    proprietor_party_role.save()
    proprietor_party_role.party.middle_initial = None
    proprietor_party_role.party.save()
    assert rules.is_self_registered_owner_operator(user, business) is True
