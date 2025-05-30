import pytest
from dotenv import find_dotenv, load_dotenv

from future_effective_filings import create_app

# this will load all the envars from a .env file located in the project root (api)
load_dotenv(find_dotenv())

def test_create_app():
    try:
        create_app()
    except Exception:
        pytest.fail("Failed to create app")