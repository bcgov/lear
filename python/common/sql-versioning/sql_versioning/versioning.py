# Copyright © 2024 Province of British Columbia
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
"""Versioned mixin class, listeners and other utilities."""
import datetime
from contextlib import suppress

from sqlalchemy import (BigInteger, Column, DateTime, Integer, SmallInteger,
                        String, and_, event, func, insert, inspect, select,
                        update)
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import Session, mapper

from .debugging import debug

Base = declarative_base()


# ---------- Utilities ----------
def _is_obj_modified(obj):
    """
    Check if the properties and relationships of the given object have been modified.

    :param obj: The object to inspect for changes.
    :return: True if any property or relationship has been modified, otherwise False.
    """
    column_names = inspect(obj.__class__).columns.keys()
    relationship_keys = inspect(obj.__class__).relationships.keys()

    for key, attr in inspect(obj).attrs.items():
        if key in column_names:
            if attr.history.has_changes():
                return True
        if key in relationship_keys:
            if attr.history.has_changes():
                return True
    return False


def _is_session_modified(session):
    """Check if the session contains modified versioned objects.
    
    :param session: The database sesseion instance.
    :return: True if the session contains modified versioned objects, otherwise False.
    """
    for obj in versioned_objects(session):
        if obj in session.deleted or session.new:
            return True
        if obj in session.dirty and _is_obj_modified(obj):
            return True
    return False


def _get_operation_type(session, obj):
    """Return the operation type for the given object within the session.
    
    :param session: The database session instance.
    :param obj: The object to determine the operation type.
    :return: The operation type ('I' for insert, 'U' for update, 'D' for delete), or None if unchanged.
    """
    if obj in session.new:
        return 'I'
    elif obj in session.dirty:
        return 'U' if _is_obj_modified(obj) else None
    elif obj in session.deleted:
        return 'D'
    return None


def _create_version(session, target, operation_type):
    """Create and updates a versioned record given the target object and operation type.
    
    :param session: The database session instance.
    :param target: The object to create version.
    :param operation_type: The type of operation ('I', 'U', 'D') being performed on the object.
    :return: None
    """

    print(f'\033[32mCreating version for {target.__class__.__name__} (id={target.id}), operation_type: {operation_type}\033[0m')

    if not session:
        print(f'\033[32mSkipping version creation for {target.__class__.__name__} (id={target.id})\033[0m')
        return

    transaction_manager = TransactionManager(session)
    transaction_id = transaction_manager.get_current_transaction_id()

    if transaction_id is None:
        print(f'\033[31mError - Unable to create transaction for {target.__class__.__name__} (id={target.id})\033[0m')
        return

    VersionClass = target.__class__.__versioned_cls__

    # Check if a version for this transaction already exists
    existing_version = session.execute(
        select(VersionClass).where(
            and_(
                VersionClass.id == target.id,
                VersionClass.transaction_id == transaction_id
            )
        )
    ).scalar_one_or_none()

    # Prepare new version data
    new_version_data = {
        'id': target.id,
        'transaction_id': transaction_id,
        'end_transaction_id': None,
        'operation_type': {'I': 0, 'U': 1, 'D': 2}.get(operation_type, 1)
    }

    mapper = inspect(target.__class__)

    for column in mapper.columns:
        if column.name not in ['transaction_id', 'end_transaction_id', 'operation_type']:
            property_name = mapper.get_property_by_column(column).key
            if hasattr(target, property_name):
                new_version_data[column.name] = getattr(target, property_name)

    if existing_version:
        # Update the existing version
        session.execute(
            update(VersionClass).
            where(and_(
                VersionClass.id == target.id,
                VersionClass.transaction_id == transaction_id
            )).
            values(new_version_data)
        )
    else:
        # Insert a new version
        session.execute(insert(VersionClass).values(new_version_data))

    # Close any open versions
    session.execute(
        update(VersionClass).
        where(and_(
            VersionClass.id == target.id,
            VersionClass.end_transaction_id.is_(None),
            VersionClass.transaction_id != transaction_id
        )).
        values(end_transaction_id=transaction_id)
    )

    print(f'\033[32mVersion created/updated for {target.__class__.__name__} (id={target.id}), transaction_id: {transaction_id}\033[0m')


