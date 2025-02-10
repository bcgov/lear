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
"""Tests for versioning extension.

Test-Suite to ensure that the versioning extension is working as expected.
"""
import pytest
from sqlalchemy import Column, ForeignKey, Integer, String, orm

from sql_versioning import (Base, TransactionFactory, Versioned,
                            enable_versioning, version_class)

enable_versioning()

Transaction = TransactionFactory.create_transaction_model()

class Model(Base):
    __tablename__ = 'models'
    id = Column(Integer, primary_key=True)
    name = Column(String)

class User(Base, Versioned):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String)

    address = orm.relationship('Address', backref='user', uselist=False)
    locations = orm.relationship('Location', backref='user', lazy='dynamic')

class Address(Base, Versioned):
    __tablename__ = 'addresses'

    id = Column(Integer, primary_key=True)
    name = Column(String)

    user_id = Column(Integer, ForeignKey('users.id'))

class Location(Base):
    __tablename__ = 'locations'

    id = Column(Integer, primary_key=True)
    name = Column(String)

    user_id = Column(Integer, ForeignKey('users.id'))

orm.configure_mappers()


@pytest.mark.parametrize('test_name', ['CLASS','INSTANCE'])
def test_version_class(db, session, test_name):
    """Test version_class."""
    if test_name == 'CLASS':
        model = Model
        user = User
    else:
        model = Model()
        user = User()

    model_version = version_class(model)
    assert model_version is None

    user_version = version_class(user)
    assert user_version


def test_versioned_obj(db, session):
    """Test version_class-2."""
    address = Address()
    version = version_class(address)
    assert version


def test_basic(db, session):
    """Test basic db operation."""
    
    model = Model(name='model')
    session.add(model)
    session.commit()

    result_model = session.query(Model)\
        .filter(Model.name=='model')\
        .one_or_none()
    assert result_model
    assert result_model.id

    user = User(name='user')
    session.add(user)
    session.commit()

    result_user = session.query(User)\
        .filter(User.name=='user')\
        .one_or_none()
    assert result_user
    assert result_user.id


def test_versioning_insert(db, session):
    """Test insertion."""
    user = User(name='user')
    address = Address(name='address')
    user.address = address
    session.add(user)
    session.commit()
    
    result = session.query(User)\
        .filter(User.name=='user')\
        .one_or_none()
    assert result
    assert result.address

    transactions = session.query(Transaction).all()
    assert len(transactions) == 1
    transaction = transactions[0]
    assert transaction

    user_version = version_class(User)
    result_revision = session.query(user_version)\
        .filter(user_version.name=='user')\
        .one_or_none()
    assert result_revision
    assert result_revision.transaction_id == transaction.id
    assert result_revision.operation_type == 0
    assert result_revision.end_transaction_id is None

    address_version = version_class(Address)
    result_versioned_address = session.query(address_version)\
        .filter(address_version.name=='address')\
        .one_or_none()
    assert result_versioned_address
    assert result_versioned_address.transaction_id == transaction.id
    assert result_versioned_address.operation_type == 0
    assert result_versioned_address.end_transaction_id is None

def test_versioning_relationships(db, session):
    user = User(name='user')
    address = Address(name='address')
    locations = [Location(name='location1'), Location(name='location2')]
    user.address = address
    user.locations = locations
    session.add(user)
    session.commit()

    user_version = version_class(User)
    result_revision = session.query(user_version)\
        .filter(user_version.name=='user')\
        .one_or_none()
    assert result_revision.address == address
    # assert result_revision.locations == locations


