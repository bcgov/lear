import pytest
from future_effective_filings import create_app

from dotenv import load_dotenv, find_dotenv

# this will load all the envars from a .env file located in the project root (api)
load_dotenv(find_dotenv())

def test_create_app():
    try:
        create_app()
    except Exception:
        pytest.fail("Failed to create app")