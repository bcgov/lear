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
"""Create SQLAlchemy and Schema managers.

These will get initialized by the application using the models
"""
from datetime import datetime

from flask import current_app
from flask_sqlalchemy import SignallingSession, SQLAlchemy
from sql_versioning import TransactionManager
from sql_versioning import disable_versioning as _new_disable_versioning
from sql_versioning import enable_versioning as _new_enable_versioning
from sql_versioning import version_class as _new_version_class
from sqlalchemy import event, orm
from sqlalchemy.orm import Session, mapper
from sqlalchemy_continuum import make_versioned
from sqlalchemy_continuum import version_class as _old_version_class
from sqlalchemy_continuum.manager import VersioningManager


# by convention in the Flask community these are lower case,
# whereas pylint wants them upper case
db = SQLAlchemy()  # pylint: disable=invalid-name


class Transaction(db.Model):
    """This class manages the transaction."""

    __tablename__ = 'transaction'

    id = db.Column(
                db.BigInteger,
                db.Sequence('transaction_id_seq'),
                primary_key=True,
                autoincrement=True
            )
    remote_addr = db.Column(db.String(50), nullable=True)
    issued_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=True)


def print_versioning_info():
    """
    Print the current versioning status if not already printed.

    This should only be called within an application context.
    """
    try:
        from legal_api.services import flags as flag_service  # pylint: disable=import-outside-toplevel

        current_service = current_app.config.get('SERVICE_NAME')
        if current_service:
            db_versioning = flag_service.value('db-versioning')
            use_new_versioning = (bool(db_versioning) and bool(db_versioning.get(current_service)))
            current_versioning = 'new' if use_new_versioning else 'old'
            current_app.logger.info(f'\033[31mService: {current_service}, db versioning={current_versioning}\033[0m')
    except Exception as err:
        # Don't crash if something goes wrong
        current_app.logger.error('Unable to read flags: %s' % repr(err), exc_info=True)


def init_db(app):
    """Initialize database using flask app and configure db mappers.

    :param app: Flask app
    :return: None
    """
    db.init_app(app)
    orm.configure_mappers()

    with app.app_context():
        print_versioning_info()


# TODO: remove versioning switching logic
# TODO: remove debugging variables, messages, and decorators
versioning_manager = VersioningManager(transaction_cls=Transaction)


def _old_enable_versioning():
    """Enable old versioning.

    :return: None
    """
    versioning_manager.track_operations(mapper)
    versioning_manager.track_session(Session)


def _old_disable_versioning():
    """Disable old versioning.

    :return: None
    """
    versioning_manager.remove_operations_tracking(mapper)
    versioning_manager.remove_session_tracking(Session)


def _old_get_transaction_id(session):
    """Get the transaction ID using the old versioning.

    :param session: The database session instance.
    :return: The transaction ID
    """
    uow = versioning_manager.unit_of_work(session)
    transaction = uow.create_transaction(session)
    return transaction.id


def _new_get_transaction_id(session):
    """Get the transaction ID using the new versioning.

    :param session: The database session instance.
    :return: The transaction ID
    """
    new_transaction_manager = TransactionManager(session)
    return new_transaction_manager.create_transaction()


