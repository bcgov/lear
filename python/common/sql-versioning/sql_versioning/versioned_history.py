"""Versioned mixin class and other utilities."""
import datetime
from contextlib import suppress
from sqlalchemy import Column, String, DateTime, Integer, event, inspect, insert, Table, func, and_, or_, select, \
    update, SmallInteger
from sqlalchemy.ext.declarative import declared_attr, declarative_base
from sqlalchemy.orm import mapper, Session

Base = declarative_base()

class Transaction(Base):
    __tablename__ = 'transaction'

    id = Column(Integer, primary_key=True, autoincrement=True)
    issued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    remote_addr = Column(String(50), nullable=True)

class TransactionManager:
    def __repr__(self):
        return f"<Transaction(id={self.id}, issued_at={self.issued_at})>"

    def __init__(self, session):
        self.session = session

    def create_transaction(self):
        print("Entering create_transaction")
        if 'current_transaction_id' in self.session.info:
            print(f"Reusing existing transaction: {self.session.info['current_transaction_id']}")
            return self.session.info['current_transaction_id']

        # Use insert().returning() to get the ID and issued_at without committing
        stmt = insert(Transaction).values(
            issued_at=func.now()
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
                'transaction_id': Column(Integer, nullable=False),
                'end_transaction_id': Column(Integer, nullable=True),
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

    @staticmethod
    def create_version(target, operation_type):
        session = Session.object_session(target)
        print(f"create_version called for {target.__class__.__name__} (id={target.id}), operation_type: {operation_type}")
        print(f"Session versioning enabled: {session.versioning_enabled}")
        print(f"Session current versioning: {session.current_versioning}")

        if not session or not session.is_new_versioning_active():
            print(f"Skipping version creation for {target.__class__.__name__} (id={target.id})")
            return

        if getattr(target, '__versioned__', {}).get('versioning', True):
            print(f"Warning: Object {target} still has versioning enabled")
            return

        # transaction_manager = TransactionManager(session)
        # transaction_id = transaction_manager.get_current_transaction_id()
        transaction_id = session.get_or_create_transaction()
        if transaction_id is None:
            print(f"Error: Unable to create transaction for {target.__class__.__name__} (id={target.id})")
            return

        print(f"Using transaction_id: {transaction_id}")

        VersionClass = target.__class__.__versioned_cls__

        # Use a more robust way to track versioned objects
        if not hasattr(session, '_versioned_objects'):
            session._versioned_objects = {}

        object_key = (target.__class__, target.id)
        if object_key in session._versioned_objects:
            if operation_type in session._versioned_objects[object_key]:
                print(f"Skipping duplicate version creation for {target.__class__.__name__} (id={target.id}), operation_type: {operation_type}")
                return
        else:
            session._versioned_objects[object_key] = set()

        # Convert operation_type to integer
        operation_type_map = {'I': 0, 'U': 1, 'D': 2}
        operation_type_int = operation_type_map.get(operation_type, 1)  # Default to UPDATE if unknown

        # Prepare the data for the new version
        new_version_data = {
            'id': target.id,
            'transaction_id': transaction_id,
            'end_transaction_id': None,
            'operation_type': operation_type_int
        }
        for column in inspect(target.__class__).columns:
            if column.name not in ['transaction_id', 'end_transaction_id', 'operation_type']:
                if hasattr(target, column.name):
                    new_version_data[column.name] = getattr(target, column.name)

        # Check if a version already exists for this transaction
        existing_version = session.execute(
            select(VersionClass).where(
                and_(
                    VersionClass.id == target.id,
                    VersionClass.transaction_id == transaction_id
                )
            )
        ).scalar_one_or_none()

        if existing_version:
            # Update the existing version
            print(f"Updating existing version for {target.__class__.__name__} (id={target.id}), transaction_id: {transaction_id}")
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
            print(f"Inserting new version for {target.__class__.__name__} (id={target.id}), transaction_id: {transaction_id}")
            session.execute(insert(VersionClass).values(new_version_data))

        # Close any other open versions
        session.execute(
            update(VersionClass).
            where(and_(
                VersionClass.id == target.id,
                VersionClass.end_transaction_id.is_(None),
                VersionClass.transaction_id != transaction_id
            )).
            values(end_transaction_id=transaction_id)
        )

        # Mark this object as versioned for this operation type
        session._versioned_objects[object_key].add(operation_type)

        print(f"Version created/updated for {target.__class__.__name__} (id={target.id}), transaction_id: {transaction_id}")

    @classmethod
    def _before_flush(cls, session, flush_context, instances):
        print(f"_before_flush called for {cls.__name__}")
        if session.is_new_versioning_active():
            # transaction_manager = TransactionManager(session)
            # transaction_id = transaction_manager.get_current_transaction_id()
            transaction_id = session.get_or_create_transaction()
            if transaction_id is None:
                print(f"Error: Unable to create transaction in _before_flush for {cls.__name__}")
                return
            print(f"Using transaction_id: {transaction_id}")
            for obj in session.new:
                if isinstance(obj, cls):
                    cls.create_version(obj, 'I')
            for obj in session.dirty:
                if isinstance(obj, cls):
                    cls.create_version(obj, 'U')
            for obj in session.deleted:
                if isinstance(obj, cls):
                    cls.create_version(obj, 'D')
        print(f"_before_flush completed for {cls.__name__}")

# def versioned_session(session):
#     @event.listens_for(session, "before_flush")
#     def before_flush(session, flush_context, instances):
#         if not session.versioning_enabled or session.current_versioning != 'new':
#             return
#
#         for obj in session.new.union(session.dirty).union(session.deleted):
#             if hasattr(obj, '__versioned_cls__'):
#                 obj._before_flush(session, flush_context, instances)

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


