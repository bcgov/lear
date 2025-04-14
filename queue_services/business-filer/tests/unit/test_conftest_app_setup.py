import pytest
import os
from flask import current_app
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer
postgres = PostgresContainer("postgres:16-alpine")

# def test_app_fixture(app):

#     assert app

#     db_url = current_app.config.get('SQLALCHEMY_DATABASE_URI', None)
#     assert db_url




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
    # Base.metadata.drop_all(engine)
    # Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    # cleanup
    session.close()
    # Base.metadata.drop_all(engine)

def test_basic_db(session):

    try:
        ret = session.execute(text("select now();"))
        print(ret)
    except Exception as err:
        print (err)
