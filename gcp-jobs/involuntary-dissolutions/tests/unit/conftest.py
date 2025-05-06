# Copyright © 2024 Province of British Columbia
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

import contextlib

import business_model_migrations
import pytest
import sqlalchemy
from flask_migrate import Migrate, upgrade

from business_model.models.db import db as _db
from involuntary_dissolutions.involuntary_dissolutions import create_app

event = sqlalchemy.event
text = sqlalchemy.text


@pytest.fixture(scope="session")
def app(request):
    """Return session-wide application."""
    app = create_app("testing")

    return app


@pytest.fixture(scope="session")
def client_ctx(app):
    """Return session-wide Flask test client."""
    with app.test_client() as c:
        yield c

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
    database_uri = database_uri if database_uri else f"postgresql://{user}:{password}@{host}:{port}/{user}"

    database_uri = database_uri[: database_uri.rfind("/")] + "/postgres"

    try:
        with sqlalchemy.create_engine(
            database_uri, isolation_level="AUTOCOMMIT"
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
    database_uri = database_uri if database_uri else f"postgresql://{user}:{password}@{host}:{port}/{user}"

    database_uri = database_uri[: database_uri.rfind("/")] + "/postgres"

    close_all = f"""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = '{database}'
        AND pid <> pg_backend_pid();
    """
    with contextlib.suppress(sqlalchemy.exc.ProgrammingError, Exception), sqlalchemy.create_engine(
        database_uri, isolation_level="AUTOCOMMIT"
    ).connect() as conn:
        conn.execute(text(close_all))
        conn.execute(text(f"DROP DATABASE {database}"))

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

        Migrate(
            app,
            _db,
            directory=business_model_migrations.__path__[0],
            dialect_name="postgres",
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
        app.logger.error("running cleanup")
        sess.remove()
        # This instruction rollsback any commit that were executed in the tests.
        txn.rollback()
        conn.close()

@pytest.fixture(autouse=True)
def run_around_tests(db):
    # run before each test
    yield
    # run after each test
    db.session.rollback()
    db.session.execute(text("TRUNCATE TABLE businesses CASCADE"))
    db.session.execute(text("TRUNCATE TABLE batches CASCADE"))
    db.session.execute(text("TRUNCATE TABLE batch_processing CASCADE"))
    db.session.commit()
