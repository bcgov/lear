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
from minio.error import S3Error
from sqlalchemy import event, text
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import now as _sqla_now
from testcontainers.postgres import PostgresContainer

import business_model_migrations
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
        with patch('legal_api.utils.datetime.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = frozen_datetime.replace(tzinfo=timezone.utc)
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
    monkey_session.setattr('legal_api.utils.datetime.datetime.utcnow', _utcnow_side_effect)


    def _now_side_effect():
        """super().now() is not supported by freezegun, so we mock datetime.now() directly."""
        return datetime.now()
    monkey_session.setattr('legal_api.utils.datetime.datetime.now', _now_side_effect)

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


@pytest.fixture()
def minio_server(monkeypatch):
    """Create the minio services that the integration tests will use."""
    mock_url = 'https://dummy-minio-url.com/businesses'
    minio_mock = Mock()

    def _presigned_url_side_effect(bucket_name, key, *args, **kwargs):
        return f'{mock_url}/{key}'

    def _put_object_side_effect(bucket_name, key, data, *args, **kwargs):
        # The 'data' argument is a file-like object, read its content.
        # Ensure it's read to the end for completeness, but typically only one read is needed.
        file_content = data.read()
        minio_mock.stored_objects[key] = file_content
        return None

    def _get_object_side_effect(bucket_name, key, *args, **kwargs):
        if key in minio_mock.stored_objects:
            mock_file = Mock()
            mock_file.data = minio_mock.stored_objects[key]
            return mock_file
        raise S3Error("NoSuchKey", "Object does not exist", None, None, None, None)

    def _get_info_side_effect(bucket_name, key, *args, **kwargs):
        if key in minio_mock.stored_objects:
            mock_file = Mock()
            mock_file.size = len(minio_mock.stored_objects[key])
            return mock_file
        raise S3Error("NoSuchKey", "Object does not exist", None, None, None, None)

    def _remove_object_side_effect(bucket_name, key, *args, **kwargs):
        if key in minio_mock.stored_objects:
            del minio_mock.stored_objects[key]
        return None

    minio_mock.stored_objects = {}

    minio_mock.presigned_get_object.side_effect = _presigned_url_side_effect
    minio_mock.presigned_put_object.side_effect = _presigned_url_side_effect
    minio_mock.stat_object.side_effect = _get_info_side_effect
    minio_mock.get_object.side_effect = _get_object_side_effect
    minio_mock.remove_object.side_effect = _remove_object_side_effect
    minio_mock.put_object.side_effect = _put_object_side_effect

    monkeypatch.setattr('legal_api.services.minio.MinioService._get_client', lambda: minio_mock)
    with requests_mock.Mocker() as mock:
        def _mock_put_side_effect(request, context):
            key = request.url.replace(f'{mock_url}/', '', 1)
            minio_mock.stored_objects[key] = request.body
            context.status_code = HTTPStatus.CREATED
            return None

        def _mock_get_side_effect(request, context):
            key = request.url.replace(f'{mock_url}/', '', 1)
            content = minio_mock.stored_objects.get(key)
            if content is not None:
                context.status_code = HTTPStatus.OK
                return content
            else:
                raise S3Error("NoSuchKey", "Object does not exist", None, None, None, None)

        mock.put(re.compile(f"{mock_url}.*"), json=_mock_put_side_effect)
        mock.get(re.compile(f"{mock_url}.*"), content=_mock_get_side_effect)

        yield minio_mock


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
