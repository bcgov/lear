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
"""Common setup and fixtures for the pytest suite used by this service."""
import asyncio
import datetime
import json
import os
import random
import time
from contextlib import contextmanager, suppress

import pytest
import requests
import sqlalchemy
import business_model_migrations
from flask import Flask, current_app
from flask_migrate import Migrate, upgrade
from business_model import db as _db

# from legal_api import db as _db
# from legal_api import jwt as _jwt
from sqlalchemy import event, text
from sqlalchemy.schema import DropConstraint, MetaData

from entity_filer import create_app
from entity_filer.config import Testing

from . import FROZEN_DATETIME


@contextmanager
def not_raises(exception):
    """Corallary to the pytest raises builtin.

    Assures that an exception is NOT thrown.
    """
    try:
        yield
    except exception:
        raise pytest.fail(f"DID RAISE {exception}")


# fixture to freeze utcnow to a fixed date-time
@pytest.fixture
def freeze_datetime_utcnow(monkeypatch):
    """Fixture to return a static time for utcnow()."""

    class _Datetime:
        @classmethod
        def utcnow(cls):
            return FROZEN_DATETIME

    monkeypatch.setattr(datetime, "datetime", _Datetime)


@pytest.fixture(scope="session")
def app():
    """Return a session-wide application configured in TEST mode."""
    # _app = create_app('testing')
    app = create_app(Testing)
    return app


@pytest.fixture
def config(app):
    """Return the application config."""
    return app.config


@pytest.fixture(scope="session")
def client(app):  # pylint: disable=redefined-outer-name
    """Return a session-wide Flask test client."""
    return app.test_client()


# @pytest.fixture(scope='session')
# def jwt():
#     """Return a session-wide jwt manager."""
#     return _jwt


@pytest.fixture(scope="session")
def client_ctx(app):  # pylint: disable=redefined-outer-name
    """Return session-wide Flask test client."""
    with app.test_client() as _client:
        yield _client


@pytest.fixture(scope="function")
def account(app):
    """Create an account to be used for testing."""
    import uuid

    account_id = random.randint(1, 1000000)
    yield account_id


# @pytest.fixture(scope='function')
# def account(app):
#     """Create an account to be used for testing."""
#     import uuid
#     from legal_api.services.bootstrap import AccountService
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


# @pytest.fixture(scope='function')
# def client_id():
#     """Return a unique client_id that can be used in tests."""
#     _id = random.SystemRandom().getrandbits(0x58)
# #     _id = (base64.urlsafe_b64encode(uuid.uuid4().bytes)).replace('=', '')

#     return f'client-{_id}'


# @pytest.fixture(scope='session')
# def db(app):  # pylint: disable=redefined-outer-name, invalid-name
#     """Return a session-wide initialised database.

#     Drops all existing tables - Meta follows Postgres FKs
#     """
#     with app.app_context():
#         # Clear out any existing tables
#         metadata = MetaData(_db.engine)
#         metadata.reflect()
#         metadata.drop_all()
#         _db.drop_all()

#         sequence_sql = """SELECT sequence_name FROM information_schema.sequences
#                           WHERE sequence_schema='public'
#                        """

#         sess = _db.session()
#         for seq in [name for (name,) in sess.execute(text(sequence_sql))]:
#             try:
#                 sess.execute(text('DROP SEQUENCE public.%s ;' % seq))
#                 print('DROP SEQUENCE public.%s ' % seq)
#             except Exception as err:  # pylint: disable=broad-except
#                 print(f'Error: {err}')
#         sess.commit()

#         # ############################################
#         # There are 2 approaches, an empty database, or the same one that the app will use
#         #     create the tables
#         #     _db.create_all()
#         # or
#         # Use Alembic to load all of the DB revisions including supporting lookup data
#         # This is the path we'll use in legal_api!!

#         # even though this isn't referenced directly, it sets up the internal configs that upgrade needs
#         legal_api_dir = os.path.abspath('..').replace('queue_services', 'legal-api')
#         legal_api_dir = os.path.join(legal_api_dir, 'migrations')
#         Migrate(app, _db, directory=legal_api_dir)
#         upgrade()

#         return _db


@pytest.fixture(scope="session")
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

        dir_path = os.path.dirname(business_model_migrations.__file__)

        migrate = Migrate(app, _db, directory=dir_path, **{"dialect_name": "postgres"})
        upgrade()

        yield _db

        try:
            drop_test_db(
                database=app.config.get("DB_NAME"),
                database_uri=app.config.get("SQLALCHEMY_DATABASE_URI"),
            )
        except sqlalchemy.exc.InterfaceError:
            print("dropped database before all connections closed")


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


# @pytest.fixture(scope='session')
# def stan_server(docker_services):
#     """Create the nats / stan services that the integration tests will use."""
#     if os.getenv('TEST_NATS_DOCKER'):
#         docker_services.start('nats')
#         time.sleep(2)
#     # TODO get the wait part working, as opposed to sleeping for 2s
#     # public_port = docker_services.wait_for_service("nats", 4222)
#     # dsn = "{docker_services.docker_ip}:{public_port}".format(**locals())
#     # return dsn


# @pytest.fixture(scope='function')
# @pytest.mark.asyncio
# async def stan(event_loop, client_id):
#     """Create a stan connection for each function, to be used in the tests."""
#     nc = Nats()
#     sc = Stan()
#     cluster_name = 'test-cluster'

#     await nc.connect(io_loop=event_loop, name='entity.filing.tester')

#     await sc.connect(cluster_name, client_id, nats=nc)

#     yield sc

#     await sc.close()
#     await nc.close()


# @pytest.fixture(scope='function')
# @pytest.mark.asyncio
# async def entity_stan(app, event_loop, client_id):
#     """Create a stan connection for each function.

#     Uses environment variables for the cluster name.
#     """
#     nc = Nats()
#     sc = Stan()

#     await nc.connect(io_loop=event_loop)

#     cluster_name = os.getenv('STAN_CLUSTER_NAME')

#     if not cluster_name:
#         raise ValueError('Missing env variable: STAN_CLUSTER_NAME')

#     await sc.connect(cluster_name, client_id, nats=nc)

#     yield sc

#     await sc.close()
#     await nc.close()


# @pytest.fixture(scope='function')
# def future(event_loop):
#     """Return a future that is used for managing function tests."""
#     _future = asyncio.Future(loop=event_loop)
#     return _future


# @pytest.fixture
# def create_mock_coro(mocker, monkeypatch):
#     """Return a mocked coroutine, and optionally patch-it in."""
#     def _create_mock_patch_coro(to_patch=None):
#         mock = mocker.Mock()

#         async def _coro(*args, **kwargs):
#             return mock(*args, **kwargs)

#         if to_patch:  # <-- may not need/want to patch anything
#             monkeypatch.setattr(to_patch, _coro)
#         return mock, _coro

#     return _create_mock_patch_coro


# @pytest.fixture(scope='session')
# def minio_server(docker_services):
#     """Create the minio services that the integration tests will use."""
#     docker_services.start('minio')
#     docker_services.wait_for_service('minio', 9000)
#     time.sleep(10)


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
    with suppress(sqlalchemy.exc.ProgrammingError, Exception):
        with sqlalchemy.create_engine(
            DATABASE_URI, isolation_level="AUTOCOMMIT"
        ).connect() as conn:
            conn.execute(text(close_all))
            conn.execute(text(f"DROP DATABASE {database}"))
