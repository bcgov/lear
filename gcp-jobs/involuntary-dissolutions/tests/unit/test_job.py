import os

import pg8000.native


def test_connection_failed():
    status = False
    try:
        connection = pg8000.native.Connection(
            user=os.getenv("FAKE_DATABASE_USERNAME", ""),
            password=os.getenv("FAKE_DATABASE_PASSWORD", ""),
            host=os.getenv("FAKE_DATABASE_HOST", ""),
            port=int(os.getenv("FAKE_DATABASE_PORT", "5432")),
            database=os.getenv("FAKE_DATABASE_NAME", ""),
        )
        connection.run("SELECT 1")
        status = True
    except Exception:
        status = False
    finally:
        assert status == False


def test_database_connection_succeed():
    status = False
    try:
        connection = pg8000.native.Connection(
            user=os.getenv("DATABASE_TEST_USERNAME", ""),
            password=os.getenv("DATABASE_TEST_PASSWORD", ""),
            host=os.getenv("DATABASE_TEST_HOST", ""),
            port=int(os.getenv("DATABASE_TEST_PORT", "5432")),
            database=os.getenv("DATABASE_TEST_NAME", ""),
        )
        connection.run("SELECT 1")
        status = True
    except Exception:
        status = False
    finally:
        assert status == True
