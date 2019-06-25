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

from legal_api.exceptions import BusinessException
from legal_api.models import User


def test_user(session):
    """Assert that a User can be stored in the service.

    Start with a blank database.
    """
    user = User(username='username', firstname='firstname', lastname='lastname', sub='sub', iss='iss')

    session.add(user)
    session.commit()

    assert user.id is not None


def test_user_find_by_jwt_token(session):
    """Assert that a User can be stored in the service.

    Start with a blank database.
    """
    user = User(username='username', firstname='firstname', lastname='lastname', sub='sub', iss='iss')
    session.add(user)
    session.commit()

    token = {'sub': 'sub'}
    u = User.find_by_jwt_token(token)

    assert u.id is not None


def test_create_from_jwt_token(session):
    """Assert User is created from the JWT fields."""
    token = {'username': 'username',
             'given_name': 'given_name',
             'family_name': 'family_name',
             'iss': 'iss',
             'sub': 'sub'
             }
    u = User.create_from_jwt_token(token)
    assert u.id is not None


def test_get_or_create_user_by_jwt(session):
    """Assert User is created from the JWT fields."""
    token = {'username': 'username',
             'given_name': 'given_name',
             'family_name': 'family_name',
             'iss': 'iss',
             'sub': 'sub'
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
    user = User(username='username', firstname='firstname', lastname='lastname', sub='sub', iss='iss')
    session.add(user)
    session.commit()

    u = User.find_by_username('username')

    assert u.id is not None


def test_find_by_sub(session):
    """Assert find User by the unique sub key."""
    user = User(username='username', firstname='firstname', lastname='lastname', sub='sub', iss='iss')
    session.add(user)
    session.commit()

    u = User.find_by_sub('sub')

    assert u.id is not None


def test_user_save(session):
    """Assert User record is saved."""
    user = User(username='username', firstname='firstname', lastname='lastname', sub='sub', iss='iss')
    user.save()

    assert user.id is not None


def test_user_delete(session):
    """Assert the User record is deleted."""
    user = User(username='username', firstname='firstname', lastname='lastname', sub='sub', iss='iss')
    user.save()
    user.delete()

    assert user.id is not None
