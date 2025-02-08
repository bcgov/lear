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
import logging
from unittest.mock import MagicMock, patch
import pytest
import jwt as pyjwt
from legal_api.models.business import Business
from legal_api.models.party import Party
from legal_api.models.party_role import PartyRole
from legal_api.models.user import User
from legal_api.services import DigitalCredentialsRulesService
from legal_api.services.authz import PUBLIC_USER, are_digital_credentials_allowed
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

    assert rules.FormattedUser(test_user).__dict__ == expected


@patch('legal_api.models.User.find_by_jwt_token', return_value=None)
def test_has_general_access_false_when_no_user(monkeypatch, app, session, caplog, jwt, rules):
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
        caplog.set_level(logging.DEBUG)
        user = User.find_by_jwt_token(jwt)

        assert rules._has_general_access(user) is False
        assert 'No user is provided.' in caplog.text


@patch('legal_api.models.User.find_by_jwt_token',
       return_value=User(id=1, login_source='NOT_BCSC'))
def test_has_general_access_false_when_login_source_not_bcsc(monkeypatch, app, session, caplog, jwt, rules):
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
        caplog.set_level(logging.DEBUG)
        user = User.find_by_jwt_token(jwt)

        assert rules._has_general_access(user) is False
        assert 'User is not logged in with BCSC.' in caplog.text


@patch('legal_api.models.User.find_by_jwt_token',
       return_value=User(id=1, login_source='BCSC'))
def test_has_general_access_true(monkeypatch, app, session, jwt, caplog, rules):
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

        assert rules._has_general_access(user) is True


@patch('legal_api.models.User.find_by_jwt_token',
       return_value=User(id=1, login_source='BCSC'))
def test_has_specific_access_false_when_no_business(monkeypatch, app, session, caplog, jwt, rules):
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
        caplog.set_level(logging.DEBUG)
        user = User.find_by_jwt_token(jwt)

        assert rules._has_specific_access(user, None) is False
        assert 'No buisiness is provided.' in caplog.text


@patch('legal_api.models.User.find_by_jwt_token',
       return_value=User(id=1, login_source='BCSC'))
def test_has_specific_access_false_when_wrong_business_type(monkeypatch, app, session, caplog, jwt, rules):
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
        caplog.set_level(logging.DEBUG)
        user = User.find_by_jwt_token(jwt)
        business = create_business(
            Business.LegalTypes.COMP.value, Business.State.ACTIVE)

        assert rules._has_specific_access(user, business) is False
        assert 'No specific access rules are met.' in caplog.text


@pytest.mark.parametrize('legal_type', [
    Business.LegalTypes.SOLE_PROP.value,
    Business.LegalTypes.PARTNERSHIP.value,
    Business.LegalTypes.BCOMP.value,
])
@patch('legal_api.models.User.find_by_jwt_token',
       return_value=User(id=1, login_source='BCSC'))
@patch.object(DigitalCredentialsRulesService, '_is_completing_party_and_has_party_role', return_value=True)
def test_has_specific_access_true_when_correct_business_type(monkeypatch, app, session, legal_type, jwt, rules):
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
        business = create_business(legal_type, Business.State.ACTIVE)

        assert rules._has_specific_access(user, business) is True


@patch('legal_api.models.Filing.get_filings_by_types', return_value=[])
def test_is_completing_party_false_when_no_registration_filing(app, session, caplog, rules):
    user = factory_user(username='test', firstname='Test', lastname='User')
    business = create_business(
        Business.LegalTypes.SOLE_PROP.value, Business.State.ACTIVE)
    caplog.set_level(logging.DEBUG)

    assert rules._is_completing_party(user, business) is False
    assert 'No registration filing found for the business.' in caplog.text


