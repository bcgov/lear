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
"""Common setup and fixtures for the pytest suite used by this service."""
import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sql_versioning import Base

POSTGRES_URL = 'postgresql://postgres:postgres@localhost:5433/test'


@pytest.fixture(scope='session')
def db(docker_services):
    """Create postgres service."""
    docker_services.start('postgres')
    time.sleep(2)


@pytest.fixture(scope='session')
def session(db):
    """Clear DB and build tables"""
    engine = create_engine(POSTGRES_URL)

    # create tables
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine) 

    # TODO: debug
    for table in Base.metadata.tables:
        print(f'Creating table: {table}')

    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    # cleanup
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def clear_tables(session):
    """Clear tables and reset transaction sequence."""
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.execute('ALTER SEQUENCE transaction_id_seq RESTART WITH 1')
    session.commit()
