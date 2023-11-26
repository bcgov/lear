# Copyright © 2023 Province of British Columbia
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
"""Tests for the queue worker are contained here."""

import os
from unittest.mock import patch

import pytest
from flask import Flask
from flask_migrate import Migrate, upgrade
from legal_api import db as _db
from legal_api.models import Filing
from sqlalchemy import event, text
from sqlalchemy.schema import MetaData

from entity_digital_credentials.config import get_named_config
from entity_digital_credentials.worker import process_digital_credential
from tests.unit import create_business, create_filing


class QueueException(Exception):
    """Base exception for the Queue Services."""


# Fixtures
@pytest.fixture(scope='session')
def app():
    """Return a session-wide application configured in TEST mode."""
    _app = Flask(__name__)
    _app.config.from_object(get_named_config('testing'))
    _db.init_app(_app)

    return _app


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
            except Exception as err:  # pylint: disable=broad-except; # noqa: B902
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
        Migrate(app, _db, directory=legal_api_dir)
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

        # For those who have local databases on bare metal in local time.
        # Otherwise some of the returns will come back in local time and unit tests will fail.
        # The current DEV database uses UTC.
        sess.execute("SET TIME ZONE 'UTC';")
        sess.commit()

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


@pytest.mark.asyncio
@patch('entity_digital_credentials.digital_credentials_processors.admin_revoke.process')
@patch('entity_digital_credentials.digital_credentials_processors.business_number.process')
@patch('entity_digital_credentials.digital_credentials_processors.change_of_registration.process')
@patch('entity_digital_credentials.digital_credentials_processors.dissolution.process')
@patch('entity_digital_credentials.digital_credentials_processors.put_back_on.process')
async def test_processes_not_run(mock_put_back_on, mock_dissolution, mock_change_of_registration,
                                 mock_business_number, mock_admin_revoke, app, session):
    """Assert processors are not called if message type is not supported."""
    # Arrange
    dc_msg = {'type': 'bc.registry.business.test', 'identifier': 'FM0000001'}

    # Act
    await process_digital_credential(dc_msg, flask_app=app)

    # Assert
    mock_admin_revoke.assert_not_called()
    mock_business_number.assert_not_called()
    mock_change_of_registration.assert_not_called()
    mock_dissolution.assert_not_called()
    mock_put_back_on.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize('dc_msg', [{
    'type': 'bc.registry.admin.revoke',
    'identifier': 'FM0000001'
}, {
    'type': 'bc.registry.business.bn',
    'identifier': 'FM0000002'
}])
@patch('entity_digital_credentials.digital_credentials_processors.admin_revoke.process')
@patch('entity_digital_credentials.digital_credentials_processors.business_number.process')
@patch('entity_digital_credentials.digital_credentials_processors.change_of_registration.process')
@patch('entity_digital_credentials.digital_credentials_processors.dissolution.process')
@patch('entity_digital_credentials.digital_credentials_processors.put_back_on.process')
async def test_processes_no_filing_required(mock_put_back_on, mock_dissolution, mock_change_of_registration,
                                            mock_business_number, mock_admin_revoke, dc_msg, app, session):
    """Assert processor runs if given the right message type."""
    # Arrange
    business = create_business(dc_msg['identifier'])

    # Act
    await process_digital_credential(dc_msg, flask_app=app)

    # Assert
    if dc_msg['type'] == 'bc.registry.admin.revoke':
        mock_admin_revoke.assert_called_once()
        assert business.identifier == 'FM0000001'
        mock_admin_revoke.assert_called_with(business)

        # Other processors should not be called
        mock_business_number.assert_not_called()
        mock_change_of_registration.assert_not_called()
        mock_dissolution.assert_not_called()
        mock_put_back_on.assert_not_called()
    elif dc_msg['type'] == 'bc.registry.business.bn':
        mock_business_number.assert_called_once()
        assert business.identifier == 'FM0000002'
        mock_business_number.assert_called_with(business)

        # Other processors should not be called
        mock_admin_revoke.assert_not_called()
        mock_change_of_registration.assert_not_called()
        mock_dissolution.assert_not_called()
        mock_put_back_on.assert_not_called()
    else:
        assert False