def test_is_completing_party_false_when_no_completing_parties(app, session, caplog, rules):
    user = factory_user(username='test', firstname='Test', lastname='User')
    business = create_business(
        Business.LegalTypes.SOLE_PROP.value, Business.State.ACTIVE)
    # Skip creating a completing party
    filing = factory_completed_filing(
        business=business,
        data_dict={'filing': {'header': {'name': 'registration'}}},
        filing_date=datetime.utcnow(), filing_type='registration'
    )
    filing.submitter_id = user.id
    filing.save()
    caplog.set_level(logging.DEBUG)

    assert rules._is_completing_party(user, business) is False
    assert 'No completing parties found for the registration filing.' in caplog.text


@patch('legal_api.models.PartyRole.get_party_roles_by_filing',
       return_value=[PartyRole(role=PartyRole.RoleTypes.COMPLETING_PARTY.value)])
def test_is_completing_party_false_when_no_completing_party(app, session, caplog, rules):
    user = factory_user(username='test', firstname='Test', lastname='User')
    business = create_business(
        Business.LegalTypes.SOLE_PROP.value, Business.State.ACTIVE)
    # Skip creating a completing party
    filing = factory_completed_filing(
        business=business,
        data_dict={'filing': {'header': {'name': 'registration'}}},
        filing_date=datetime.utcnow(), filing_type='registration'
    )
    filing.submitter_id = user.id
    filing.save()
    caplog.set_level(logging.DEBUG)

    assert rules._is_completing_party(user, business) is False
    assert 'No completing party found for the registration filing.' in caplog.text


@pytest.mark.parametrize('user, party', [
    ({'username': 'test', 'firstname': 'Test1', 'lastname': 'User1'},
     {'first_name': 'Test2', 'last_name': 'User2'}),
    ({'username': 'test', 'firstname': 'Test1 TU1', 'lastname': 'User1'},
     {'first_name': 'Test2', 'middle_initial': 'TU2', 'last_name': 'User2'}),
    #  Test when proprietor uses middle name field and user does not
    ({'username': 'test', 'firstname': 'Test1', 'lastname': 'User1', },
     {'first_name': 'Test1', 'middle_initial': 'TU1', 'last_name': 'User1'}),
    #  Test when user uses middle name field and proprietor does not
    ({'username': 'test', 'firstname': 'Test1 TU1', 'lastname': 'User1', },
     {'first_name': 'Test1', 'last_name': 'User1'})
])
def test_is_completing_party_false_when_user_name_not_matching_completing_party_name(app, session, user, party, rules):
    user = factory_user(**user)
    business = create_business(
        Business.LegalTypes.SOLE_PROP.value, Business.State.ACTIVE)
    completing_party_role = create_party_role(
        PartyRole.RoleTypes.COMPLETING_PARTY,
        **create_test_user(**party, default_middle=False)
    )
    filing = factory_completed_filing(
        business=business,
        data_dict={'filing': {'header': {'name': 'registration'}}},
        filing_date=datetime.utcnow(), filing_type='registration'
    )
    filing.filing_party_roles.append(completing_party_role)
    filing.submitter_id = user.id
    filing.save()

    assert rules._is_completing_party(user, business) is False


def test_is_completing_party_false_when_user_is_not_submitter(app, session, caplog, rules):
    user = factory_user(username='test', firstname='Test', lastname='User')
    business = create_business(
        Business.LegalTypes.SOLE_PROP.value, Business.State.ACTIVE)
    completing_party_role = create_party_role(
        PartyRole.RoleTypes.COMPLETING_PARTY,
        **create_test_user(first_name='Test', last_name='User', default_middle=False)
    )
    filing = factory_completed_filing(
        business=business,
        data_dict={'filing': {'header': {'name': 'registration'}}},
        filing_date=datetime.utcnow(), filing_type='registration'
    )
    filing.filing_party_roles.append(completing_party_role)
    # Skip setting the submitter
    filing.save()

    assert rules._is_completing_party(user, business) is False


def test_has_party_role_false_when_no_proprietors(app, session, caplog, rules):
    user = factory_user(username='test', firstname='Test', lastname='User')
    business = create_business(
        Business.LegalTypes.SOLE_PROP.value, Business.State.ACTIVE)
    # Skip creating a proprietor
    caplog.set_level(logging.DEBUG)

    assert rules._has_party_role(
        user, business, PartyRole.RoleTypes.PROPRIETOR.value) is False
    assert 'No parties found for the business with role: proprietor' in caplog.text