# ---------- Transaction Related Classes ----------
class TransactionFactory:
    """Factory to create or return singleton Transaction model."""

    _transaction_model = None

    @staticmethod
    def create_transaction_model(transaction_cls=None):
        """Create or return the existing Transaction model.

        :param transaction_cls: A custom transaction model class. If provided, 
        it replaces the default Transaction model. Defaults to None.

        :return: Transaction model class (either custom or default).
        """
    
        if transaction_cls:
            TransactionFactory._transaction_model = transaction_cls

        elif TransactionFactory._transaction_model is None:
            class Transaction(Base):
                __tablename__ = 'transaction'

                id = Column(BigInteger, primary_key=True, autoincrement=True)
                issued_at = Column(DateTime(timezone=False), default=datetime.datetime.utcnow, nullable=True)
                remote_addr = Column(String(50), nullable=True)
            
            TransactionFactory._transaction_model = Transaction

        return TransactionFactory._transaction_model


class TransactionManager:
    """Handle transaction creation, retrieval, and cleanup for a session."""

    def __init__(self, session):
        """Initialize a TransactionManager

        :param session: The database session instance.
        """
        self.session = session
        self.transaction_model = TransactionFactory.create_transaction_model()

    @debug
    def create_transaction(self):
        """Create a new transaction in the session.

        :return: The ID of the created transaction.
        """

        if 'current_transaction_id' in self.session.info:
            print(f"\033[32mPoping out existing transaction: {self.session.info['current_transaction_id']}\033[0m")
            self.session.info.pop('current_transaction_id', None)

        # Use insert().returning() to get the ID and issued_at without committing
        stmt = insert(self.transaction_model).values(
            issued_at = func.now()
        ).returning(self.transaction_model.id, self.transaction_model.issued_at)
        result = self.session.execute(stmt)
        transaction_id, issued_at = result.first()

        print(f'\033[32mCreated new transaction: {transaction_id}\033[0m')

        self.session.info['current_transaction_id'] = transaction_id
        print(f'\033[32mSet current_transaction_id: {transaction_id}\033[0m')
        return transaction_id

    def get_current_transaction_id(self):
        """Return the current transaction_id stored in the session.
        
        :return: The current transaction ID in the session.
        """
        if 'current_transaction_id' in self.session.info:
            return self.session.info.get('current_transaction_id')
        else:
            return self.create_transaction()

    @debug
    def clear_current_transaction(self):
        """Clear the current transaction_id stored in the session.
        
        :return: None
        """
        if self.session.transaction.nested:
            print(f"\033[32mSkip clearing nested transaction\033[0m")
            return
        print(f"\033[32mClearing current transaction: {self.session.info.get('current_transaction_id')}\033[0m")
        self.session.info.pop('current_transaction_id', None)


# ---------- Event Listeners ----------
@debug
def _before_flush(session, flush_context, instances):
    """Trigger before a flush operation to ensure a transaction is created."""
    try:
        if not _is_session_modified(session):
            print('\033[31mThere is no modified versioned object in this session.\033[0m')
            return
        
        if 'current_transaction_id' in session.info:
            print(f"\033[31mtransaction_id={session.info['current_transaction_id']} exists before flush.\033[0m")
        else:
            print('\033[31mCreating transaction before flush.\033[0m')
            transaction_manager = TransactionManager(session)
            transaction_manager.create_transaction()

    except Exception as e:
        raise e


@debug
def _after_flush(session, flush_context):
    """Trigger after a flush operation to create version records for changed objects."""
    try:
        for obj in versioned_objects(session):
            operation_type = _get_operation_type(session, obj)
            if operation_type:
                _create_version(session, obj, operation_type)
    except Exception as e:
        raise e


