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
import os
from contextlib import contextmanager

import pytest
from flask import Flask
from flask_migrate import Migrate, upgrade
from sqlalchemy import event, text
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import now as _sqla_now
from testcontainers.postgres import PostgresContainer

import business_model_migrations
from business_model.models import db as _db
from config import Testing

postgres = PostgresContainer("postgres:16-alpine")


# Models default many timestamp columns to ``func.now()`` which Postgres
# resolves to the transaction start time. Per-test transaction isolation
# means every row a test creates would share the same timestamp, breaking
# any ``ORDER BY created_date`` query. Substitute ``clock_timestamp()`` so
# each row gets a distinct wall-clock value at insert time. Test-only.
@compiles(_sqla_now, 'postgresql')
def _compile_now_to_clock_timestamp(element, compiler, **kw):
    return 'clock_timestamp()'


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
def database_service(request):
    """Start up database."""
    postgres.start()

    def remove_container():
        postgres.stop()
    
    request.addfinalizer(remove_container)


@pytest.fixture(scope="session")
def app(database_service):
    """Return a session-wide application configured in TEST mode."""
    _app = Flask(__name__)
    Testing.SQLALCHEMY_DATABASE_URI = postgres.get_connection_url()
    _app.config.from_object(Testing)
    _db.init_app(_app)

    with _app.app_context():
        yield _app


@pytest.fixture(scope='function')
def app_request():
    """Return a session-wide application configured in TEST mode."""
    app = Flask(__name__)
    Testing.SQLALCHEMY_DATABASE_URI = postgres.get_connection_url()
    app.config.from_object(Testing)
    _db.init_app(app)

    return app


@pytest.fixture(scope="session")
def client(app):  # pylint: disable=redefined-outer-name
    """Return a session-wide Flask test client."""
    return app.test_client()


@pytest.fixture(scope="session", autouse=True)
def database_setup(database_service, app):
    """Start up database."""
    dir_path = os.path.dirname(business_model_migrations.__file__)
    Migrate(app, _db, directory=dir_path)
    upgrade() 


@pytest.fixture(scope='function')
def session(database_setup):
    """Per-test DB session with SAVEPOINT-based isolation.

    Opens a dedicated connection with an outer transaction, starts a
    SAVEPOINT inside it, and re-issues a fresh SAVEPOINT every time one
    ends. Production code that commits (every model's `.save()` calls
    `db.session.commit()`) only releases the inner SAVEPOINT — it
    never escapes the outer transaction. Teardown rolls back the outer
    transaction, wiping everything the test wrote.
    """
    connection = _db.engine.connect()
    transaction = connection.begin()

    scoped = _db._make_scoped_session(options=dict(bind=connection, binds={}))
    _db.session = scoped

    sess = scoped()
    # Flask-SQLAlchemy's Session.get_bind() ignores the Session's `bind=` and
    # returns db.engines[None]; force it to use our test connection so writes
    # land inside the outer transaction we just opened.
    sess.get_bind = lambda *args, **kwargs: connection
    sess.begin_nested()

    # Needed for extra save points in factory functions etc.
    @event.listens_for(sess, 'after_transaction_end')
    def restart_savepoint(s, trans):
        if trans.nested and not trans._parent.nested:
            s.begin_nested()

    sess.execute(text("SET TIME ZONE 'UTC';"))

    yield scoped

    event.remove(sess, 'after_transaction_end', restart_savepoint)
    scoped.close()
    transaction.rollback()
    connection.close()
