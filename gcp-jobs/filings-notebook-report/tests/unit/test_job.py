import os
from unittest.mock import patch
import shutil
import psycopg2
import pytest
from notebookreport.notebookreport import processnotebooks

from dotenv import load_dotenv, find_dotenv

# this will load all the envars from a .env file located in the project root (api)
load_dotenv(find_dotenv())


def test_connection_failed():
    status = False
    try:
        connection = psycopg2.connect(user=os.getenv('FAKE_PG_USER', ''),
                                      password=os.getenv('FAKE_PG_PASSWORD', ''),
                                      host=os.getenv('FAKE_PG_HOST', ''),
                                      port=os.getenv('FAKE_PG_PORT', '5432'),
                                      database=os.getenv('FAKE_PG_DB_NAME', ''))

        cursor = connection.cursor()
        status = True
    except Exception:
        status = False
    finally:
        assert status == False


def test_connection_succeed():
    status = False
    try:
        DATABASE_TEST_USERNAME = os.getenv("DATABASE_TEST_USERNAME")
        DATABASE_TEST_PASSWORD = os.getenv("DATABASE_TEST_PASSWORD")
        DATABASE_TEST_NAME = os.getenv("DATABASE_TEST_NAME")
        DATABASE_TEST_HOST = os.getenv("DATABASE_TEST_HOST")
        DATABASE_TEST_PORT = os.getenv("DATABASE_TEST_PORT")
        connection = psycopg2.connect(user=DATABASE_TEST_USERNAME,
                                      password=DATABASE_TEST_PASSWORD,
                                      host=DATABASE_TEST_HOST,
                                      port=DATABASE_TEST_PORT,
                                      database=DATABASE_TEST_NAME)
        connection.cursor()
        status = True
    except Exception:
        status = False
    finally:
        assert status == True


test_filings_monthly_data = [
    ("daily"), ("monthly"),
]

@patch('requests.get')
@pytest.mark.parametrize("report_type", test_filings_monthly_data)
def test_filings_monthly_notebook_report(mock_get,report_type):
    # Mock setup
    mock_response = mock_get.return_value
    mock_response.status_code = 200
    mock_response.json.return_value = {'key': 'value'}

    days = ""
    for i in range(1, 32):
        days += str(i) + ","
    os.environ["MONTH_REPORT_DATES"] = "[" + days[:-1] + "]"
    os.environ["PG_USER"] = os.getenv("DATABASE_TEST_USERNAME")
    os.environ["PG_PASSWORD"] = os.getenv("DATABASE_TEST_PASSWORD")
    os.environ["PG_HOST"] = os.getenv("DATABASE_TEST_HOST")
    os.environ["PG_PORT"] = os.getenv("DATABASE_TEST_PORT")
    os.environ["PG_DB_NAME"] = os.getenv("DATABASE_TEST_NAME")
    os.environ["RETRY_INTERVAL"] = "60"

    data_dir = os.path.join(os.getcwd(), r'data/')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    status = processnotebooks(report_type, data_dir)
    shutil.rmtree(data_dir)

    assert status == True
