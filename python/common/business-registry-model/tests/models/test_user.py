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

"""Tests to assure the User Class.

Test-Suite to ensure that the User Class is working as expected.
"""
import base64
import uuid

import pytest

from business_model.exceptions import BusinessException
from business_model.models import User


def create_sub():
    return base64.urlsafe_b64encode(uuid.uuid4().bytes).decode().replace('=', '')


def _set_jwt_oidc_claim_config(app, monkeypatch):
    """Configure the JWT claim names so token claims map onto the User attributes."""
    monkeypatch.setitem(app.config, 'JWT_OIDC_USERNAME', 'username')
    monkeypatch.setitem(app.config, 'JWT_OIDC_FIRSTNAME', 'firstname')
    monkeypatch.setitem(app.config, 'JWT_OIDC_LASTNAME', 'lastname')


def test_user(session):
    """Assert that a User can be stored in the service.

    Start with a blank database.
    """
    user = User(username='username',
                firstname='firstname',
                middlename='middlename',
                lastname='lastname',
                sub=create_sub(),
                iss='iss',
                idp_userid='123',
                login_source='IDIR'
    )

    session.add(user)
    session.commit()

    assert user.id is not None


def test_user_find_by_jwt_token(session):
    """Assert that a User can be stored in the service.

    Start with a blank database.
    """
    idp_userid = create_sub()
    user = User(username='username', firstname='firstname', lastname='lastname', sub=create_sub(), iss='iss', idp_userid=idp_userid, login_source='IDIR')
    session.add(user)
    session.commit()

    token = {'idp_userid': idp_userid}
    u = User.find_by_jwt_token(token)

    assert u.id is not None


def test_create_from_jwt_token(session):
    """Assert User is created from the JWT fields."""
    token = {'username': 'username',
             'given_name': 'given_name',
             'family_name': 'family_name',
             'iss': 'iss',
             'sub': create_sub(),
             'idp_userid': '123',
             'loginSource': 'IDIR'
             }
    u = User.create_from_jwt_token(token)
    assert u.id is not None


def test_get_or_create_user_by_jwt(session):
    """Assert User is created from the JWT fields."""
    token = {'username': 'username',
             'given_name': 'given_name',
             'family_name': 'family_name',
             'iss': 'iss',
             'sub': create_sub(),
             'idp_userid': create_sub(),
             'loginSource': 'IDIR'
             }
    u = User.get_or_create_user_by_jwt(token)
    assert u.id is not None


def test_get_or_create_user_by_jwt_invlaid_jwt(session):
    """Assert User is created from the JWT fields."""
    token = b'invalidtoken'

    with pytest.raises(BusinessException) as excinfo:
        User.get_or_create_user_by_jwt(token)

    assert excinfo.value.error == 'unable_to_get_or_create_user'


def test_get_or_create_user_by_jwt_creates_new_user_with_token_claims(session, app, monkeypatch):
    """Assert that a brand new user is created and populated from the JWT claims."""
    _set_jwt_oidc_claim_config(app, monkeypatch)
    idp_userid = create_sub()
    token = {'username': 'newusername',
             'firstname': 'New',
             'lastname': 'User',
             'iss': 'iss',
             'sub': create_sub(),
             'idp_userid': idp_userid,
             'loginSource': 'BCSC'
             }

    u = User.get_or_create_user_by_jwt(token)

    assert u.id is not None
    assert u.username == 'newusername'
    assert u.firstname == 'New'
    assert u.lastname == 'User'


@pytest.mark.parametrize('test_name, attribute', [
    ('firstname changed', 'firstname'),
    ('lastname changed', 'lastname'),
    ('username changed', 'username'),
])
def test_get_or_create_user_by_jwt_syncs_changed_claim(session, app, monkeypatch, test_name, attribute):
    """Assert that an existing user's stored attribute is refreshed when the JWT claim has changed."""
    _set_jwt_oidc_claim_config(app, monkeypatch)
    idp_userid = create_sub()
    user = User(username='username', firstname='firstname', lastname='lastname',
                sub=create_sub(), iss='iss', idp_userid=idp_userid, login_source='IDIR')
    session.add(user)
    session.commit()
    user_id = user.id

    token = {'username': 'username', 'firstname': 'firstname', 'lastname': 'lastname',
             'iss': 'iss', 'sub': create_sub(), 'idp_userid': idp_userid, 'loginSource': 'IDIR'}
    token[attribute] = 'updated_value'

    u = User.get_or_create_user_by_jwt(token)

    assert u.id == user_id
    assert getattr(u, attribute) == 'updated_value'


def test_get_or_create_user_by_jwt_leaves_matching_claims_unchanged(session, app, monkeypatch):
    """Assert that an existing user's attributes are left unchanged when the JWT claims already match."""
    _set_jwt_oidc_claim_config(app, monkeypatch)
    idp_userid = create_sub()
    user = User(username='username', firstname='firstname', lastname='lastname',
                sub=create_sub(), iss='iss', idp_userid=idp_userid, login_source='IDIR')
    session.add(user)
    session.commit()
    user_id = user.id

    token = {'username': 'username', 'firstname': 'firstname', 'lastname': 'lastname',
             'iss': 'iss', 'sub': create_sub(), 'idp_userid': idp_userid, 'loginSource': 'IDIR'}

    u = User.get_or_create_user_by_jwt(token)

    assert u.id == user_id
    assert u.username == 'username'
    assert u.firstname == 'firstname'
    assert u.lastname == 'lastname'