@pytest.mark.asyncio
@pytest.mark.parametrize('dc_msg', [{
    'type': 'bc.registry.business.changeOfRegistration',
    'identifier': 'FM0000001',
    'data': {'filing': {'header': {'filingId': None}}}
}, {
    'type': 'bc.registry.business.dissolution',
    'identifier': 'FM0000002',
    'data': {'filing': {'header': {'filingId': None}}}
}, {
    'type': 'bc.registry.business.putBackOn',
    'identifier': 'FM0000003',
    'data': {'filing': {'header': {'filingId': None}}}
}])
@patch('entity_digital_credentials.digital_credentials_processors.admin_revoke.process')
@patch('entity_digital_credentials.digital_credentials_processors.business_number.process')
@patch('entity_digital_credentials.digital_credentials_processors.change_of_registration.process')
@patch('entity_digital_credentials.digital_credentials_processors.dissolution.process')
@patch('entity_digital_credentials.digital_credentials_processors.put_back_on.process')
async def test_processes_filing_required(mock_put_back_on, mock_dissolution, mock_change_of_registration,
                                         mock_business_number, mock_admin_revoke, dc_msg, app, session):
    """Assert processor runs if given the right message type."""
    # Arrange
    business = create_business(dc_msg['identifier'])
    filing_type = dc_msg['type'].replace('bc.registry.business.', '')
    filing = create_filing(session, business.id, None, filing_type, Filing.Status.COMPLETED.value)
    dc_msg['data']['filing']['header']['filingId'] = filing.id

    # Act
    await process_digital_credential(dc_msg, flask_app=app)

    # Assert
    if dc_msg['type'] == 'bc.registry.business.changeOfRegistration':
        mock_change_of_registration.assert_called_once()
        assert business.identifier == 'FM0000001'
        mock_change_of_registration.assert_called_with(business, filing)

        # Other processors should not be called
        mock_admin_revoke.assert_not_called()
        mock_business_number.assert_not_called()
        mock_dissolution.assert_not_called()
        mock_put_back_on.assert_not_called()
    elif dc_msg['type'] == 'bc.registry.business.dissolution':
        mock_dissolution.assert_called_once()
        assert business.identifier == 'FM0000002'
        mock_dissolution.assert_called_with(business, 'test')

        # Other processors should not be called
        mock_admin_revoke.assert_not_called()
        mock_business_number.assert_not_called()
        mock_change_of_registration.assert_not_called()
        mock_put_back_on.assert_not_called()
    elif dc_msg['type'] == 'bc.registry.business.putBackOn':
        mock_put_back_on.assert_called_once()
        assert business.identifier == 'FM0000003'
        mock_put_back_on.assert_called_with(business)

        # Other processors should not be called
        mock_admin_revoke.assert_not_called()
        mock_business_number.assert_not_called()
        mock_change_of_registration.assert_not_called()
        mock_dissolution.assert_not_called()
    else:
        assert False


@pytest.mark.asyncio
@pytest.mark.parametrize('dc_msg', [{
    'type': 'bc.registry.business.changeOfRegistration',
    'identifier': 'FM0000001'
}, {
    'type': 'bc.registry.business.changeOfRegistration',
    'identifier': 'FM0000001',
    'data': {}
}, {
    'type': 'bc.registry.business.changeOfRegistration',
    'identifier': 'FM0000001',
    'data': {'filing': {}}
}, {
    'type': 'bc.registry.business.changeOfRegistration',
    'identifier': 'FM0000001',
    'data': {'filing': {'header': {}}}
}])
async def test_process_failure_filing_required(app, session, dc_msg):
    """Assert processor throws QueueException if filing data not in message."""
    # Arrange
    from entity_queue_common.service_utils import QueueException

    # Act
    with pytest.raises(QueueException) as excinfo:
        await process_digital_credential(dc_msg, flask_app=app)

    # Assert
    assert 'Digital credential message is missing data.' in str(excinfo)


@pytest.mark.asyncio
async def test_process_failure_no_identifier_no_filing_required(app, session):
    """Assert processor throws QueueException if no idenfiier in message."""
    # Arrange
    from entity_queue_common.service_utils import QueueException
    dc_msg = {'type': 'bc.registry.admin.revoke'}

    # Act
    with pytest.raises(QueueException) as excinfo:
        await process_digital_credential(dc_msg, flask_app=app)

    # Assert
    assert 'Digital credential message is missing identifier' in str(excinfo)


@pytest.mark.asyncio
async def test_process_failure_no_business_no_filing_required(app, session):
    """Assert processor throws Exception if idenfiier in message but business not found."""
    # Arrange
    identifier = 'FM0000001'
    dc_msg = {'type': 'bc.registry.admin.revoke', 'identifier': identifier}

    # Act
    with pytest.raises(Exception) as excinfo:
        await process_digital_credential(dc_msg, flask_app=app)

    # Assert
    assert f'Business with identifier: {identifier} not found.' in str(excinfo)
