from datetime import datetime
import os
import shutil
import psycopg2
import pytest
import ast
from notebookreport import processnotebooks


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
        connection = psycopg2.connect(user=os.getenv('PG_USER', ''),
                                      password=os.getenv('PG_PASSWORD', ''),
                                      host=os.getenv('PG_HOST', ''),
                                      port=os.getenv('PG_PORT', '5432'),
                                      database=os.getenv('PG_DB_NAME', ''))
        cursor = connection.cursor()
        status = True
    except Exception:
        status = False
    finally:
        assert status == True


test_filings_monthly_data = [
    ("daily"), ("monthly"),
]


@pytest.mark.parametrize("report_type", test_filings_monthly_data)
def test_filings_monthly_notebook_report(report_type):
    data_dir = os.path.join(os.getcwd(), r'data/')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    status = processnotebooks(report_type, data_dir)
    shutil.rmtree(data_dir)

    assert status == True
