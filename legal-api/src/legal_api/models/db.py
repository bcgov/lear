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
import functools
from functools import wraps

from flask import current_app
from flask_sqlalchemy import SignallingSession, SQLAlchemy
from sqlalchemy import event, orm
from sqlalchemy.orm import Session, mapper
from sqlalchemy_continuum import make_versioned, remove_versioning
from sqlalchemy_continuum import version_class as _old_version_class
from sqlalchemy_continuum import versioning_manager

# from sql_versioning.versioned_history import versioned_session
from sql_versioning.versioned_history import TransactionManager
from sql_versioning.versioned_history import disable_versioning as _disable_new_versioning
from sql_versioning.versioned_history import enable_versioning as _enable_new_versioning
from sql_versioning.versioned_history import versioned_cls as _new_version_class


# by convention in the Flask community these are lower case,
# whereas pylint wants them upper case
db = SQLAlchemy()  # pylint: disable=invalid-name

# make_versioned(user_cls=None, plugins=[FlaskPlugin()])
# make_versioned(user_cls=None)


def init_db(app):
    db.init_app(app)
    orm.configure_mappers()


def debug(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f'\033[34m--> Entering {func.__qualname__}()\033[0m')
        ret = func(*args, **kwargs)
        print(f'\033[34m<-- Exiting {func.__qualname__}()\033[0m')
        return ret

    return wrapper


def _enable_old_versioning():
    versioning_manager.track_operations(mapper)
    versioning_manager.track_session(Session)

def _disable_old_versioning():
    versioning_manager.remove_operations_tracking(mapper)
    versioning_manager.remove_session_tracking(Session)

def _old_get_transaction_id(session):
    uow = versioning_manager.unit_of_work(session)
    transaction = uow.create_transaction(session)
    return transaction.id

def _new_get_transaction_id(session):
    new_transaction_manager = TransactionManager(session)
    return new_transaction_manager.create_transaction()


class VersioningProxy:

    _current_versioning = None  # only used to set a session's versioning if this session is unset
    _is_initialized = False

    _versioning_control = {
        'old': {
            'enable': _enable_old_versioning,
            'disable': _disable_old_versioning,
            'version_class': _old_version_class,
            'get_transaction_id': _old_get_transaction_id
        },
        'new': {
            'enable': _enable_new_versioning,
            'disable': _disable_new_versioning,
            'version_class': _new_version_class,
            'get_transaction_id': _new_get_transaction_id
        }
    }

    @classmethod
    @debug
    def lock_versioning(cls, session, transaction):
        print(f"Current service={current_app.config['SERVICE_NAME']}, session={session}, transaction={transaction}")
        if '_versioning_locked' not in session.info:
            if not cls._is_initialized:
                cls._initialize_versioning()
                print(f'\033[31mVersioning locked, current versioning type={cls._current_versioning}(initialized)\033[0m')
            else:
                previous_versioning = cls._current_versioning
                cls._check_versioning()

                # debug - lock_type
                lock_type = 'unchanged'  
                if cls._current_versioning != previous_versioning:
                    cls._switch_versioning(previous_versioning, cls._current_versioning)
                    lock_type = 'switched'

                print(f'\033[31mVersioning locked, current versioning type={cls._current_versioning}({lock_type})\033[0m')
            
            session.info['_versioning_locked'] = cls._current_versioning
            session.info['_transactions_locked'] = []
        
        # debug - else statement
        else:
            print('\033[31mVersioning already set for this session, skip\033[0m')

        session.info['_transactions_locked'].append(transaction)

    @classmethod
    def _check_versioning(cls):
        from legal_api.services import flags
        current_service = current_app.config['SERVICE_NAME']
        db_versioning = flags.value('db-versioning')
        use_new_versioning = (bool(db_versioning.get('initialize-new-versioning'))
                            and bool(db_versioning.get('enable-new-versioning', {}).get(current_service)))
        cls._current_versioning ='new' if use_new_versioning else 'old'
        print(f'\033[31mCurrent versioning={cls._current_versioning}\033[0m')
        
    @classmethod
    def _initialize_versioning(cls):
        cls._is_initialized = True
        cls._check_versioning()
        disabled = 'new' if cls._current_versioning == 'old' else 'old'
        cls._versioning_control[disabled]['disable']()

    @classmethod
    def _switch_versioning(cls, previous, current):
        cls._versioning_control[previous]['disable']()
        cls._versioning_control[current]['enable']()

    @classmethod
    @debug
    def unlock_versioning(cls, session, transaction):
        print(f'Session={session}, transaction={transaction}')
        if '_versioning_locked' in session.info and '_transactions_locked' in session.info:
            session.info['_transactions_locked'].remove(transaction)
            print('\033[35mTransaction unlocked\033[0m')

            if not session.info['_transactions_locked']:
                session.info.pop('_versioning_locked', None)
                session.info.pop('_transactions_locked', None)
                print('\033[31mVersioning unlocked\033[0m')
            
            # debug - else statement
            else:
                print(f"This session has active transaction, can't be unlocked")

        # debug - else statement
        else:
            print("Versioning/Transaction lock doesn't exist, skip")

    @classmethod
    @debug
    def get_transaction_id(cls, session):
        transaction_id = None
        current_versioning = session.info['_versioning_locked']

        print(f'\033[31mCurrent versioning type={current_versioning}\033[0m')
        transaction_id = cls._versioning_control[current_versioning]['get_transaction_id'](session)
        print(f'\033[31mUsing transaction_id = {transaction_id}\033[0m')

        return transaction_id

    @classmethod
    @debug
    def version_class(cls, session, obj):
        if not session.in_transaction():  # trigger versioning setup listener
            session.begin()

        current_versioning = session.info['_versioning_locked']
        print(f'\033[31mCurrent versioning type={current_versioning}\033[0m')

        return cls._versioning_control[current_versioning]['version_class'](obj)


@debug
def setup_versioning():
    @event.listens_for(SignallingSession, 'after_transaction_create')  # skip events for continuum's internal session/txn operations
    @debug
    def after_transaction_create(session, transaction):
        VersioningProxy.lock_versioning(session, transaction)

    @event.listens_for(SignallingSession, 'after_transaction_end')
    @debug
    def clear_transaction(session, transaction):
        VersioningProxy.unlock_versioning(session, transaction)

    _enable_new_versioning()
    make_versioned(user_cls=None)


setup_versioning()  # it should be called before data model initialzed, otherwise, old versioning doesn't work properly
