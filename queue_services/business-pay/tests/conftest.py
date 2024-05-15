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
import asyncio
import contextlib
import datetime
import os
import random
import time
from contextlib import contextmanager
from glob import glob
from unittest.mock import patch

import pg8000
import pg8000.native
import pytest
import pytest_asyncio
import sqlalchemy
from flask import Flask
from nats.aio.client import Client as Nats
from sqlalchemy import event, text
from sqlalchemy.schema import MetaData
from stan.aio.client import Client as Stan

from business_pay import create_app
from business_pay.config import get_named_config
from business_pay.database.db import db as _db

# from . import FROZEN_DATETIME

pytest_plugins = ("pytest_asyncio",)


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


def load_sql_file(app, con, file_name: str = "*.sql"):
    basedir = os.path.abspath(os.path.dirname(__file__))
    datadir = os.path.join(basedir, "data", file_name)
    files = glob(datadir)
    database_uri = app.config.get("SQLALCHEMY_DATABASE_URI")
    DB_USER = app.config.get("DB_USER", "")
    DB_PASSWORD = app.config.get("DB_PASSWORD", "")
    DB_NAME = app.config.get("DB_NAME", "")
    DB_HOST = app.config.get("DB_HOST", "")
    DB_PORT = app.config.get("DB_PORT", "5432")
    try:
        con = pg8000.native.Connection(
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            host=DB_HOST,
            port=int(DB_PORT),
        )
    except Exception as err:
        print(err)
        raise err

    for file in files:
        try:
            f = open(file, "r")
            buffer = f.read()
            con.run(buffer)
        except Exception as err:
            print(err)
            raise err


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
        DATABASE_URI = f"postgresql+pg8000://{user}:{password}@{host}:{port}/{user}"

    DATABASE_URI = DATABASE_URI[: DATABASE_URI.rfind("/")] + "/postgres"

    close_all = f"""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = '{database}'
        AND pid <> pg_backend_pid();
    """
    with contextlib.suppress(sqlalchemy.exc.ProgrammingError, pg8000.Error, Exception):
        with sqlalchemy.create_engine(
            DATABASE_URI, isolation_level="AUTOCOMMIT"
        ).connect() as conn:
            conn.execute(text(close_all))
            conn.execute(text(f"DROP DATABASE {database}"))


@contextmanager
def not_raises(exception):
    """Corallary to the pytest raises builtin.

    Assures that an exception is NOT thrown.
    """
    try:
        yield
    except exception:
        raise pytest.fail(f"DID RAISE {exception}")


@pytest.fixture(scope="session")
def app():
    """Return a session-wide application configured in TEST mode."""
    test_config = get_named_config("testing")
    _app = create_app(test_config)
    return _app


@pytest.fixture(scope="session")
def client(app):  # pylint: disable=redefined-outer-name
    """Return a session-wide Flask test client."""
    return app.test_client()


@pytest.fixture(scope="function")
def client_id():
    """Return a unique client_id that can be used in tests."""
    _id = random.SystemRandom().getrandbits(0x58)

    return f"client-{_id}"


@pytest.fixture(scope="session")
def db(app):  # pylint: disable=redefined-outer-name, invalid-name
    """Return a session-wide initialised database.

    Drops all existing tables - Meta follows Postgres FKs
    """
    with app.app_context():
        create_test_db(
            database=app.config.get("DATABASE_TEST_NAME"),
            database_uri=app.config.get("SQLALCHEMY_DATABASE_URI"),
        )

        sess = _db.session()
        sess.execute(text("SET TIME ZONE 'UTC';"))
        load_sql_file(app, sess.connection())

        yield _db

        drop_test_db(
            database=app.config.get("DATABASE_TEST_NAME"),
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
            print("done")

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
        sess.remove()
        # This instruction rollsback any commit that were executed in the tests.
        txn.rollback()
        conn.close()


@pytest.fixture(scope="session")
def stan_server(docker_services):
    """Create the nats / stan services that the integration tests will use."""
    if os.getenv("TEST_NATS_DOCKER"):
        try:
            docker_services.start("nats")
        except Exception as err:
            print(err)
        time.sleep(2)
    # TODO get the wait part working, as opposed to sleeping for 2s
    # public_port = docker_services.wait_for_service("nats", 4222)
    # dsn = "{docker_services.docker_ip}:{public_port}".format(**locals())
    # return dsn


@pytest_asyncio.fixture(scope="function")
async def stan(client_id):
    """Create a stan connection for each function, to be used in the tests."""
    event_loop = asyncio.get_running_loop()
    nc = Nats()
    sc = Stan()
    cluster_name = "test-cluster"

    await nc.connect(io_loop=event_loop, name="entity.filing.worker")

    await sc.connect(cluster_name, client_id, nats=nc)

    sc.subscribe()

    return sc

    # yield sc

    # await sc.close()
    # await nc.close()


@pytest_asyncio.fixture(scope="function")
async def entity_stan(app, event_loop, client_id):
    """Create a stan connection for each function.

    Uses environment variables for the cluster name.
    """
    # event_loop = asyncio.get_running_loop()
    nc = Nats()
    sc = Stan()

    await nc.connect(io_loop=event_loop)

    cluster_name = os.getenv("STAN_CLUSTER_NAME")

    if not cluster_name:
        raise ValueError("Missing env variable: STAN_CLUSTER_NAME")

    await sc.connect(cluster_name, client_id, nats=nc)

    # return sc

    yield nc, sc

    await sc.close()
    await nc.close()


@pytest.fixture(scope="function")
def future(event_loop):
    """Return a future that is used for managing function tests."""
    # event_loop = asyncio.get_running_loop()
    _future = asyncio.Future(loop=event_loop)
    return _future


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
