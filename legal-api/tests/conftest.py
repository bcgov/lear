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
import datetime
import time
from contextlib import contextmanager, suppress
import re
import pytest
import json
from http import HTTPStatus

from flask_migrate import Migrate, upgrade
from sqlalchemy import event, text
from sqlalchemy.schema import DropConstraint, MetaData
from unittest import mock
import requests_mock
import os

from legal_api import create_app
from legal_api import jwt as _jwt
from legal_api.models import db as _db

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
    _app = create_app('testing')

    return _app


@pytest.fixture(scope='function')
def app_ctx(event_loop):
    # def app_ctx():
    """Return a session-wide application configured in TEST mode."""
    _app = create_app('testing')
    with _app.app_context():
        yield _app


@pytest.fixture
def config(app):
    """Return the application config."""
    return app.config


@pytest.fixture(scope='function')
def app_request():
    """Return a session-wide application configured in TEST mode."""
    _app = create_app('testing')

    return _app


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


@pytest.fixture(scope='session')
def db(app):  # pylint: disable=redefined-outer-name, invalid-name
    """Return a session-wide initialised database.

    Drops all existing tables - Meta follows Postgres FKs
    """
    with app.app_context():
        # Clear out any existing tables
        metadata = MetaData(_db.engine)
        metadata.reflect()
        with suppress(Exception):
            metadata.drop_all()
        with suppress(Exception):
            _db.drop_all()

        sequence_sql = """SELECT sequence_name FROM information_schema.sequences
                          WHERE sequence_schema='public'
                       """

        sess = _db.session()
        for seq in [name for (name,) in sess.execute(text(sequence_sql))]:
            with suppress(Exception):
                sess.execute(text('DROP SEQUENCE public.%s ;' % seq))
                print('DROP SEQUENCE public.%s ' % seq)
        sess.commit()

        # drop enums
        enum_type_sql = "SELECT typname FROM pg_type WHERE typcategory = 'E'"
        for enum_name in [name for (name,) in sess.execute(text(enum_type_sql))]:
            with suppress(Exception):
                sess.execute(text('DROP TYPE %s ;' % enum_name))
                print('DROP TYPE %s ' % enum_name)
        sess.commit()

        # For those who have local databases on bare metal in local time.
        # Otherwise some of the returns will come back in local time and unit tests will fail.
        # The current DEV database uses UTC.
        sess.execute("SET TIME ZONE 'UTC';")
        sess.commit()

        # ############################################
        # There are 2 approaches, an empty database, or the same one that the app will use
        #     create the tables
        #     _db.create_all()
        # or
        # Use Alembic to load all of the DB revisions including supporting lookup data
        # This is the path we'll use in legal_api!!

        # even though this isn't referenced directly, it sets up the internal configs that upgrade needs
        Migrate(app, _db)
        upgrade()

        return _db


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
    docker_services.start('nats')
    time.sleep(2)


@pytest.fixture(scope='session')
def minio_server(docker_services):
    """Create the minio services that the integration tests will use."""
    docker_services.start('minio')
    with suppress(Exception):
        docker_services.wait_for_service('minio', 9000)
    time.sleep(10)

DOCUMENT_API_URL = os.getenv('DOCUMENT_API_URL', 'http://document-api.com')
DOCUMENT_API_VERSION = os.getenv('DOCUMENT_API_VERSION', '/api/v1')
DOCUMENT_SVC_URL = f'{DOCUMENT_API_URL + DOCUMENT_API_VERSION}/documents'
DOCUMENT_PRODUCT_CODE = os.getenv('DOCUMENT_PRODUCT_CODE', 'LEGAL_API')

@pytest.fixture()
def mock_doc_service():
  mock_response = {
      'identifier': 1,
      'url': 'https://document-service.com/document/1'
  }
  with requests_mock.Mocker(real_http=True) as mock:
    post_url = f'{DOCUMENT_SVC_URL}/application-reports/{DOCUMENT_PRODUCT_CODE}/'
    mock.post(re.compile(f"{post_url}.*"), status_code=HTTPStatus.CREATED, text=json.dumps(mock_response))
    get_url = f'{DOCUMENT_SVC_URL}/application-reports/{DOCUMENT_PRODUCT_CODE}/'
    mock.get(re.compile(f"{get_url}.*"), status_code=HTTPStatus.OK, text=json.dumps(mock_response))
    yield mock