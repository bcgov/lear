#THESE TESTS ONLY WORK LOCALLY THEY DO NOT RUN IN CI
import os
from unittest.mock import patch
import shutil
import pg8000
import pytest
from notebookreport.notebookreport import processnotebooks

from dotenv import load_dotenv, find_dotenv

# this will load all the envars from a .env file located in the project root (api)
load_dotenv(find_dotenv())


def test_connection_failed():
    status = False
    try:
        connection = pg8000.connect(user=os.getenv('FAKE_DATABASE_USERNAME', ''),
                                     password=os.getenv('FAKE_DATABASE_PASSWORD', ''),
                                     host=os.getenv('FAKE_DATABASE_HOST', ''),
                                     port=int(os.getenv('FAKE_DATABASE_PORT', '5432')),
                                     database=os.getenv('FAKE_DATABASE_NAME', ''))

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
        connection = pg8000.connect(user=DATABASE_TEST_USERNAME,
                                     password=DATABASE_TEST_PASSWORD,
                                     host=DATABASE_TEST_HOST,
                                     port=int(DATABASE_TEST_PORT or 5432),
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

@patch('requests.post')
@patch('requests.get')
@pytest.mark.parametrize("report_type", test_filings_monthly_data)
def test_filings_monthly_notebook_report(mock_get, mock_post, report_type, app):
    # Mock setup
    mock_get_response = mock_get.return_value
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {'key': 'value'}

    mock_post_response = mock_post.return_value
    mock_post_response.status_code = 200
    mock_post_response.json.return_value = {'access_token': 'fake-token'}

    days = ""
    for i in range(1, 32):
        days += str(i) + ","
    os.environ["MONTH_REPORT_DATES"] = "[" + days[:-1] + "]"
    os.environ["DATABASE_USERNAME"] = os.getenv("DATABASE_TEST_USERNAME", "")
    os.environ["DATABASE_PASSWORD"] = os.getenv("DATABASE_TEST_PASSWORD", "")
    os.environ["DATABASE_HOST"] = os.getenv("DATABASE_TEST_HOST", "")
    os.environ["DATABASE_PORT"] = os.getenv("DATABASE_TEST_PORT", "5432")
    os.environ["DATABASE_NAME"] = os.getenv("DATABASE_TEST_NAME", "")

    data_dir = os.path.join(os.getcwd(), r'data/')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    status = processnotebooks(report_type, data_dir)
    shutil.rmtree(data_dir)

    assert status == True