def test_get_or_create_user_by_jwt_preserves_stored_values_when_claims_missing(session, app, monkeypatch):
    """Assert that stored name values survive a token with no name claims (eg. a service account)."""
    _set_jwt_oidc_claim_config(app, monkeypatch)
    idp_userid = create_sub()
    user = User(username='username', firstname='firstname', lastname='lastname',
                sub=create_sub(), iss='iss', idp_userid=idp_userid, login_source='IDIR')
    session.add(user)
    session.commit()
    user_id = user.id

    # service-account style token: no username/firstname/lastname claims present
    token = {'iss': 'iss', 'sub': create_sub(), 'idp_userid': idp_userid, 'loginSource': 'system'}

    u = User.get_or_create_user_by_jwt(token)

    assert u.id == user_id
    assert u.username == 'username'
    assert u.firstname == 'firstname'
    assert u.lastname == 'lastname'


def test_get_or_create_user_by_jwt_split_name_is_not_stale(session, app, monkeypatch):
    """Assert that a record splitting the same name differently is left untouched."""
    _set_jwt_oidc_claim_config(app, monkeypatch)
    idp_userid = create_sub()
    user = User(username='username', firstname='Joe', middlename='P', lastname='Swanson',
                sub=create_sub(), iss='iss', idp_userid=idp_userid, login_source='BCSC')
    session.add(user)
    session.commit()
    user_id = user.id

    token = {'username': 'username', 'firstname': 'Joe P', 'lastname': 'Swanson',
             'iss': 'iss', 'sub': create_sub(), 'idp_userid': idp_userid, 'loginSource': 'BCSC'}

    u = User.get_or_create_user_by_jwt(token)

    assert u.id == user_id
    assert u.firstname == 'Joe'
    assert u.middlename == 'P'
    assert u.lastname == 'Swanson'


def test_get_or_create_user_by_jwt_name_change_clears_middlename(session, app, monkeypatch):
    """Assert that a genuine name change replaces the whole stored name, middlename included."""
    _set_jwt_oidc_claim_config(app, monkeypatch)
    idp_userid = create_sub()
    user = User(username='username', firstname='Joe', middlename='P', lastname='Swanson',
                sub=create_sub(), iss='iss', idp_userid=idp_userid, login_source='BCSC')
    session.add(user)
    session.commit()
    user_id = user.id

    token = {'username': 'username', 'firstname': 'Joseph P', 'lastname': 'Swanson',
             'iss': 'iss', 'sub': create_sub(), 'idp_userid': idp_userid, 'loginSource': 'BCSC'}

    u = User.get_or_create_user_by_jwt(token)

    assert u.id == user_id
    assert u.firstname == 'Joseph P'
    assert u.middlename is None
    assert u.lastname == 'Swanson'


def test_create_from_jwt_token_no_token(session):
    """Assert User is not created from an empty token."""
    token = None
    u = User.create_from_jwt_token(token)
    assert u is None


def test_create_from_invalid_jwt_token_no_token(session):
    """Assert User is not created from an empty token."""
    token = b'invalidtoken'

    with pytest.raises(AttributeError) as excinfo:
        User.create_from_jwt_token(token)

    assert excinfo.value.args[0] == "'bytes' object has no attribute 'get'"


def test_find_by_username(session):
    """Assert User can be found by the most current username."""
    user = User(username='username', firstname='firstname', lastname='lastname', sub=create_sub(), iss='iss', idp_userid='123', login_source='IDIR')
    session.add(user)
    session.commit()

    u = User.find_by_username('username')

    assert u.id is not None


def test_find_by_sub(session):
    """Assert find User by the unique sub key."""
    sub = create_sub()
    user = User(username='username', firstname='firstname', lastname='lastname', sub=sub, iss='iss', idp_userid='123', login_source='IDIR')
    session.add(user)
    session.commit()

    u = User.find_by_sub(sub)

    assert u.id is not None


def test_user_save(session):
    """Assert User record is saved."""
    user = User(username='username', firstname='firstname', lastname='lastname', sub=create_sub(), iss='iss', idp_userid='123', login_source='IDIR')
    user.save()

    assert user.id is not None


def test_user_delete(session):
    """Assert the User record is deleted."""
    user = User(username='username', firstname='firstname', lastname='lastname', sub=create_sub(), iss='iss', idp_userid='123', login_source='IDIR')
    user.save()
    user.delete()

    assert user.id is not None


TEST_USER_DISPLAY_NAME = [
    ('nothing to show', '', '', '', '', None),
    ('simple username', 'someone', '', '', '', 'someone'),
    # below: idir is idir\blablabla; flake thinks we're trying to escape a character, hence the double slashes
    ('username - idir with slash', 'idir\\joefresh', '', '', '', 'joefresh'),
    ('username - idir with @', 'joefresh@idir', '', '', '', 'joefresh'),
    ('username - services card', 'bcsc/abc123', '', '', '', None),
    ('simple name', 'anything', 'First', 'Last', '', 'First Last'),
    ('name - first name only', 'anything', 'First', '', '', 'First'),
    ('name - last name only', 'anything', '', 'Last', '', 'Last'),
    ('name - middle name only', 'anything', '', '', 'Middle', 'Middle'),
    ('name - full name', 'anything', 'First', 'Last', 'Middle', 'First Middle Last')
]


@pytest.mark.parametrize('test_description, username, firstname, lastname, middlename, display_name', TEST_USER_DISPLAY_NAME)
def test_user_display_name(session, test_description, username, firstname, lastname, middlename, display_name):
    """Assert the User record is deleted."""
    user = User(username=username, firstname=firstname, lastname=lastname, middlename=middlename, sub=create_sub(), iss='iss', idp_userid='123', login_source='IDIR')

    assert display_name == user.display_name
