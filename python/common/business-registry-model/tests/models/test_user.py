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
import pytest

from business_model.exceptions import BusinessException
from business_model.models import User


def test_user(session):
    """Assert that a User can be stored in the service.

    Start with a blank database.
    """
    user = User(username='username',
                firstname='firstname',
                middlename='middlename',
                lastname='lastname',
                sub='sub',
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
    user = User(username='username', firstname='firstname', lastname='lastname', sub='sub', iss='iss', idp_userid='123', login_source='IDIR')
    session.add(user)
    session.commit()

    token = {'idp_userid': '123'}
    u = User.find_by_jwt_token(token)

    assert u.id is not None


def test_create_from_jwt_token(session):
    """Assert User is created from the JWT fields."""
    token = {'username': 'username',
             'given_name': 'given_name',
             'family_name': 'family_name',
             'iss': 'iss',
             'sub': 'sub',
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
             'sub': 'sub',
             'idp_userid': '123',
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
    user = User(username='username', firstname='firstname', lastname='lastname', sub='sub', iss='iss', idp_userid='123', login_source='IDIR')
    session.add(user)
    session.commit()

    u = User.find_by_username('username')

    assert u.id is not None


def test_find_by_sub(session):
    """Assert find User by the unique sub key."""
    user = User(username='username', firstname='firstname', lastname='lastname', sub='sub', iss='iss', idp_userid='123', login_source='IDIR')
    session.add(user)
    session.commit()

    u = User.find_by_sub('sub')

    assert u.id is not None


def test_user_save(session):
    """Assert User record is saved."""
    user = User(username='username', firstname='firstname', lastname='lastname', sub='sub', iss='iss', idp_userid='123', login_source='IDIR')
    user.save()

    assert user.id is not None


def test_user_delete(session):
    """Assert the User record is deleted."""
    user = User(username='username', firstname='firstname', lastname='lastname', sub='sub', iss='iss', idp_userid='123', login_source='IDIR')
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
    user = User(username=username, firstname=firstname, lastname=lastname, middlename=middlename, sub='sub', iss='iss', idp_userid='123', login_source='IDIR')

    assert display_name == user.display_name
