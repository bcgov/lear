import os

import psycopg2


def test_connection_failed():
    status = False
    try:
        connection = psycopg2.connect(user=os.getenv("FAKE_DATABASE_USERNAME", ""),
                                      password=os.getenv("FAKE_DATABASE_PASSWORD", ""),
                                      host=os.getenv("FAKE_DATABASE_HOST", ""),
                                      port=os.getenv("FAKE_DATABASE_PORT", "5432"),
                                      database=os.getenv("FAKE_DATABASE_NAME", ""))

        connection.cursor()
        status = True
    except Exception:
        status = False
    finally:
        assert status == False


def test_database_connection_succeed():
    status = False
    try:
        connection = psycopg2.connect(user=os.getenv("DATABASE_USERNAME", ""),
                                      password=os.getenv("DATABASE_PASSWORD", ""),
                                      host=os.getenv("DATABASE_HOST", ""),
                                      port=os.getenv("DATABASE_PORT", "5432"),
                                      database=os.getenv("DATABASE_NAME", ""))
        connection.cursor()
        status = True
    except Exception:
        status = False
    finally:
        assert status == True