def test_versioning_relationships(db, session):
    user = User(name='user')
    address = Address(name='Some address')
    locations = [Location(name='Some location'), Location(name='Some other location')]
    user.address = address
    user.locations = locations
    session.add(user)
    session.commit()

    user_version = version_class(User)
    result_revision = session.query(user_version)\
        .filter(user_version.name=='user')\
        .one_or_none()
    
    # Test one-to-one relationship (w/ relationship to version class)
    assert result_revision.address.id == address.id
    assert result_revision.address.name == "Some address"
    assert result_revision.address.user == user

    # Test one-to-many relationship (w/ relationship to non-version class)
    result_locations = result_revision.locations.all()
    assert len(result_locations) == len(locations)
    assert result_locations[0].id == locations[0].id
    assert result_locations[0].name == "Some location"
    assert result_locations[1].id == locations[1].id
    assert result_locations[1].name == "Some other location"

    # Test many-to-one relationship
    # Note: this is a quirk of the RelationshipBuilder. We don't explicitly establish bi-directionality
    # by including the "reverse" side of the relationship (i.e. Location.user), but it works anyway
    assert result_revision.locations[0].user == user
    assert result_revision.locations[1].user == user

    # Test update relationship
    user.address = Address(name='Some new address')
    session.commit()

    user_version = version_class(User)
    result_revisions = session.query(user_version)\
        .filter(user_version.name=='user')\
        .all()
    
    assert user.address.name == 'Some new address'
    assert len(result_revisions) == 2
    assert result_revisions[0].address.name == "Some address"
    # assert result_revisions[1].address.name == "Some new address"


def test_versioning_delete(db, session):
    """Test deletion."""
    user = User(name='test')
    session.add(user)
    session.commit()

    session.delete(user)
    session.commit()

    user_version = version_class(User)
    results = session.query(user_version)\
        .filter(user_version.id==user.id)\
        .order_by(user_version.transaction_id)\
        .all()

    assert len(results) == 2
    assert results[1].operation_type == 2
    assert results[1].transaction_id is not None
    assert results[0].operation_type == 0
    assert results[0].end_transaction_id == results[1].transaction_id


def test_versioning_update(db, session):
    """Test update."""
    user = User(name='old')
    session.add(user)
    session.commit()

    user.name = 'new'
    session.add(user)
    session.commit()

    # the following operations should not result in new versioned records for native sqlalchemy session
    session.add(user)
    session.commit()

    user_version = version_class(User)
    results = session.query(user_version)\
        .filter(user_version.id==user.id)\
        .order_by(user_version.transaction_id)\
        .all()

    assert len(results) == 2
    assert results[1].operation_type == 1
    assert results[1].name == 'new'
    assert results[1].transaction_id is not None
    assert results[0].operation_type == 0
    assert results[0].name == 'old'
    assert results[0].end_transaction_id == results[1].transaction_id


def test_versioning_query(db, session):
    """Test querying versioned data."""
    user = User(name='old')
    session.add(user)
    session.commit()

    user.name = 'new'
    session.add(user)
    session.commit()

    user_version = version_class(User)
    result = session.query(user_version)\
        .filter(user_version.transaction_id==1)\
        .one_or_none()
    
    assert result
    assert result.name == 'old'


def test_versioning_rollback(db, session):
    """Test rollback."""
    user1 = User(name='test1')
    session.add(user1)
    session.commit()
    
    user_version = version_class(User)
    results_txn1 = session.query(Transaction).all()
    results_user1 = session.query(User).all()
    results_version1 = session.query(user_version).all()

    assert len(results_txn1) == 1
    assert len(results_user1) == 1
    assert len(results_version1) == 1
    
    try:
        user2 = User(name='test2')
        session.add(user2)
        session.flush()
        raise Exception('an error')
    except Exception:
        session.rollback()

    results_txn2 = session.query(Transaction).all()
    results_user2 = session.query(User).all()
    results_version2 = session.query(user_version).all()

    assert len(results_txn2) == 1
    assert len(results_user2) == 1
    assert len(results_version2) == 1
    assert results_txn1[0] == results_txn2[0]
    assert results_user1[0] == results_user2[0]
    assert results_version1[0] == results_version2[0]
