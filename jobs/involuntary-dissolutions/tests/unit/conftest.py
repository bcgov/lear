import pytest
from flask import current_app

from involuntary_dissolutions import create_app

from config import _Config


@pytest.fixture(scope="session")
def app(request):
    """
    Returns session-wide application.
    """
    app = create_app(_Config)

    return app


@pytest.fixture(scope="session")
def client_ctx(app):
    """
    Returns session-wide Flask test client.
    """
    with app.test_client() as c:
        yield c
