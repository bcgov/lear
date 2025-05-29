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
import os
import random
import time
from contextlib import contextmanager

import pytest
from flask import Flask
from flask_migrate import Migrate, upgrade
from entity_emailer.config import get_named_config  # noqa: I001
from tracker.config import get_named_config as get_tracker_named_config  # noqa: I001
from tracker.models import db as _tracker_db  # noqa: I001
from entity_emailer import worker  # noqa: I001
from legal_api import db as _db
from legal_api import jwt as _jwt
from nats.aio.client import Client as Nats
from sqlalchemy import event, text
from sqlalchemy.schema import DropConstraint, MetaData
from stan.aio.client import Client as Stan


from . import FROZEN_DATETIME


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
    _app = Flask(__name__)
    _app.config.from_object(get_named_config('testing'))
    _db.init_app(_app)

    return _app


@pytest.fixture(scope='session')
def tracker_app():
    """Return a session-wide tracker app instance configured in TEST mode.

    This is used only to reset the tracker test db.
    """
    _tracker_app = Flask(__name__)
    _tracker_app.config.from_object(get_tracker_named_config('testing'))
    _tracker_db.init_app(_tracker_app)
    return _tracker_app


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


@pytest.fixture(scope='session')
def db(app):  # pylint: disable=redefined-outer-name, invalid-name
    """Return a session-wide initialised database.

    Drops all existing tables - Meta follows Postgres FKs
    """
    with app.app_context():
        # Clear out any existing tables
        metadata = MetaData(_db.engine)
        metadata.reflect()
        metadata.drop_all()
        _db.drop_all()

        sequence_sql = """SELECT sequence_name FROM information_schema.sequences
                          WHERE sequence_schema='public'
                       """

        sess = _db.session()
        for seq in [name for (name,) in sess.execute(text(sequence_sql))]:
            try:
                sess.execute(text('DROP SEQUENCE public.%s ;' % seq))
                print('DROP SEQUENCE public.%s ' % seq)
            except Exception as err:  # pylint: disable=broad-except  # noqa B902
                print(f'Error: {err}')
        sess.commit()

        # ############################################
        # There are 2 approaches, an empty database, or the same one that the app will use
        #     create the tables
        #     _db.create_all()
        # or
        # Use Alembic to load all of the DB revisions including supporting lookup data
        # This is the path we'll use in legal_api!!

        # even though this isn't referenced directly, it sets up the internal configs that upgrade needs
        legal_api_dir = os.path.abspath('..').replace('queue_services', 'legal-api')
        legal_api_dir = os.path.join(legal_api_dir, 'migrations')
        Migrate(app, _db, legal_api_dir)
        upgrade()

        return _db


@pytest.fixture(scope='session')
def tracker_db(tracker_app):  # pylint: disable=redefined-outer-name, invalid-name
    """Return a session-wide initialised database.

    Drops all existing tables - Meta follows Postgres FKs
    """
    with tracker_app.app_context():
        # Clear out any existing tables
        metadata = MetaData(_tracker_db.engine)
        metadata.reflect()
        for table in metadata.tables.values():
            for fk in table.foreign_keys:  # pylint: disable=invalid-name
                _tracker_db.engine.execute(DropConstraint(fk.constraint))
        metadata.drop_all()
        _tracker_db.drop_all()

        sequence_sql = """SELECT sequence_name FROM information_schema.sequences
                          WHERE sequence_schema='public'
                       """

        sess = _tracker_db.session()
        for seq in [name for (name,) in sess.execute(text(sequence_sql))]:
            try:
                sess.execute(text('DROP SEQUENCE public.%s ;' % seq))
                print('DROP SEQUENCE public.%s ' % seq)
            except Exception as err:  # pylint: disable=broad-except # noqa: B902
                print(f'Error: {err}')
        sess.commit()

        # ############################################
        # There are 2 approaches, an empty database, or the same one that the app will use
        #     create the tables
        #     _db.create_all()
        # or
        # Use Alembic to load all of the DB revisions including supporting lookup data
        # even though this isn't referenced directly, it sets up the internal configs that upgrade needs
        Migrate(tracker_app, _tracker_db)
        upgrade()

        return _tracker_db


@pytest.fixture(scope='function')
def session(app, db):  # pylint: disable=redefined-outer-name, invalid-name
    """Return a function-scoped session."""
    with app.app_context():
        conn = db.engine.connect()
        txn = conn.begin()

        options = dict(bind=conn, binds={})
        sess = db.create_scoped_session(options=options)

        # establish  a SAVEPOINT just before beginning the test
        # (http://docs.sqlalchemy.org/en/latest/orm/session_transaction.html#using-savepoint)
        sess.begin_nested()

        @event.listens_for(sess(), 'after_transaction_end')
        def restart_savepoint(sess2, trans):  # pylint: disable=unused-variable
            # Detecting whether this is indeed the nested transaction of the test
            if trans.nested and not trans._parent.nested:  # pylint: disable=protected-access
                # Handle where test DOESN'T session.commit(),
                sess2.expire_all()
                sess.begin_nested()

        db.session = sess

        sql = text('select 1')
        sess.execute(sql)

        yield sess

        # Cleanup
        sess.remove()
        # This instruction rollsback any commit that were executed in the tests.
        txn.rollback()
        conn.close()


@pytest.fixture(scope='session')
def stan_server(docker_services):
    """Create the nats / stan services that the integration tests will use."""
    if os.getenv('TEST_NATS_DOCKER'):
        docker_services.start('nats')
        time.sleep(2)
    # TODO get the wait part working, as opposed to sleeping for 2s
    # public_port = docker_services.wait_for_service("nats", 4222)
    # dsn = "{docker_services.docker_ip}:{public_port}".format(**locals())
    # return dsn


@pytest.fixture(scope='function')
@pytest.mark.asyncio
async def stan(event_loop, client_id):
    """Create a stan connection for each function, to be used in the tests."""
    nc = Nats()
    sc = Stan()
    cluster_name = 'test-cluster'

    await nc.connect(io_loop=event_loop, name='entity.filing.tester')

    await sc.connect(cluster_name, client_id, nats=nc)

    yield sc

    await sc.close()
    await nc.close()


@pytest.fixture(scope='function')
@pytest.mark.asyncio
async def entity_stan(app, event_loop, client_id):
    """Create a stan connection for each function.

    Uses environment variables for the cluster name.
    """
    nc = Nats()
    sc = Stan()

    await nc.connect(io_loop=event_loop)

    cluster_name = os.getenv('STAN_CLUSTER_NAME')

    if not cluster_name:
        raise ValueError('Missing env variable: STAN_CLUSTER_NAME')

    await sc.connect(cluster_name, client_id, nats=nc)

    yield sc

    await sc.close()
    await nc.close()


@pytest.fixture(scope='function')
def future(event_loop):
    """Return a future that is used for managing function tests."""
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


@pytest.fixture(autouse=True)
def mock_settings_env_vars(app, db, monkeypatch):
    """Mock FLASK_APP and db to use test instances for worker.py."""
    monkeypatch.setattr(worker, 'FLASK_APP', app)
    monkeypatch.setattr(worker, 'db', db)
