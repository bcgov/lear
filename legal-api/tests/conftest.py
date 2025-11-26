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
from datetime import timezone
import time
from contextlib import contextmanager, suppress
import re
import pytest
from unittest.mock import patch
import json
from http import HTTPStatus

from flask_migrate import Migrate, upgrade
from ldclient.integrations.test_data import TestData
from testcontainers.postgres import PostgresContainer
from sqlalchemy import event, text
from sqlalchemy.schema import MetaData
import requests_mock

from legal_api import create_app
from legal_api import jwt as _jwt
from legal_api.config import TestConfig
from legal_api.models import db as _db

postgres = PostgresContainer("postgres:16-alpine")

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


@pytest.fixture(scope='session')
def app(ld):
    """Return a session-wide application configured in TEST mode."""
    TestConfig.SQLALCHEMY_DATABASE_URI = postgres.get_connection_url()
    options = {
        'ld_test_data':ld,
        'config': TestConfig,
    }
    _app = create_app("testing", **options)


    return _app


@pytest.fixture(scope='function')
def app_ctx(ld, event_loop):
    # def app_ctx():
    """Return a session-wide application configured in TEST mode."""
    TestConfig.SQLALCHEMY_DATABASE_URI = postgres.get_connection_url()
    options = {
        'ld_test_data':ld,
        'config': TestConfig,
    }
    _app = create_app("testing", **options)
    with _app.app_context():
        yield _app


@pytest.fixture
def config(app):
    """Return the application config."""
    return app.config


@pytest.fixture(scope='function')
def app_request(ld):
    """Return a session-wide application configured in TEST mode."""
    TestConfig.SQLALCHEMY_DATABASE_URI = postgres.get_connection_url()
    options = {
        'ld_test_data':ld,
        'config': TestConfig,
    }
    _app = create_app("testing", **options)

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
    Migrate(app, _db)
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


@pytest.fixture(scope='session')
def minio_server(docker_services):
    """Create the minio services that the integration tests will use."""
    docker_services.start('minio')
    with suppress(Exception):
        docker_services.wait_for_service('minio', 9000)
    time.sleep(10)


DOCUMENT_API_URL = 'http://document-api.com'
DOCUMENT_API_VERSION = '/api/v1'
DOCUMENT_SVC_URL = f'{DOCUMENT_API_URL + DOCUMENT_API_VERSION}/documents'
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
        yield mock
