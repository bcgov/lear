# Copyright © 2025 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""Common setup and fixtures for the pytest suite used by this service."""
import asyncio
import datetime
import json
import os
import random
import time
from contextlib import contextmanager

import business_model_migrations
import pytest
import requests
from flask import Flask, current_app
from flask_migrate import Migrate, upgrade
from business_filer import db as _db
from flask_jwt_oidc import JwtManager
# from business_filer import jwt as _jwt
from ldclient.integrations.test_data import TestData
from sqlalchemy import event, text
from sqlalchemy.schema import DropConstraint, MetaData
from testcontainers.postgres import PostgresContainer
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from business_filer.config import TestConfig
from business_filer import create_app

from . import FROZEN_DATETIME

postgres = PostgresContainer("postgres:16-alpine")

@contextmanager
def not_raises(exception):
    """Corallary to the pytest raises builtin.

    Assures that an exception is NOT thrown.
    """
    try:
        yield
    except exception:
        raise pytest.fail(f'DID RAISE {exception}')


# fixture to freeze utcnow to a fixed date-time
@pytest.fixture
def freeze_datetime_utcnow(monkeypatch):
    """Fixture to return a static time for utcnow()."""
    class _Datetime:
        @classmethod
        def utcnow(cls):
            return FROZEN_DATETIME

    monkeypatch.setattr(datetime, 'datetime', _Datetime)


@pytest.fixture(scope="session")
def ld():
    """LaunchDarkly TestData source."""
    td = TestData.data_source()
    with open("flags.json") as file:
        data = file.read()
        test_flags: dict[str, dict] = json.loads(data)
        for flag_name, flag_value in test_flags["flagValues"].items():
            # NOTE: should check if isinstance dict and if so, apply each variation
            td.update(td.flag(flag_name).variation_for_all(flag_value))
    yield td


@pytest.fixture(scope="session")
def database_service(request):
    """Start up database."""
    postgres.start()

    def remove_container():
        postgres.stop()
    
    request.addfinalizer(remove_container)


@pytest.fixture(scope="session")
def app(ld, database_service):
    """Return a session-wide application configured in TEST mode."""
    TestConfig.SQLALCHEMY_DATABASE_URI = postgres.get_connection_url()
    options = {
        'ld_test_data':ld,
        'config': TestConfig,
    }
    _app = create_app("testing", **options)

    with _app.app_context():
        yield _app


# @pytest.fixture
# def config(app):
#     """Return the application config."""
#     return app.config


@pytest.fixture(scope='session')
def client(app):  # pylint: disable=redefined-outer-name
    """Return a session-wide Flask test client."""
    return app.test_client()


@pytest.fixture(scope='session')
def jwt(app):
    """Return a session-wide jwt manager."""
    _jwt = JwtManager()
    def get_roles(a_dict):
        return a_dict['realm_access']['roles']  # pragma: no cover
    app.config['JWT_ROLE_CALLBACK'] = get_roles
    _jwt.init_app(app)

    return _jwt


# @pytest.fixture(scope='function')
# def account(app):
#     """Create an account to be used for testing."""
#     import uuid
#     from business_filer.services import AccountService
#     with app.app_context():
#         account_url = current_app.config.get('ACCOUNT_SVC_AFFILIATE_URL')
#         account_url = account_url[:account_url.rfind('{') - 1]

#         org_data = json.dumps({'name': str(uuid.uuid4())})
#         token = AccountService.get_bearer_token()

#         # with app.app_context():
#         rv = requests.post(
#             url=account_url,
#             data=org_data,
#             headers={**AccountService.CONTENT_TYPE_JSON,
#                      'Authorization': AccountService.BEARER + token},
#             timeout=20
#         )

#         account_id = rv.json()['id']

#         yield account_id

#         rv = requests.delete(url=f'{account_url}/{account_id}',
#                              headers={'Authorization': AccountService.BEARER + token},
#                              timeout=20
#                              )
#         print(rv)





@pytest.fixture(scope="session", autouse=True)
def database_setup(database_service, app):
    """Start up database."""
    dir_path = os.path.dirname(business_model_migrations.__file__)
    Migrate(app, _db, directory=dir_path)
    upgrade() 


@pytest.fixture(scope='function')
def session(database_setup):
    """DB and build tables"""
   # Connect to the database
    connection = _db.engine.connect()

    # Begin a non-ORM transaction
    transaction = connection.begin()
    
    options = dict(bind=connection,
                   join_transaction_mode="create_savepoint",
                   binds={})
    session = _db._make_scoped_session(options=options)

    _db.session = session

    # ping the connection
    session.execute(text("SET TIME ZONE 'UTC';"))

    yield session  # this is where the test runs

    # Teardown: close session, rollback transaction, close connection
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def create_mock_coro(mocker, monkeypatch):
    """Return a mocked coroutine, and optionally patch-it in."""
    def _create_mock_patch_coro(to_patch=None):
        mock = mocker.Mock()

        def _coro(*args, **kwargs):
            return mock(*args, **kwargs)

        if to_patch:  # <-- may not need/want to patch anything
            monkeypatch.setattr(to_patch, _coro)
        return mock, _coro

    return _create_mock_patch_coro