@debug
def _clear_transaction(session):
    """Clears the current transaction from the session after commit or rollback."""
    try:
        transaction_manager = TransactionManager(session)
        transaction_manager.clear_current_transaction()
    except Exception as e:
        raise e


EVENT_LISTENERS = {
    'before_flush': _before_flush,
    'after_flush': _after_flush,
    'after_commit': _clear_transaction,
    'after_rollback': _clear_transaction
}


# ---------- Main Versioning Class/Functions ----------
class Versioned:
    """Class to add versioning capability to models."""

    @declared_attr
    def __versioned_cls__(cls):
        """Return the versioned class associated with the model.

        :return: The versioned class.
        """
        return cls.get_or_create_version_class()

    @classmethod
    def get_or_create_version_class(cls):
        """Create a versioned class.

        :return: The versioned class.
        """
        if not hasattr(cls, '_version_cls'):
            class_name = f'{cls.__name__}Version'
            table_name = f'{cls.__tablename__}_version'

            attrs = {
                '__tablename__': table_name,
                'id': Column(Integer, primary_key=True),
                'transaction_id': Column(BigInteger, primary_key=True, nullable=False),
                'end_transaction_id': Column(BigInteger, nullable=True),
                'operation_type': Column(SmallInteger, nullable=False),
            }

            # We'll add columns from the original table later
            cls._version_cls = type(class_name, (Base,), attrs)

            # Add this class to a list to be processed later
            if not hasattr(cls, '_pending_version_classes'):
                cls._pending_version_classes = []
            cls._pending_version_classes.append(cls)

        return cls._version_cls

    @classmethod
    def __init_subclass__(cls, **kwargs):
        """
        Initialize subclass and register a listener to configure versioned 
        classes after mapper configuration.

        :param kwargs: Arguments for the subclass.
        :return: None
        """
        super().__init_subclass__(**kwargs)
        event.listen(mapper, 'after_configured', cls._after_configured)

    @classmethod
    def _after_configured(cls):
        """
        Trigger after configured. Add columns from the original table to 
        the versioned class.

        :return: None
        """
        if hasattr(cls, '_pending_version_classes'):
            for pending_cls in cls._pending_version_classes:
                version_cls = pending_cls._version_cls
                mapper = inspect(pending_cls)
                # Now add columns from the original table
                for c in mapper.columns:
                    # Make sure table's column name and class's property name can be different
                    property_name = mapper.get_property_by_column(c).key
                    if not hasattr(version_cls, property_name):
                        setattr(version_cls, property_name, Column(c.name, c.type))
            delattr(cls, '_pending_version_classes')


def version_class(obj):
    """Return the version class associated with a model.

    :param obj: The object to get the version class for.
    :return: The version class or None if not found.
    """
    with suppress(Exception):
        versioned_class = obj.__versioned_cls__
        print(f'\033[32mVersioned Class={versioned_class}\033[0m')
        return versioned_class
    return None


def versioned_objects(session):
    """Yield versioned objects that have been changed from the session.
    
    :param session: The database session instance.
    :return: Generator of versioned objects.
    """
    for obj in session.new.union(session.dirty).union(session.deleted):
        if isinstance(obj, Versioned):
            yield obj


@debug
def enable_versioning(transaction_cls=None):
    """Enable versioning. It registers listeners.

    :param transaction_cls: Optional custom transaction class used for versioning.
    :return: None
    """
    try:
        TransactionFactory.create_transaction_model(transaction_cls)

        for event_name, listener in EVENT_LISTENERS.items():
            event.listen(Session, event_name, listener)
    except Exception as e:
        raise e


@debug
def disable_versioning():
    """Disable versioning. It removes listeners.
    
    :return: None
    """
    try:
        for event_name, listener in EVENT_LISTENERS.items():
            event.remove(Session, event_name, listener)
    except Exception as e:
        raise e
