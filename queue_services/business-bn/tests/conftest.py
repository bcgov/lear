# Copyright © 2024 Province of British Columbia
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
import datetime
import random
import contextlib
from contextlib import contextmanager

import pytest
import sqlalchemy
from sqlalchemy import event, text
from flask import Flask
from flask_migrate import Migrate, upgrade
from flask_jwt_oidc import JwtManager

from business_model.models import db as _db
from business_bn import create_app

import business_model_migrations

from . import FROZEN_DATETIME

_jwt = JwtManager()  # pylint: disable=invalid-name; lower case name as used by convention in most Flask apps

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


@pytest.fixture(scope='session')
def app():
    """Return a session-wide application configured in TEST mode."""
    _app = create_app('testing')

    return _app


@pytest.fixture
def config(app):
    """Return the application config."""
    return app.config


@pytest.fixture(scope='session')
def client(app):  # pylint: disable=redefined-outer-name
    """Return a session-wide Flask test client."""
    return app.test_client()


@pytest.fixture(scope='session')
def jwt():
    """Return a session-wide jwt manager."""
    return _jwt


@pytest.fixture(scope='session')
def client_ctx(app):  # pylint: disable=redefined-outer-name
    """Return session-wide Flask test client."""
    with app.test_client() as _client:
        yield _client


@pytest.fixture(scope='function')
def client_id():
    """Return a unique client_id that can be used in tests."""
    _id = random.SystemRandom().getrandbits(0x58)

    return f'client-{_id}'


def create_test_db(
    user: str = None,
    password: str = None,
    database: str = None,
    host: str = "localhost",
    port: int = 1521,
    database_uri: str = None,
) -> bool:
    """Create the database in our .devcontainer launched postgres DB.
    Parameters
    ------------
        user: str
            A datbase user that has create database privledges
        password: str
            The users password
        database: str
            The name of the database to create
        host: str, Optional
            The network name of the server
        port: int, Optional
            The numeric port number
    Return
    -----------
        : bool
            If the create database succeeded.
    """
    if database_uri:
        DATABASE_URI = database_uri
    else:
        DATABASE_URI = f"postgresql://{user}:{password}@{host}:{port}/{user}"

    DATABASE_URI = DATABASE_URI[: DATABASE_URI.rfind("/")] + "/postgres"

    try:
        with sqlalchemy.create_engine(
            DATABASE_URI, isolation_level="AUTOCOMMIT"
        ).connect() as conn:
            conn.execute(text(f"CREATE DATABASE {database}"))

        return True
    except sqlalchemy.exc.ProgrammingError as err:
        print(err)  # used in the test suite, so on failure print something
        return False


def drop_test_db(
    user: str = None,
    password: str = None,
    database: str = None,
    host: str = "localhost",
    port: int = 1521,
    database_uri: str = None,
) -> bool:
    """Delete the database in our .devcontainer launched postgres DB."""
    if database_uri:
        DATABASE_URI = database_uri
    else:
        DATABASE_URI = f"postgresql://{user}:{password}@{host}:{port}/{user}"

    DATABASE_URI = DATABASE_URI[: DATABASE_URI.rfind("/")] + "/postgres"

    close_all = f"""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = '{database}'
        AND pid <> pg_backend_pid();
    """
    with contextlib.suppress(sqlalchemy.exc.ProgrammingError, Exception):
        with sqlalchemy.create_engine(
            DATABASE_URI, isolation_level="AUTOCOMMIT"
        ).connect() as conn:
            conn.execute(text(close_all))
            conn.execute(text(f"DROP DATABASE {database}"))


@pytest.fixture(scope='session')
def db(app):  # pylint: disable=redefined-outer-name, invalid-name
    """Return a session-wide initialised database.
    Drops all existing tables - Meta follows Postgres FKs
    """
    with app.app_context():
        create_test_db(
            database=app.config.get("DB_NAME"),
            database_uri=app.config.get("SQLALCHEMY_DATABASE_URI"),
        )

        sess = _db.session()
        sess.execute(text("SET TIME ZONE 'UTC';"))
        migrate = Migrate(
            app,
            _db,
            directory=business_model_migrations.__path__[0],
            **{"dialect_name": "postgres"},
        )
        upgrade()

        yield _db

        drop_test_db(
            database=app.config.get("DB_NAME"),
            database_uri=app.config.get("SQLALCHEMY_DATABASE_URI"),
        )


@pytest.fixture(scope="function")
def session(app, db):  # pylint: disable=redefined-outer-name, invalid-name
    """Return a function-scoped session."""
    with app.app_context():
        conn = db.engine.connect()
        txn = conn.begin()

        try:
            options = dict(bind=conn, binds={})
            # sess = db.create_scoped_session(options=options)
            sess = db._make_scoped_session(options=options)
        except Exception as err:
            print(err)

        # establish  a SAVEPOINT just before beginning the test
        # (http://docs.sqlalchemy.org/en/latest/orm/session_transaction.html#using-savepoint)
        sess.begin_nested()

        @event.listens_for(sess(), "after_transaction_end")
        def restart_savepoint(sess2, trans):  # pylint: disable=unused-variable
            # Detecting whether this is indeed the nested transaction of the test
            if (
                trans.nested and not trans._parent.nested
            ):  # pylint: disable=protected-access
                # Handle where test DOESN'T session.commit(),
                sess2.expire_all()
                sess.begin_nested()

        db.session = sess

        sql = text("select 1")
        sess.execute(sql)

        yield sess

        # Cleanup
        sess.rollback()
        sess.remove()
        # This instruction rollsback any commit that were executed in the tests.
        txn.rollback()
        conn.close()


@pytest.fixture
def create_mock_coro(mocker, monkeypatch):
    """Return a mocked coroutine, and optionally patch-it in."""

    def _create_mock_patch_coro(to_patch=None):
        mock = mocker.Mock()

        async def _coro(*args, **kwargs):
            return mock(*args, **kwargs)

        if to_patch:  # <-- may not need/want to patch anything
            monkeypatch.setattr(to_patch, _coro)
        return mock, _coro

    return _create_mock_patch_coro


@pytest.fixture(autouse=True)
def run_around_tests(db):
    # run before each test
    yield
    # run after each test
    db.session.rollback()
    db.session.execute(text(f'TRUNCATE TABLE businesses CASCADE'))
    db.session.commit()
