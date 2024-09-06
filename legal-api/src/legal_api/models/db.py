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

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.declarative import declarative_base
from sql_versioning import TransactionManager as NewTransactionManager
from sqlalchemy.orm import sessionmaker, configure_mappers
from sqlalchemy import event, Column, DateTime, func, Integer
from sqlalchemy_continuum import make_versioned, versioning_manager
from sqlalchemy.orm.session import Session as SQLAlchemySession

Base = declarative_base()

class Transaction(Base):
    __tablename__ = 'transaction'

    id = Column(Integer, primary_key=True, autoincrement=True)
    issued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __init__(self, manager=None):
        pass  # We don't need to do anything with the manager in this simplified version

# Initialize SQLAlchemy-Continuum at the module level
make_versioned(user_cls=None)

def initialize_sqlalchemy_continuum(app):
    with app.app_context():
        versioning_manager.declarative_base = db.Model
        versioning_manager.transaction_cls = Transaction
        versioning_manager.options['native_versioning'] = False
        configure_mappers()
        print("SQLAlchemy-Continuum initialized")

class VersioningSwitchableSession(SQLAlchemySession):
    def __init__(self, db=None, **options):
        super().__init__(bind=options.pop('bind', None) or db.engine,
                         binds=options.pop('binds', None) or db.get_binds(db.get_app()),
                         **options)
        self.app = db.get_app()
        self.db = db
        self.versioning_enabled = True
        self.current_versioning = None
        self._old_versioning_disabled = False
        self.new_transaction_manager = NewTransactionManager(self)
        self.options = {'versioning': True}
        self._initialize_versioning()

    def _initialize_versioning(self):
        from legal_api.services import flags
        db_versioning = flags.value('db-versioning')
        use_new_versioning = (bool(db_versioning.get('initialize-new-versioning'))
                              and bool(db_versioning.get('enable-new-versioning', {}).get('legal-api')))
        self.enable_versioning('new' if use_new_versioning else 'old')

    def enable_versioning(self, versioning_type):
        print(f"Enabling versioning: type={versioning_type}")
        self.versioning_enabled = True
        self.current_versioning = versioning_type
        if versioning_type == 'new':
            self._disable_old_versioning()
        else:
            self._enable_old_versioning()
        print(f"Versioning enabled: {versioning_type}")

    def _disable_old_versioning(self):
        print("Disabling old versioning system")
        self._old_versioning_disabled = True
        versioning_manager.options['versioning'] = False
        for obj in self:
            if hasattr(obj, '__versioned__'):
                obj.__versioned__['versioning'] = False

    def _enable_old_versioning(self):
        print("Enabling old versioning system")
        self._old_versioning_disabled = False
        versioning_manager.options['versioning'] = True
        for obj in self:
            if hasattr(obj, '__versioned__'):
                obj.__versioned__['versioning'] = True

    def is_new_versioning_active(self):
        return self.current_versioning == 'new'

    def is_old_versioning_active(self):
        return self.current_versioning == 'old' and not self._old_versioning_disabled

    def _disable_sqlalchemy_continuum(self):
        print("Disabling SQLAlchemy-Continuum versioning")
        self.options['versioning'] = False
        for obj in self:
            if hasattr(obj, '__versioned__'):
                obj.__versioned__['versioning'] = False

    def _enable_sqlalchemy_continuum(self):
        print("Enabling SQLAlchemy-Continuum versioning")
        self.options['versioning'] = True
        versioning_manager.options['native_versioning'] = False

    def get_or_create_transaction(self):
        if self.is_new_versioning_active():
            return self.new_transaction_manager.create_transaction()
        else:
            uow = versioning_manager.unit_of_work(self)
            return uow.current_transaction

    def clear_transaction(self):
        print("Entering clear_transaction")
        if self.is_new_versioning_active():
            self.new_transaction_manager.clear_current_transaction()
        elif self.is_old_versioning_active():
            versioning_manager.clear(self)
        print("Exiting clear_transaction")

    def commit(self):
        print("Entering commit")
        try:
            if self.is_new_versioning_active():
                # New versioning commit logic (if any)
                super().commit()
            elif self.is_old_versioning_active():
                uow = versioning_manager.unit_of_work(self)
                uow.process_before_flush(self)
                super().commit()
                uow.process_after_flush(self)
            else:
                super().commit()
        except Exception as e:
            print(f"Error during commit: {str(e)}")
            self.rollback()
            raise
        finally:
            self.clear_transaction()
            print("Exiting commit")

    def rollback(self):
        print("Entering rollback")
        super().rollback()
        self.clear_transaction()
        print("Exiting rollback")


class CustomSQLAlchemy(SQLAlchemy):
    def create_session(self, options):
        return sessionmaker(class_=VersioningSwitchableSession, db=self, **options)

db = CustomSQLAlchemy()

def init_db(app):
    db.init_app(app)
    initialize_sqlalchemy_continuum(app)

def versioned_session(session):
    @event.listens_for(session, "before_flush")
    def before_flush(session, flush_context, instances):
        print(f"Before flush: new_versioning_active={session.is_new_versioning_active()}, old_versioning_active={session.is_old_versioning_active()}")
        try:
            from legal_api.services import flags
            db_versioning = flags.value('db-versioning')
            enable_new_versioning = db_versioning.get('enable-new-versioning')
            use_new_versioning = (bool(db_versioning.get('initialize-new-versioning'))
                                  and bool(enable_new_versioning.get('legal-api')))

            print(f"DB versioning flag values: {db_versioning}")
            print(f"Use new versioning: {use_new_versioning}")
            print(f"Current versioning: {session.current_versioning}")

            # Update the session's versioning type based on the current flag value
            session.enable_versioning('new' if use_new_versioning else 'old')

            if session.is_new_versioning_active():
                transaction_id = session.get_or_create_transaction()
                for obj in session.new.union(session.dirty).union(session.deleted):
                    if hasattr(obj, '__versioned_cls__'):
                        print(f"Calling _before_flush for object: {obj.__class__.__name__} (id={getattr(obj, 'id', None)})")
                        try:
                            obj._before_flush(session, flush_context, instances)
                        except Exception as e:
                            print(f"Error in _before_flush for object {obj.__class__.__name__} (id={getattr(obj, 'id', None)}): {str(e)}")
            elif session.is_old_versioning_active():
                print("Using old versioning system (SQLAlchemy-Continuum)")
                uow = versioning_manager.unit_of_work(session)
                uow.process_before_flush(session)

            print(f"New versioning active: {session.is_new_versioning_active()}")
        except Exception as e:
            print(f"Error in before_flush: {str(e)}")
            import traceback
            print(traceback.format_exc())
        print("Exiting before_flush")

    @event.listens_for(session, "after_flush")
    def after_flush(session, flush_context):
        print("Entering after_flush")
        try:
            if session.is_old_versioning_active():
                print("Processing after_flush for old versioning")
                uow = versioning_manager.unit_of_work(session)
                uow.process_after_flush(session)
        except Exception as e:
            print(f"Error in after_flush: {str(e)}")
            import traceback
            print(traceback.format_exc())
        print("Exiting after_flush")

    @event.listens_for(session, "after_commit")
    @event.listens_for(session, "after_rollback")
    def clear_transaction(session):
        print("Entering clear_transaction")
        session.clear_transaction()

    return session


def initialize_versioning(app):
    with app.app_context():
        versioned_session(db.session)
    print("Versioning initialized")
