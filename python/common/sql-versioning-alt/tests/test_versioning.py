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

from sql_versioning import (version_class)
from tests import (Base, Model, User, Address, Location, Email, Item, Transaction)


@pytest.mark.parametrize('test_name', ['CLASS','INSTANCE'])
def test_version_class(session, test_name):
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
    assert user_version.__table__ in Base.metadata.sorted_tables


def test_versioned_obj(session):
    """Test version_class-2."""
    address = Address()
    version = version_class(address)
    assert version


def test_basic(session):
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


def test_versioning_insert(session):
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


def test_versioning_relationships(session):
    user = User(name='user')
    address = Address(name='Some address')
    location = Location(name='Some location')
    emails = [Email(name='primary'), Email(name='secondary')]
    items = [Item(name='An item'), Item(name='Another item')]
    user.address = address
    user.location = location
    user.items = items
    user.emails = emails
    session.add(user)
    session.commit()

    user_version = version_class(User)
    result_revision = session.query(user_version)\
        .filter(user_version.name=='user')\
        .one_or_none()
    
    # Test one-to-one relationship
    # Versioned
    assert result_revision.address.id == address.id
    assert result_revision.address.name == "Some address"
    assert result_revision.address.user.name == user.name
    # Non versioned
    assert result_revision.location.id == location.id
    assert result_revision.location.name == "Some location"
    assert result_revision.location.user.name == user.name

    # Test one-to-many relationship
    # Versioned
    result_emails = result_revision.emails.all()
    assert len(result_emails) == len(emails)
    assert result_emails[0].id == emails[0].id
    assert result_emails[0].name == "primary"
    assert result_emails[1].id == emails[1].id
    assert result_emails[1].name == "secondary"
    # Non versioned
    result_items = result_revision.items.all()
    assert len(result_items) == len(items)
    assert result_items[0].id == items[0].id
    assert result_items[0].name == "An item"
    assert result_items[1].id == items[1].id
    assert result_items[1].name == "Another item"

    # Test many-to-one relationship
    # Note: this is a quirk of the RelationshipBuilder. We don't explicitly establish bi-directionality
    # by including the "reverse" side of the relationship (i.e. Item.user), but it works anyway
    # Versioned
    assert result_revision.emails[0].user.name == user.name
    assert result_revision.emails[1].user.name == user.name
    # Non versioned
    assert result_revision.items[0].user == user
    assert result_revision.items[1].user == user

    # Test update relationship
    user.address = Address(name='Some new address')
    session.commit()

    user_version = version_class(User)
    result_revisions = session.query(user_version)\
        .filter(user_version.name=='user')\
        .order_by(user_version.transaction_id)\
        .all()
    
    assert user.address.name == 'Some new address'
    assert len(result_revisions) == 2
    assert result_revisions[0].address.name == "Some address"
    assert result_revisions[1].address.name == "Some new address"


def test_versioning_relationships_remove(session):
    """Test remove from relationship."""
    user = User(name='test')
    for i in range(5):
        email = Email(name=f'email {i}')
        user.emails.append(email)
    session.add(user)
    session.commit()

    if existing_emails := user.emails.all():
        for email in existing_emails:
            user.emails.remove(email)
    session.add(user)
    session.commit()

    user = session.query(User).one_or_none()
    emails = user.emails.all()
    assert not emails

    emails = session.query(Email).all()
    assert not emails

    email_versions = session.query(version_class(Email))\
        .order_by(version_class(Email).transaction_id)\
        .all()
    assert len(email_versions) == 10
    for i in range(10):
        if i < 5:
            assert email_versions[i].operation_type == 0
        else:
            assert email_versions[i].operation_type == 2


def test_versioning_delete(session):
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


def test_versioning_update(session):
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


def test_versioning_query(session):
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


def test_versioning_rollback(session):
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
