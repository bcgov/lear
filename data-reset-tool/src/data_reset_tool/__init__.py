import os

from data_reset_tool import config
from data_reset_tool.blueprints.fixture import fixture_blueprint
from flask import Flask
from flask_cors import CORS
from legal_api.models import db
from legal_api.schemas import rsbc_schemas
from legal_api.utils.logging import setup_logging

setup_logging(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'logging.conf'))  # important to do this first


def create_app(run_mode=os.getenv('FLASK_ENV', 'production')):
    """Return a configured Flask App using the Factory method."""
    app = Flask(__name__)
    app.config.from_object(config.CONFIGURATION[run_mode])

    # # Configure Sentry
    # if app.config.get('SENTRY_DSN', None):
    #     sentry_sdk.init(
    #         dsn=app.config.get('SENTRY_DSN'),
    #         integrations=[FlaskIntegration()]
    #     )

    db.init_app(app)
    rsbc_schemas.init_app(app)

    # Register blueprints
    app.register_blueprint(fixture_blueprint)

    # Shell context for flask cli
    @app.shell_context_processor
    def ctx():
        return {'app': app, 'db': db}

    return app


# def create_app(script_info=None):
#     # Instantiate the app
#     app = Flask(__name__)
#
#     # Enable CORS
#     CORS(app)
#
#     # Get config
#     app.config.from_object('data_reset_tool.config.Config')
#
#     # Set up extensions
#     db.init_app(app)
#
#     # Register blueprints
#     from data_reset_tool.blueprints.fixture import fixture_blueprint
#     app.register_blueprint(fixture_blueprint)
#     # ADD OTHER BLUEPRINTS AS NEW RESOURCES ARE NEEDED
#
#     # Shell context for flask cli
#     @app.shell_context_processor
#     def ctx():
#         return {'app': app, 'db': db}
#
#     return app
