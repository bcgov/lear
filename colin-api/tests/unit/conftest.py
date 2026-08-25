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
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import event, text

from colin_api import create_app
from colin_api import jwt as _jwt
from colin_api.models import Business, Office, Party, ShareObject

from . import build_business, build_director, build_office, build_share_structure, bypass_auth


@pytest.fixture(scope='session')
def app():
    """Return a session-wide application configured in TEST mode."""
    _app = create_app('testing')

    return _app


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


@pytest.fixture
def authorized(mocker):
    """Bypass the colin service role check - the gate itself is asserted separately."""
    bypass_auth(mocker)


@pytest.fixture
def mock_db(mocker):
    """Mock the Oracle connection for the modules that acquire it directly.

    cursor.fetchone defaults to (0,) so count-style lookups (eg. the snapshot's
    future-effective filing count) read zero; tests needing a specific row (eg. the
    corp password) override the return value.
    """
    cursor = MagicMock()
    cursor.fetchone.return_value = (0,)
    connection = MagicMock()
    connection.cursor.return_value = cursor
    db = MagicMock()  # pylint: disable=invalid-name; mirrors the patched module attribute
    db.connection = connection
    mocker.patch('colin_api.models.business.DB', db)
    mocker.patch('colin_api.models.business_snapshot.DB', db)
    return SimpleNamespace(connection=connection, cursor=cursor)


@pytest.fixture
def mock_lookups(mocker):
    """Stub the model lookups the snapshot composes, with realistic model objects."""
    mocker.patch.object(Business, 'find_by_identifier', return_value=build_business())
    mocker.patch.object(Party, 'get_current', return_value=[build_director()])
    mocker.patch.object(
        Office, 'get_current',
        # the liquidation office proves out-of-scope office types are dropped
        return_value=[build_office('registeredOffice'), build_office('recordsOffice'),
                      build_office('liquidationOffice')]
    )
    mocker.patch.object(ShareObject, 'get_all', return_value=[build_share_structure()])
    mocker.patch.object(Business, 'get_resolutions', return_value=['2020-01-01', '2019-06-15'])


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
