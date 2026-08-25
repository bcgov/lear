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
import json
import os
import pytest
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from http import HTTPStatus

import requests_mock
from flask import Flask
from flask_migrate import Migrate, upgrade
from ldclient.integrations.test_data import TestData
from sqlalchemy import event, text
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import now as _sqla_now
from testcontainers.postgres import PostgresContainer

import business_model_migrations
from business_common.utils import datetime as common_datetime
from business_model.models import db as _db
from legal_api import create_app, jwt as _jwt
from legal_api.config import TestConfig

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
        raise pytest.fail(f'DID RAISE {exception}')


@pytest.fixture
def freeze_datetime_utcnow():
    """Freeze time for testing.
    
    super().now(tz=timezone.utc) is not supported by freezegun.
    So we mock datetime.utcnow() directly.
    """
    @contextmanager
    def _freeze_time(frozen_datetime):
        with patch.object(common_datetime, 'utcnow') as mock_datetime_utcnow:
            mock_datetime_utcnow.return_value = frozen_datetime.replace(tzinfo=timezone.utc)
            yield
    return _freeze_time


@pytest.fixture(scope="session")
def ld():
    """LaunchDarkly TestData source."""
    td = TestData.data_source()
    with open("flags.json") as file:
        data = file.read()
        test_flags: dict[str, dict] = json.loads(data)
        for flag_name, flag_value in test_flags["flagValues"].items():
            # NOTE: should check if isinstance dict and if so, apply each variation
            td.update(td.flag(flag_name).variations(flag_value))
    yield td


@pytest.fixture(scope="session")
def monkey_session():
    """Return a session-wide monkeypatching fixture."""
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


@pytest.fixture(scope='session')
def app(monkey_session, ld, database_service):
    """Return a session-wide application configured in TEST mode."""
    options = {
        'ld_test_data':ld,
    }
    TestConfig.SQLALCHEMY_DATABASE_URI = postgres.get_connection_url()
    _app = create_app("testing", **options)

    def _utcnow_side_effect():
        """super().now(tz=timezone.utc) is not supported by freezegun, so we mock datetime.utcnow() directly."""
        return datetime.now(tz=timezone.utc)
    monkey_session.setattr(common_datetime, 'utcnow', _utcnow_side_effect)


    def _now_side_effect():
        """super().now() is not supported by freezegun, so we mock datetime.now() directly."""
        return datetime.now()
    monkey_session.setattr(common_datetime, 'now', _now_side_effect)

    with _app.app_context():
        yield _app


@pytest.fixture(scope='function')
def app_request(ld, database_setup, monkeypatch):
    """Return a function-scoped Flask app for tests that register routes ad-hoc.

    ``StructuredLogging.get_logger()`` is a staticmethod that returns the
    StructuredLogging instance (not a logger) whenever ``current_app`` is set,
    which corrupts the second app's ``app.logger``. Patch it to always return a
    fresh JSON logger during this fixture.
    """
    from structured_logging.logging import StructuredLogging as _SL, getJSONLogger
    monkeypatch.setattr(_SL, 'get_logger', staticmethod(getJSONLogger))
    TestConfig.SQLALCHEMY_DATABASE_URI = postgres.get_connection_url()
    _app = create_app("testing", ld_test_data=ld)
    with _app.app_context():
        yield _app


@pytest.fixture(scope='session')
def client(app):  # pylint: disable=redefined-outer-name
    """Return a session-wide Flask test client."""
    return app.test_client()


@pytest.fixture(scope='session')
def jwt():
    """Return a session-wide jwt manager."""
    return _jwt


@pytest.fixture(scope="session")
def database_service(request):
    """Start up database."""
    postgres.start()

    def remove_container():
        postgres.stop()
    
    request.addfinalizer(remove_container)


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

    options = dict(bind=connection, binds={})
    scoped = _db._make_scoped_session(options=options)
    _db.session = scoped

    session = scoped()
    # Flask-SQLAlchemy's Session.get_bind() ignores the Session's `bind=` and
    # returns db.engines[None]; force it to use our test connection so writes
    # land inside the outer transaction we just opened.
    session.get_bind = lambda *args, **kwargs: connection
    session.begin_nested()

    # Needed for extra save points in factory functions etc.
    @event.listens_for(session, 'after_transaction_end')
    def restart_savepoint(s, trans):
        if trans.nested and not trans._parent.nested:
            s.begin_nested()

    session.execute(text("SET TIME ZONE 'UTC';"))

    yield scoped

    event.remove(session, 'after_transaction_end', restart_savepoint)
    scoped.close()
    transaction.rollback()
    connection.close()




@pytest.fixture(scope="function")
def mock_bearer_token(app, requests_mock):
    token_mock = requests_mock.post(app.config.get("ACCOUNT_SVC_AUTH_URL"), json={"access_token": "mock-token"})
    return token_mock
    

DOCUMENT_API_URL = 'http://document-api.com'
DOCUMENT_API_VERSION = '/api/v1'
DOCUMENT_SVC_URL = f'{DOCUMENT_API_URL + DOCUMENT_API_VERSION}'
DOCUMENT_PRODUCT_CODE = 'BUSINESS'

@pytest.fixture()
def mock_doc_service():
    mock_response = {
        'identifier': 1,
        'url': 'https://document-service.com/document/1'
    }
    with requests_mock.Mocker(real_http=True) as mock:
        post_url = f'{DOCUMENT_SVC_URL}/application-reports/{DOCUMENT_PRODUCT_CODE}/'
        mock.post(re.compile(f"{post_url}.*"),
                  status_code=HTTPStatus.CREATED,
                  text=json.dumps(mock_response))
        get_url = f'{DOCUMENT_SVC_URL}/application-reports/{DOCUMENT_PRODUCT_CODE}/'
        mock.get(re.compile(f"{get_url}.*"),
                 status_code=HTTPStatus.OK,
                 text=json.dumps(mock_response))
        get_url2 = f'{DOCUMENT_SVC_URL}/application-reports/history/{DOCUMENT_PRODUCT_CODE}/'
        mock.get(re.compile(f"{get_url2}.*"),
                 status_code=HTTPStatus.OK,
                 text=json.dumps(mock_response))
        yield mock


@pytest.fixture()
def mock_drs_service():
    mock_response = []
    with requests_mock.Mocker(real_http=True) as m:
        get_url = f'{DOCUMENT_SVC_URL}/application-reports/{DOCUMENT_PRODUCT_CODE}/'
        get_url2 = f'{DOCUMENT_SVC_URL}/application-reports/history/{DOCUMENT_PRODUCT_CODE}/'
        get_url3 = f'{DOCUMENT_SVC_URL}/application-reports/events/{DOCUMENT_PRODUCT_CODE}/'
        m.register_uri('GET', re.compile(f"{get_url}.*"), json=mock_response, status_code=HTTPStatus.OK)
        m.register_uri('GET', re.compile(f"{get_url2}.*"), json=mock_response, status_code=HTTPStatus.OK)
        m.register_uri('GET', re.compile(f"{get_url3}.*"), json=mock_response, status_code=HTTPStatus.OK)
        yield m