class VersioningProxy:
    """A proxy class to handle switching between old and new versioning extension."""

    _current_versioning = None  # only used to set a session's versioning if this session is unset
    _is_initialized = False

    _versioning_control = {
        'old': {
            'enable': _old_enable_versioning,
            'disable': _old_disable_versioning,
            'version_class': _old_version_class,
            'get_transaction_id': _old_get_transaction_id
        },
        'new': {
            'enable': _new_enable_versioning,
            'disable': _new_disable_versioning,
            'version_class': _new_version_class,
            'get_transaction_id': _new_get_transaction_id
        }
    }

    @classmethod
    def _check_versioning(cls):
        """Check which versioning should be used based on feature flag.

        :return: None
        """
        from legal_api.services import flags  # pylint: disable=import-outside-toplevel
        current_service = current_app.config['SERVICE_NAME']
        db_versioning = flags.value('db-versioning')
        use_new_versioning = (bool(db_versioning) and bool(db_versioning.get(current_service)))
        cls._current_versioning = 'new' if use_new_versioning else 'old'

    @classmethod
    def _initialize_versioning(cls):
        """Initialize versioning.

        :return: None
        """
        cls._is_initialized = True
        cls._check_versioning()
        disabled = 'new' if cls._current_versioning == 'old' else 'old'
        cls._versioning_control[disabled]['disable']()

    @classmethod
    def _switch_versioning(cls, previous, current):
        """Switch versioning from one to the other.

        :param previous: The previously used versioning.
        :param current: The versioning system to switch to.
        :return: None
        """
        cls._versioning_control[previous]['disable']()
        cls._versioning_control[current]['enable']()
        # Print when versioning changes
        current_app.logger.info(f'\033[31mVersioning changed: {previous} -> {current}\033[0m')

    @classmethod
    def lock_versioning(cls, session, transaction):
        """Lock versioning for the session.

        This ensures that only one versioning extension is enabled throughout the session.

        :param session: The database session instance.
        :param transaction: The transaction associated with the session.
        :return: None
        """
        if '_versioning_locked' not in session.info:
            if not cls._is_initialized:
                cls._initialize_versioning()
            else:
                previous_versioning = cls._current_versioning
                cls._check_versioning()

                if cls._current_versioning != previous_versioning:
                    cls._switch_versioning(previous_versioning, cls._current_versioning)

            session.info['_versioning_locked'] = cls._current_versioning
            session.info['_transactions_locked'] = []

        session.info['_transactions_locked'].append(transaction)

    @classmethod
    def unlock_versioning(cls, session, transaction):
        """Unlock versioning for the session.

        It is unlocked once all the active transactions are complete.

        :param session: The database session instance.
        :param transaction: The transaction associated with the session.
        :return: None
        """
        if '_versioning_locked' in session.info and '_transactions_locked' in session.info:
            session.info['_transactions_locked'].remove(transaction)

            if not session.info['_transactions_locked']:
                session.info.pop('_versioning_locked', None)
                session.info.pop('_transactions_locked', None)

    @classmethod
    def get_transaction_id(cls, session):
        """Get the transaction ID for the session.

        :param session: The database session instance.
        :return: The transaction ID.
        """
        transaction_id = None
        current_versioning = session.info['_versioning_locked']

        transaction_id = cls._versioning_control[current_versioning]['get_transaction_id'](session)

        return transaction_id

    @classmethod
    def version_class(cls, session, obj):
        """Return version class for an object based in the session.

        :param session: The database session instance.
        :param obj: The object for which the version class is needed.
        :return: The version class of the object.
        """
        if not session.in_transaction():  # trigger versioning setup listener
            session.begin()

        current_versioning = session.info['_versioning_locked']

        return cls._versioning_control[current_versioning]['version_class'](obj)


def setup_versioning():
    """Set up and initialize versioning switching.

    :return: None
    """
    # use SignallingSession to skip events for continuum's internal session/txn operations
    @event.listens_for(SignallingSession, 'after_transaction_create')
    def after_transaction_create(session, transaction):
        VersioningProxy.lock_versioning(session, transaction)

    @event.listens_for(SignallingSession, 'after_transaction_end')
    def clear_transaction(session, transaction):
        VersioningProxy.unlock_versioning(session, transaction)

    _new_enable_versioning(transaction_cls=Transaction)
    make_versioned(user_cls=None, manager=versioning_manager)


# TODO: enable versioning switching
# it should be called before data model initialized, otherwise, old versioning doesn't work properly
setup_versioning()


# make_versioned(user_cls=None, manager=versioning_manager)
