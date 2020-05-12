"""Data reset tool End-Points.

Get, post, and delete business, including all sub-objects - filings, addresses, etc.
"""
import os

from flask import Flask

from data_reset_tool import config
from data_reset_tool.blueprints.fixture import FIXTURE_BLUEPRINT


def create_app(run_mode=os.getenv('FLASK_ENV', 'production')):
    """Return a configured Flask App using the Factory method."""
    app = Flask(__name__)
    app.config.from_object(config.CONFIGURATION[run_mode])

    # Register blueprints
    app.register_blueprint(FIXTURE_BLUEPRINT)

    # Shell context for flask cli
    @app.shell_context_processor
    def ctx():  # pylint: disable=unused-variable
        return {'app': app}

    return app
