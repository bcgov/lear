import os
import psycopg2
from unittest.mock import patch
import pytest

def test_connection_failed():
    status = False
    try:
        connection = psycopg2.connect(user=os.getenv('FAKE_DATABASE_USERNAME', ''),
                                      password=os.getenv('FAKE_DATABASE_PASSWORD', ''),
                                      host=os.getenv('FAKE_DATABASE_HOST', ''),
                                      port=os.getenv('FAKE_DATABASE_PORT', '5432'),
                                      database=os.getenv('FAKE_DATABASE_NAME', ''))

        cursor = connection.cursor()
        status = True
    except Exception:
        status = False
    finally:
        assert status == False


def test_database_connection_succeed():
    status = False
    try:
        connection = psycopg2.connect(user=os.getenv('DATABASE_USERNAME', ''),
                                      password=os.getenv('DATABASE_PASSWORD', ''),
                                      host=os.getenv('DATABASE_HOST', ''),
                                      port=os.getenv('DATABASE_PORT', '5432'),
                                      database=os.getenv('DATABASE_NAME', ''))
        cursor = connection.cursor()
        status = True
    except Exception:
        status = False
    finally:
        assert status == True


@pytest.mark.parametrize(
    'test_name, filing, expected_msg',
    [
        ('test_batch_has_already_run'),
        ('test_job_cron_valid'),
    ]
)
def test_initiate_dissolution_process(mocker, app, session, test_name):
    pass
