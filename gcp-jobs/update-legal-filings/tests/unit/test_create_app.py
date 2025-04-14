import pytest
from dotenv import find_dotenv, load_dotenv

from update_legal_filings import create_app
from update_legal_filings.worker import update_business_nos

# this will load all the envars from a .env file located in the project root (api)
load_dotenv(find_dotenv())

def test_create_app():
    try:
        create_app("testing")
    except Exception:
        pytest.fail("Failed to create app")


def test_update_business_nos(app):  # pylint: disable=redefined-outer-name
    update_business_nos()
