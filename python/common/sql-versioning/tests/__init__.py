# Copyright © 2025 Province of British Columbia
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

Initialization file that holds testing classes.
"""
from sqlalchemy import Column, ForeignKey, Integer, String, orm

from sql_versioning import (Base, TransactionFactory, Versioned,
                            enable_versioning)


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

    # One-to-one versioned relationship
    address = orm.relationship('Address', backref='user', uselist=False)
    # One-to-one non-versioned relationship
    location = orm.relationship('Location', backref='user', uselist=False)
    # One-to-many versioned relationship
    emails = orm.relationship('Email', backref='user', lazy='dynamic')
    # One-to-many non versioned relationship
    items = orm.relationship('Item', backref='user', lazy='dynamic')

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

class Email(Base, Versioned):
    __tablename__ = 'emails'

    id = Column(Integer, primary_key=True)
    name = Column(String)

    user_id = Column(Integer, ForeignKey('users.id'))


class Item(Base):
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True)
    name = Column(String)

    user_id = Column(Integer, ForeignKey('users.id'))


orm.configure_mappers()