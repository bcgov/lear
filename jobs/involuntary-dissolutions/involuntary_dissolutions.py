# Copyright © 2021 Province of British Columbia
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
"""Involuntary dissolutions job."""
import logging
import os

import sentry_sdk  # noqa: I001, E501; pylint: disable=ungrouped-imports; conflicts with Flake8
from flask import Flask
from legal_api.models import db  # noqa: I001
from legal_api.services.flags import Flags
from sentry_sdk.integrations.logging import LoggingIntegration

import config  # pylint: disable=import-error
from utils.logging import setup_logging  # pylint: disable=import-error
# noqa: I003

setup_logging(
    os.path.join(os.path.abspath(os.path.dirname(__file__)), 'logging.conf'))

SENTRY_LOGGING = LoggingIntegration(
    event_level=logging.ERROR  # send errors as events
)

flags = Flags()


def create_app(run_mode=os.getenv('FLASK_ENV', 'production')):
    """Return a configured Flask App using the Factory method."""
    app = Flask(__name__)
    app.config.from_object(config.CONFIGURATION[run_mode])
    db.init_app(app)

    # Configure Sentry
    if app.config.get('SENTRY_DSN', None):
        sentry_sdk.init(
            dsn=app.config.get('SENTRY_DSN'),
            integrations=[SENTRY_LOGGING]
        )

    if app.config.get('LD_SDK_KEY', None):
        flags.init_app(app)

    register_shellcontext(app)

    return app


def register_shellcontext(app):
    """Register shell context objects."""
    def shell_context():
        """Shell context objects."""
        return {'app': app}

    app.shell_context_processor(shell_context)


if __name__ == '__main__':
    application = create_app()
    with application.app_context():
        # TODO: detailed implementation
        application.logger.debug('Running involuntary dissolutions job')
