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
import json

import business_model_migrations
import pytest
import sqlalchemy
from flask import Flask
from flask_migrate import Migrate, upgrade
from flask_sqlalchemy import SQLAlchemy
from ldclient.integrations.test_data import TestData
from sqlalchemy import event, text

from business_model.models import db as _db
from furnishings import create_app
from furnishings.sftp import SftpConnection


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
def app(ld):
    """Return a session-wide application configured in TEST mode."""
    _app = create_app("testing", ld_test_data=ld)
    
    with _app.app_context():
        yield _app


@pytest.fixture(scope="session")
def sftpconnection(sftpserver):
    """
    Returns a session-wide SFTP connection.
    """
    return SftpConnection(
        username="user",
        password="pwd",
        host=sftpserver.host,
        port=sftpserver.port
    )

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
    db_uri = database_uri if database_uri else f"postgresql://{user}:{password}@{host}:{port}/{user}"

    db_uri = db_uri[: db_uri.rfind("/")] + "/postgres"

    try:
        with sqlalchemy.create_engine(
            db_uri, isolation_level="AUTOCOMMIT"
        ).connect() as conn:
            conn.execute(text(f"CREATE DATABASE {database}"))

        return True
    except sqlalchemy.exc.ProgrammingError as err:
        print(err)  # noqa: T201
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
    db_uri = database_uri if database_uri else f"postgresql://{user}:{password}@{host}:{port}/{user}"

    db_uri = db_uri[: db_uri.rfind("/")] + "/postgres"

    close_all = f"""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = '{database}'
        AND pid <> pg_backend_pid();
    """
    with contextlib.suppress(sqlalchemy.exc.ProgrammingError, Exception), \
        sqlalchemy.create_engine(db_uri, isolation_level="AUTOCOMMIT").connect() as conn:
        conn.execute(text(close_all))
        conn.execute(text(f"DROP DATABASE {database}"))


@pytest.fixture(scope="session")
def db(app: Flask):
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
def session(app: Flask, db: SQLAlchemy):
    """Return a function-scoped session."""
    with app.app_context():
        conn = db.engine.connect()
        txn = conn.begin()

        try:
            options = {"bind": conn, "binds":{}}
            sess = db._make_scoped_session(options=options)
        except Exception as err:
            app.logger.debug(err)
            app.logger.debug("done")

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


@pytest.fixture(autouse=True)
def run_around_tests(db: SQLAlchemy):
    # run before each test
    yield
    # run after each test
    db.session.rollback()
    db.session.execute(text("TRUNCATE TABLE businesses CASCADE"))
    db.session.execute(text("TRUNCATE TABLE batches CASCADE"))
    db.session.commit()
