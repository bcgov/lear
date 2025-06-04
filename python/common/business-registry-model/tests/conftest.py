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
import contextlib
import os
from contextlib import contextmanager

import pytest
import sqlalchemy
from flask import Flask
from flask_migrate import Migrate, upgrade
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, text
from testcontainers.postgres import PostgresContainer

import business_model_migrations
from business_model.models import db as _db
from config import Testing

postgres = PostgresContainer("postgres:16-alpine")


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
