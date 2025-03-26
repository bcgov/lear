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
from flask_sqlalchemy.session import Session
from sql_versioning import TransactionManager
from sql_versioning import enable_versioning
from sql_versioning import version_class as _new_version_class
from sqlalchemy import event
from sqlalchemy import func
from sqlalchemy import orm


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
    issued_at = db.Column(db.DateTime,
                           default=func.now(),
                          nullable=True)


def init_db(app):
    """Initialize database using flask app and configure db mappers.

    :param app: Flask app
    :return: None
    """
    db.init_app(app)
    orm.configure_mappers()


class VersioningProxy:
    """A proxy class to handle switching between old and new versioning extension."""

    @classmethod
    def lock_versioning(cls, session, transaction):
        """Lock versioning for the session.

        This ensures that only one versioning extension is enabled throughout the session.

        :param session: The database session instance.
        :param transaction: The transaction associated with the session.
        :return: None
        """
        if '_versioning_locked' not in session.info:
            session.info['_versioning_locked'] = True
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
        new_transaction_manager = TransactionManager(session)
        return new_transaction_manager.create_transaction()

    @classmethod
    def version_class(cls, session, obj):
        """Return version class for an object based in the session.

        :param session: The database session instance.
        :param obj: The object for which the version class is needed.
        :return: The version class of the object.
        """
        if not session.in_transaction():  # trigger versioning setup listener
            session.begin()

        return _new_version_class(obj)


def setup_versioning():
    """Set up and initialize versioning switching.

    :return: None
    """
    # use Session to skip events for continuum's internal session/txn operations
    @event.listens_for(Session, 'after_transaction_create')
    def after_transaction_create(session, transaction):
        VersioningProxy.lock_versioning(session, transaction)

    @event.listens_for(Session, 'after_transaction_end')
    def clear_transaction(session, transaction):
        VersioningProxy.unlock_versioning(session, transaction)

    enable_versioning(transaction_cls=Transaction)
    # make_versioned(user_cls=None, manager=versioning_manager)


setup_versioning()
