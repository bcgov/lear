"""Versioned mixin class and other utilities."""
import datetime
from contextlib import suppress

from sqlalchemy import (BigInteger, Column, DateTime, Integer, SmallInteger,
                        String, Table, and_, event, func, insert, inspect, or_,
                        select, update)
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import Session, mapper

Base = declarative_base()

class Transaction(Base):
    __tablename__ = 'transaction'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    issued_at = Column(DateTime(timezone=False), default=datetime.datetime.utcnow, nullable=True)
    remote_addr = Column(String(50), nullable=True)

    def __repr__(self):
        return f"<Transaction(id={self.id}, issued_at={self.issued_at})>"


class TransactionManager:

    def __init__(self, session):
        self.session = session

    def create_transaction(self):
        print("Entering create_transaction")
        if 'current_transaction_id' in self.session.info:
            print(f"Reusing existing transaction: {self.session.info['current_transaction_id']}")
            return self.session.info['current_transaction_id']

        # Use insert().returning() to get the ID and issued_at without committing
        stmt = insert(Transaction).values(
            issued_at = None
        ).returning(Transaction.id, Transaction.issued_at)
        result = self.session.execute(stmt)
        transaction_id, issued_at = result.first()

        print(f"Created new transaction: {transaction_id}")

        self.session.info['current_transaction_id'] = transaction_id
        print(f"Set current_transaction_id: {transaction_id}")
        return transaction_id

    def get_current_transaction_id(self):
        return self.session.info.get('current_transaction_id')

    def clear_current_transaction(self):
        print(f"Clearing current transaction: {self.session.info.get('current_transaction_id')}")
        self.session.info.pop('current_transaction_id', None)


class Versioned:

    is_enable = None  # debugging

    @declared_attr
    def __versioned_cls__(cls):
        return cls.get_or_create_version_class()

    @classmethod
    def get_or_create_version_class(cls):
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
        super().__init_subclass__(**kwargs)
        event.listen(mapper, 'after_configured', cls._after_configured)

    @classmethod
    def _after_configured(cls):
        if hasattr(cls, '_pending_version_classes'):
            for pending_cls in cls._pending_version_classes:
                version_cls = pending_cls._version_cls
                # Now add columns from the original table
                for c in pending_cls.__table__.columns:
                    if not hasattr(version_cls, c.name):
                        setattr(version_cls, c.name, Column(c.type))
            delattr(cls, '_pending_version_classes')


def create_version(session, target, operation_type):
    print(f"Creating version for {target.__class__.__name__} (id={target.id}), operation_type: {operation_type}")

    if not session:
        print(f"Skipping version creation for {target.__class__.__name__} (id={target.id})")
        return

    transaction_manager = TransactionManager(session)
    transaction_id = transaction_manager.create_transaction()

    if transaction_id is None:
        print(f"Error: Unable to create transaction for {target.__class__.__name__} (id={target.id})")
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

    for column in inspect(target.__class__).columns:
        if column.name not in ['transaction_id', 'end_transaction_id', 'operation_type']:
            if hasattr(target, column.name):
                new_version_data[column.name] = getattr(target, column.name)

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

    print(f"Version created/updated for {target.__class__.__name__} (id={target.id}), transaction_id: {transaction_id}")


def _before_flush(session, flush_context, instances):
    print("Entering new_before_flush")
    try:
        transaction_manager = TransactionManager(session)
        transaction_manager.create_transaction()

    except Exception as e:
        print(f"Error in new_before_flush: {str(e)}")
        import traceback
        print(traceback.format_exc())
    print("Exiting new_before_flush")


def _after_flush(session, flush_context):
    print("Entering _after_flush")
    try:
        for obj in session.new.union(session.dirty).union(session.deleted):
            if isinstance(obj, Versioned):
                operation_type = 'I' if obj in session.new else 'U' if obj in session.dirty else 'D'
                create_version(session, obj, operation_type)
    except Exception as e:
        print(f"Error in new.after_flush: {str(e)}")
    print("Exiting _after_flush")


def _clear_transaction(session):
    print("Entering new_clear_transaction")
    transaction_manager = TransactionManager(session)
    transaction_manager.clear_current_transaction()
    print("Exiting new_clear_transaction")


event_listeners = {
    'before_flush': _before_flush,
    'after_flush': _after_flush,
    'after_commit': _clear_transaction,
    'after_rollback': _clear_transaction
}


def enable_versioning():
    print('Entering new enable_versioning')
    Versioned.is_enable = True
    try:
        for event_name, listener in event_listeners.items():
            event.listen(Session, event_name, listener)
            print(f'Register {listener}')
        print('Exiting new enable_versioning')
    except Exception as e:
        print(e)
        raise e


def disable_versioning():
    print('Entering new_disable_versioning')
    Versioned.is_enable = False
    try:
        for event_name, listener in event_listeners.items():
            event.remove(Session, event_name, listener)
            print(f'Remove {listener}')
    except Exception as e:
        print(e)
        raise e
    print('Exiting new_disable_versioning')


def versioned_cls(obj):
    with suppress(Exception):
        versioned_class = obj.__versioned_cls__
        print(f'New Versioned Class={versioned_class}')
        return versioned_class
    return None


def history_cls(obj):
    with suppress(Exception):
        history_mapper = obj.__history_mapper__
        history_cls = history_mapper.class_
        return history_cls
    return None

def versioned_objects(iter_):
    for obj in iter_:
        if hasattr(obj, "__history_mapper__"):
            yield obj
