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
import os
import time

import pytest
from dotenv import find_dotenv, load_dotenv
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from sql_versioning import Base

load_dotenv(find_dotenv())
postgres = PostgresContainer("postgres:16-alpine")

def get_db_uri():
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    username = os.getenv("DB_USERNAME", "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")
    database = os.getenv("DB_NAME", "postgres")
    database_uri = f"postgresql+pg8000://{username}:{password}@{host}:{int(port)}/{database}"
    return database_uri

@pytest.fixture(scope="session", autouse=True)
def setup(request):
    postgres.start()

    def remove_container():
        postgres.stop()

    request.addfinalizer(remove_container)


@pytest.fixture(scope='session')
def session(setup):
    """Clear DB and build tables"""
    POSTGRES_URL = get_db_uri()
    engine = create_engine(POSTGRES_URL)

    # create tables
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

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
    session.execute(text('ALTER SEQUENCE transaction_id_seq RESTART WITH 1'))
    session.commit()