@patch('legal_api.models.PartyRole.get_parties_by_role',
       return_value=[PartyRole(role=PartyRole.RoleTypes.PROPRIETOR.value)])
def test_has_party_role_false_when_no_proprietor(app, session, caplog, rules):
    user = factory_user(username='test', firstname='Test', lastname='User')
    business = create_business(
        Business.LegalTypes.SOLE_PROP.value, Business.State.ACTIVE)
    # Skip creating a proprietor
    caplog.set_level(logging.DEBUG)

    assert rules._has_party_role(
        user, business, PartyRole.RoleTypes.PROPRIETOR.value) is False
    assert 'No party found for the business with role: proprietor' in caplog.text


@pytest.mark.parametrize('user, proprietor', [
    ({'username': 'test', 'firstname': 'Test1', 'lastname': 'User1'},
     {'first_name': 'Test2', 'last_name': 'User2'}),
    ({'username': 'test', 'firstname': 'Test1 TU1', 'lastname': 'User1'},
     {'first_name': 'Test2', 'middle_initial': 'TU2', 'last_name': 'User2'}),
    #  Test when proprietor uses middle name field and user does not
    ({'username': 'test', 'firstname': 'Test1', 'lastname': 'User1', },
     {'first_name': 'Test1', 'middle_initial': 'TU1', 'last_name': 'User1'}),
    #  Test when user uses middle name field and proprietor does not
    ({'username': 'test', 'firstname': 'Test1 TU1', 'lastname': 'User1', },
     {'first_name': 'Test1', 'last_name': 'User1'})
])
def test_has_party_role_false_when_user_name_not_matching_proprietor_name(app, session, user, proprietor, rules):
    user = factory_user(**user)
    business = create_business(
        Business.LegalTypes.SOLE_PROP.value, Business.State.ACTIVE)
    proprietor_party_role = create_party_role(
        PartyRole.RoleTypes.PROPRIETOR,
        **create_test_user(**proprietor, default_middle=False)
    )
    proprietor_party_role.business_id = business.id
    proprietor_party_role.save()

    assert rules._has_party_role(
        user, business, PartyRole.RoleTypes.PROPRIETOR.value) is False


@pytest.mark.parametrize('user, party', [
    ({'username': 'test', 'firstname': 'Test', 'lastname': 'User'},
     {'first_name': 'Test', 'last_name': 'User'}),
    ({'username': 'test', 'firstname': 'TEST', 'lastname': 'USER'},
     {'first_name': 'Test', 'last_name': 'User'}),
    ({'username': 'test', 'firstname': 'Test', 'lastname': 'User'},
     {'first_name': 'TEST', 'last_name': 'USER'}),
    # Test when user and party have middle name field
    ({'username': 'test', 'firstname': 'Test TU', 'lastname': 'User'},
     {'first_name': 'Test', 'middle_initial': 'TU', 'last_name': 'User'}),
    ({'username': 'test', 'firstname': 'TEST TU', 'lastname': 'USER'},
     {'first_name': 'Test', 'middle_initial': 'TU', 'last_name': 'User'}),
    ({'username': 'test', 'firstname': 'Test TU', 'lastname': 'User'},
     {'first_name': 'TEST', 'middle_initial': 'TU', 'last_name': 'USER'}),
])
def test_is_completing_party_and_has_party_role_true(app, session, user, party, rules):
    user = factory_user(**user)
    business = create_business(
        Business.LegalTypes.SOLE_PROP.value, Business.State.ACTIVE)
    completing_party_role = create_party_role(
        PartyRole.RoleTypes.COMPLETING_PARTY,
        **create_test_user(**party, default_middle=False)
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
        **create_test_user(**party, default_middle=False)
    )
    proprietor_party_role.business_id = business.id
    proprietor_party_role.save()

    assert rules._is_completing_party_and_has_party_role(
        user, business, PartyRole.RoleTypes.PROPRIETOR.value) is True
