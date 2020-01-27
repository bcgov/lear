"""Data reset tool End-Points.

Get, post, and delete business, including all sub-objects - filings, addresses, etc.
"""
import os

from flask import Flask
from legal_api.models import db
from legal_api.schemas import rsbc_schemas
from legal_api.utils.logging import setup_logging

from data_reset_tool import config
from data_reset_tool.blueprints.fixture import FIXTURE_BLUEPRINT


setup_logging(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'logging.conf'))  # important to do this first


def create_app(run_mode=os.getenv('FLASK_ENV', 'production')):
    """Return a configured Flask App using the Factory method."""
    app = Flask(__name__)
    app.config.from_object(config.CONFIGURATION[run_mode])

    db.init_app(app)
    rsbc_schemas.init_app(app)

    # Register blueprints
    app.register_blueprint(FIXTURE_BLUEPRINT)

    # Shell context for flask cli
    @app.shell_context_processor
    def ctx():  # pylint: disable=unused-variable
        return {'app': app, 'db': db}

    return app
