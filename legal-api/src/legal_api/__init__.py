# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""The Legal API service.

This module is the API for the Legal Entity system.
"""
import os

import sentry_sdk  # noqa: I001; pylint: disable=ungrouped-imports; conflicts with Flake8
from sentry_sdk.integrations.flask import FlaskIntegration  # noqa: I001
from flask import redirect, Flask  # noqa: I001
from registry_schemas import __version__ as registry_schemas_version  # noqa: I005
from registry_schemas.flask import SchemaServices  # noqa: I001

from legal_api import config, models
from legal_api.models import db
from legal_api.resources import endpoints
from legal_api.schemas import rsbc_schemas
from legal_api.services import digital_credentials, flags, queue
from legal_api.translations import babel
from legal_api.utils.auth import jwt
from legal_api.utils.logging import setup_logging
from legal_api.utils.run_version import get_run_version
# noqa: I003; the sentry import creates a bad line count in isort

setup_logging(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'logging.conf'))  # important to do this first


def create_app(run_mode=os.getenv('FLASK_ENV', 'production')):
    """Return a configured Flask App using the Factory method."""
    app = Flask(__name__)
    app.config.from_object(config.CONFIGURATION[run_mode])

    # Configure Sentry
    if dsn := app.config.get('SENTRY_DSN', None):
        # pylint==2.7.4 errors out on the syntatic sugar for sentry_sdk
        # the error is skipped by disable=abstract-class-instantiated
        sentry_sdk.init(  # pylint: disable=abstract-class-instantiated
            dsn=dsn,
            integrations=[FlaskIntegration()],
            release=f'legal-api@{get_run_version()}',
            send_default_pii=False
        )

    db.init_app(app)
    rsbc_schemas.init_app(app)
    flags.init_app(app)
    queue.init_app(app)
    babel.init_app(app)
    endpoints.init_app(app)

    with app.app_context():  # db require app context
        digital_credentials.init_app(app)

    setup_jwt_manager(app, jwt)

    register_shellcontext(app)

    return app


def setup_jwt_manager(app, jwt_manager):
    """Use flask app to configure the JWTManager to work for a particular Realm."""
    def get_roles(a_dict):
        return a_dict['realm_access']['roles']  # pragma: no cover
    app.config['JWT_ROLE_CALLBACK'] = get_roles

    jwt_manager.init_app(app)


def register_shellcontext(app):
    """Register shell context objects."""
    def shell_context():
        """Shell context objects."""
        return {
            'app': app,
            'jwt': jwt,
            'db': db,
            'models': models}  # pragma: no cover

    app.shell_context_processor(shell_context)
